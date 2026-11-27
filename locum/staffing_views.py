import csv
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import urlencode
from uuid import uuid4
from zoneinfo import ZoneInfo

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from appAdmin.models import Admin, Employer
from .ledger import job_shift_dates
from .models import Job
from .staffing_models import StaffingBranch, StaffingManager, StaffingPosition, StaffingRequest
from .staffing_workflow import eligible_applications, pilot_employers, record_event, reserved_job_position


Status = StaffingPosition.Status
LONDON = ZoneInfo('Europe/London')
TIME_INPUT = forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')
MAX_REQUEST_DATES = 31


class ShiftDatesInput(forms.Widget):
    def value_from_datadict(self, data, files, name):
        return data.getlist(name) or data.getlist('shift_date')


class ShiftDatesField(forms.Field):
    widget = ShiftDatesInput

    def clean(self, value):
        if not value or len(value) > MAX_REQUEST_DATES:
            raise ValidationError(f'Choose between 1 and {MAX_REQUEST_DATES} dates.')
        date_field = forms.DateField(input_formats=['%Y-%m-%d'])
        days = sorted({date_field.clean(raw_date) for raw_date in value})
        if days[0] < timezone.localdate(timezone=LONDON) or days[-1].year > 9998:
            raise ValidationError('Choose valid dates from today onwards.')
        return days


class RequestForm(forms.Form):
    branch = forms.ModelChoiceField(label='Pharmacy location', queryset=StaffingBranch.objects.none())
    shift_dates = ShiftDatesField()
    role = forms.ChoiceField(label='Role required', choices=[('', 'Select a role'), *StaffingRequest.Role.choices])
    quantity = forms.IntegerField(label='Staff per date', min_value=1, max_value=50, initial=1)
    start_time = forms.TimeField(label='Start', widget=TIME_INPUT)
    end_time = forms.TimeField(label='End', widget=TIME_INPUT)
    budget = forms.DecimalField(label='Budget per hour (£, optional)', required=False,
                                min_value=Decimal('0.01'), max_digits=8, decimal_places=2)
    submission_id = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)

    def __init__(self, employer, *args, single_site=False, **kwargs):
        super().__init__(*args, **kwargs)
        branches = employer.staffing_branches.all()
        if single_site:
            primary_id = branches.order_by('pk').values_list('pk', flat=True).first()
            branches = branches.filter(pk=primary_id)
        self.fields['branch'].queryset = branches

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('start_time') and cleaned['start_time'] == cleaned.get('end_time'):
            self.add_error('end_time', 'Choose a different end time.')
        return cleaned


class ProposalForm(forms.Form):
    candidate_name = forms.CharField(label='Offline candidate name', max_length=160, required=False)
    application = forms.IntegerField(min_value=1, required=False)
    client_rate = forms.DecimalField(label='Proposed client rate (£ per hour, optional)',
                                     required=False, min_value=Decimal('0.01'),
                                     max_digits=8, decimal_places=2)
    proposal_note = forms.CharField(label='Note for Montu (optional)', max_length=500, required=False,
                                   widget=forms.Textarea(attrs={'rows': 2}))

    def clean(self):
        cleaned = super().clean()
        if bool(cleaned.get('candidate_name')) == bool(cleaned.get('application')):
            raise ValidationError('Enter an offline candidate name or choose one job application.')
        return cleaned


class AttendanceForm(forms.Form):
    actual_start = forms.TimeField(label='Actual start', required=False, widget=TIME_INPUT)
    actual_end = forms.TimeField(label='Actual finish', required=False, widget=TIME_INPUT)
    break_minutes = forms.IntegerField(label='Unpaid break (minutes)', required=False, min_value=0, max_value=1439)
    paid_hours = forms.DecimalField(required=False, min_value=Decimal('0.01'),
                                    max_value=Decimal('24'), max_digits=4, decimal_places=2)
    note = forms.CharField(label='Attendance note (optional)', max_length=500, required=False,
                           widget=forms.Textarea(attrs={'rows': 2}))


class AttendanceExportForm(forms.Form):
    period = forms.ChoiceField(choices=[
        ('day', 'Daily'), ('week', 'Weekly'), ('month', 'Monthly'), ('range', 'Custom date range'),
    ])
    start = forms.DateField(label='Date', required=False,
                            widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    end = forms.DateField(label='End date (custom range only)', required=False,
                          widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        start, end = data.get('start'), data.get('end')
        if not start or not 1 < start.year < 9999:
            self.add_error('start', 'Choose a valid date for the report.')
        elif data.get('period') == 'range' and (not end or end < start):
            self.add_error('end', 'Choose an end date on or after the start date.')
        return data

    def date_range(self):
        start = self.cleaned_data['start']
        period = self.cleaned_data['period']
        if period == 'month':
            return start.replace(day=1), start.replace(day=monthrange(start.year, start.month)[1])
        if period == 'week':
            monday = start - timedelta(days=start.weekday())
            return monday, monday + timedelta(days=6)
        return start, self.cleaned_data['end'] if period == 'range' else start


@method_decorator(never_cache, name='dispatch')
class ManagerView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        self.membership = get_object_or_404(
            StaffingManager.objects.select_related('employer'), user=request.user, employer__in=pilot_employers())
        self.employer = self.membership.employer
        return super().dispatch(request, *args, **kwargs)


class StaffingProfileView(ManagerView):
    def get(self, request):
        return render(request, 'staffing/profile.html', {'employer': self.employer})


class StaffingStaffMixin:
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not Admin.objects.filter(pk=request.user.pk).exists():
            raise PermissionDenied
        self.employers = pilot_employers()
        if 'employer_id' in kwargs:
            self.employer = get_object_or_404(self.employers, pk=kwargs['employer_id'])
        return super().dispatch(request, *args, **kwargs)


class StaffingStaffIndexView(StaffingStaffMixin, View):
    def get(self, request):
        employers = list(self.employers.order_by('pharmacy_name', 'pk'))
        if len(employers) == 1:
            return redirect('staffing_staff', employer_id=employers[0].pk)
        return render(request, 'staffing/employers.html', {'employers': employers})


def valid_day(value):
    try:
        parsed = parse_date(value or '')
    except ValueError:
        return None
    return parsed if parsed and 1 < parsed.year < 9999 else None


class CalendarMixin:
    staff = False

    def calendar_context(self, request):
        today = timezone.localdate(timezone=LONDON)
        requested_week = valid_day(request.GET.get('week')) or today
        first = requested_week - timedelta(days=requested_week.weekday())
        days = [first + timedelta(days=i) for i in range(7)]
        selected_day = valid_day(request.GET.get('day')) or today
        if selected_day not in days:
            selected_day = first
        branches = list(self.employer.staffing_branches.all())
        primary_branch = min(branches, key=lambda branch: branch.pk, default=None)
        branch_filter = request.GET.get('branch', '')
        mode = request.GET.get('mode')
        if mode not in ('single', 'multi'):
            mode = 'multi' if self.staff or branch_filter else 'single'
        view_branches = branches if mode == 'multi' else ([primary_branch] if primary_branch else [])
        if mode == 'single':
            branch_filter = str(primary_branch.pk) if primary_branch else ''
        selected_branches = [branch for branch in view_branches if str(branch.pk) == branch_filter]
        shown_branches = selected_branches or view_branches
        branch_filter = branch_filter if selected_branches else ''
        positions = StaffingPosition.objects.filter(
            request__branch__in=shown_branches, request__shift_date__range=(first, days[-1]),
        ).select_related('request', 'request__branch').order_by('request__shift_date', 'request__start_time', 'pk')
        positions = list(positions)
        cells = defaultdict(list)
        for position in positions:
            cells[position.request.branch_id, position.request.shift_date].append(position)
        view_query = {'week': first.isoformat(), 'day': selected_day.isoformat()}
        query = urlencode({**view_query, 'branch': branch_filter, 'mode': mode})
        counts = Counter(p.status for p in positions)
        return {
            'employer': self.employer, 'staff': self.staff,
            'today': today, 'yesterday': today - timedelta(days=1), 'first': first,
            'days': days, 'selected_day': selected_day,
            'max_request_dates': MAX_REQUEST_DATES,
            'previous_week': first - timedelta(days=7), 'next_week': first + timedelta(days=7),
            'branches': branches, 'primary_branch': primary_branch, 'view_branches': view_branches,
            'shown_branches': shown_branches,
            'branch_filter': branch_filter, 'query': query,
            'mode': mode, 'view_query': urlencode(view_query),
            'selected_branch': selected_branches[0] if selected_branches else None,
            'rows': [(branch, [(day, cells[branch.pk, day]) for day in days]) for branch in shown_branches],
            'daily_positions': [p for p in positions if p.request.shift_date == selected_day],
            'positions': positions,
            'summary': [('Total positions', len(positions) - counts[Status.CANCELLED]),
                        ('Still needed', counts[Status.REQUESTED]),
                        ('Awaiting approval', counts[Status.PROPOSED]),
                        ('Approved', counts[Status.APPROVED] + counts[Status.BOOKED]),
                        ('Attended', counts[Status.ATTENDED])],
        }


class StaffingCalendarView(CalendarMixin, ManagerView):
    def get(self, request):
        return render(request, 'staffing/calendar.html', self.calendar_context(request))

    def calendar_context(self, request):
        context = super().calendar_context(request)
        context['form'] = RequestForm(self.employer, single_site=context['mode'] == 'single', initial={
            'shift_dates': [max(context['today'], context['selected_day']).isoformat()],
            'branch': context['selected_branch'] or context['primary_branch'],
            'start_time': '09:00', 'end_time': '17:00',
        })
        context['export_form'] = AttendanceExportForm(initial={'period': 'week', 'start': context['selected_day']})
        return context

    def post(self, request):
        form = RequestForm(self.employer, request.POST, single_site=request.GET.get('mode') == 'single')
        if form.is_valid():
            with transaction.atomic():
                data = form.cleaned_data
                dates = data['shift_dates']
                fields = {'branch': data['branch'], 'requested_by': request.user,
                          'start_time': data['start_time'], 'end_time': data['end_time'],
                          'role': data['role'], 'budget': data['budget']}
                shift, created = StaffingRequest.objects.get_or_create(
                    submission_key=data['submission_id'], defaults={**fields, 'shift_date': dates[0]},
                )
                if shift.requested_by_id != request.user.pk or shift.branch.employer_id != self.employer.pk:
                    raise PermissionDenied
                quantity = data['quantity']
                if created:
                    StaffingRequest.objects.bulk_create([
                        StaffingRequest(first_request=shift, shift_date=day, **fields) for day in dates[1:]
                    ])
                    request_ids = [shift.pk, *shift.additional_requests.values_list('pk', flat=True)]
                    StaffingPosition.objects.bulk_create([
                        StaffingPosition(request_id=shift_id)
                        for shift_id in request_ids for _ in range(quantity)
                    ], batch_size=250)
            if created:
                messages.success(request, f'Requested {quantity * len(dates)} staffing position(s) across '
                                 f'{len(dates)} date(s).')
            mode = request.GET.get('mode', 'multi')
            branch = request.GET.get('branch', '') if mode == 'multi' else shift.branch_id
            viewed_branch = request.GET.get('branch')
            if viewed_branch and viewed_branch != str(shift.branch_id):
                mode, branch = 'multi', shift.branch_id
            query = urlencode({'week': shift.shift_date.isoformat(), 'day': shift.shift_date.isoformat(),
                               'branch': branch, 'mode': mode})
            return redirect(f'{reverse("staffing_calendar")}?{query}')
        context = self.calendar_context(request)
        context['form'] = form
        return render(request, 'staffing/calendar.html', context, status=400)


class StaffingStaffView(StaffingStaffMixin, CalendarMixin, View):
    staff = True

    def get(self, request, employer_id):
        context = self.calendar_context(request)
        context['queue'] = StaffingPosition.objects.filter(request__branch__employer=self.employer).filter(
            Q(status__in=(Status.REQUESTED, Status.APPROVED), request__shift_date__gte=context['today'])
            | Q(status__in=(Status.REQUESTED, Status.APPROVED), replacement_for__isnull=False)
            | ~Q(change_request=''),
        ).select_related('request__branch').order_by('request__shift_date', 'pk')[:25]
        return render(request, 'staffing/calendar.html', context)

    def post(self, request, employer_id):
        name = request.POST.get('name', '').strip()
        if not name or len(name) > 120:
            messages.error(request, 'Enter a branch name up to 120 characters.')
        else:
            with transaction.atomic():
                Employer.objects.select_for_update().get(pk=employer_id)
                branch_id = request.POST.get('branch')
                if branch_id and (not branch_id.isascii() or not branch_id.isdecimal()):
                    raise PermissionDenied
                matching = self.employer.staffing_branches.filter(name__iexact=name)
                if branch_id:
                    branch = get_object_or_404(self.employer.staffing_branches, pk=branch_id)
                    if matching.exclude(pk=branch.pk).exists():
                        messages.error(request, 'This branch name is already in use.')
                    else:
                        branch.name = name
                        branch.save(update_fields=['name'])
                        messages.success(request, 'Branch renamed.')
                elif matching.exists():
                    messages.error(request, 'This branch name is already in use.')
                else:
                    branch = StaffingBranch.objects.create(employer=self.employer, name=name)
                    messages.success(request, 'Branch added.')
                    params = request.GET.copy()
                    params.update({'mode': 'multi', 'branch': branch.pk})
                    return redirect(f'{request.path}?{params.urlencode()}')
        return redirect(request.get_full_path())


class PositionMixin:
    staff = False

    def positions(self):
        return StaffingPosition.objects.filter(request__branch__employer=self.employer)

    def detail(self, request, position, *, attendance_form=None, proposal_form=None, status=200):
        applications = None
        if self.staff and position.status == Status.REQUESTED:
            applications = eligible_applications(position).select_related('locum', 'job').order_by('job_id', 'pk')
        shift = position.request
        today = timezone.localdate(timezone=LONDON)
        can_edit_attendance = not self.staff and shift.shift_date <= today and position.status in (
            Status.BOOKED, Status.ATTENDED,
        )
        if can_edit_attendance and attendance_form is None:
            attendance_form = AttendanceForm(initial={
                'actual_start': position.actual_start or shift.start_time,
                'actual_end': position.actual_end or shift.end_time,
                'break_minutes': position.break_minutes if position.break_minutes is not None else 0,
                'note': position.attendance_note,
            })
        return render(request, 'staffing/position.html', {
            'position': position, 'employer': self.employer, 'staff': self.staff,
            'applications': applications, 'today': today, 'can_edit_attendance': can_edit_attendance,
            'attendance_form': attendance_form, 'proposal_form': proposal_form or ProposalForm(),
            'events': position.events.select_related('actor').order_by('-created_at', '-pk') if self.staff else (),
            'change_resolution': position.events.filter(action__in=('resolve_change', 'cancel_booking')).order_by('-pk').first()
            if not self.staff and not position.change_request else None,
        }, status=status)

    def get(self, request, position_id, **kwargs):
        position = get_object_or_404(self.positions().select_related('request__branch'), pk=position_id)
        return self.detail(request, position)

    def post(self, request, position_id, **kwargs):
        action = request.POST.get('action')
        if self.staff and action in ('attended', 'issue'):
            raise PermissionDenied
        proposal = ProposalForm(request.POST) if self.staff and action == 'propose' else None
        attendance = AttendanceForm(request.POST) if action in ('attended', 'issue') else None
        try:
            with transaction.atomic():
                if proposal is not None and proposal.is_valid() and proposal.cleaned_data['application']:
                    # Match the lock order used by normal job approval.
                    job_id = Job.objects.filter(
                        employer=self.employer, appliedjob__pk=proposal.cleaned_data['application'],
                    ).values_list('pk', flat=True).first()
                    get_object_or_404(Job.objects.select_for_update(), pk=job_id)
                position = get_object_or_404(self.positions().select_for_update(), pk=position_id)
                detail = self.apply_action(request, position, action, proposal, attendance)
                position.save()
                record_event(position, request.user, action, detail)
            messages.success(request, 'Staffing position updated.')
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            position = get_object_or_404(self.positions().select_related('request__branch'), pk=position_id)
            return self.detail(request, position, attendance_form=attendance, proposal_form=proposal, status=400)
        if self.staff:
            return redirect('staffing_staff_position', employer_id=self.employer.pk, position_id=position_id)
        return redirect('staffing_position', position_id=position_id)

    def apply_action(self, request, position, action, proposal, attendance):
        if action == 'approve' and not self.staff and position.status == Status.PROPOSED:
            position.status = Status.APPROVED
        elif (action == 'decline' and not self.staff and position.status == Status.PROPOSED
              or action == 'withdraw' and self.staff and position.status in (Status.PROPOSED, Status.APPROVED)):
            name = position.candidate_name
            position.status = Status.REQUESTED
            position.candidate_name = ''
            position.client_rate = None
            position.proposal_note = ''
            position.application_id = None
            position.from_application = False
            return name
        elif action == 'cancel' and position.status == Status.REQUESTED:
            position.status = Status.CANCELLED
        elif action == 'propose' and self.staff and position.status == Status.REQUESTED:
            return self.propose(position, proposal)
        elif action == 'book' and self.staff and position.status == Status.APPROVED and not position.from_application:
            position.status = Status.BOOKED
        elif action == 'cancel_booking' and self.staff and position.status == Status.BOOKED and not position.from_application:
            note = request.POST.get('note', '').strip()
            if not note or len(note) > 500:
                raise ValidationError('Enter the reason for cancellation, up to 500 characters.')
            position.status = Status.CANCELLED
            position.change_request = ''
            return note
        elif action in ('attended', 'issue') and (
                position.status == Status.BOOKED
                or action == 'attended' and position.status == Status.ATTENDED):
            return self.attendance(position, action, attendance)
        elif action == 'request_replacement' and not self.staff and position.status == Status.ISSUE:
            replacement, created = StaffingPosition.objects.get_or_create(
                replacement_for=position, defaults={'request': position.request},
            )
            if not created:
                raise ValidationError('A replacement request already exists for this booking.')
            return f'Replacement position #{replacement.pk}'
        elif action == 'request_change' and not self.staff and position.status in (
                Status.PROPOSED, Status.APPROVED, Status.BOOKED):
            note = request.POST.get('note', '').strip()
            if not note or len(note) > 500 or position.change_request:
                raise ValidationError('Enter a change request up to 500 characters and wait for any open request to be resolved.')
            position.change_request = note
            return note
        elif action == 'resolve_change' and self.staff and position.change_request:
            note = request.POST.get('note', '').strip()
            if not note or len(note) > 500:
                raise ValidationError('Enter how the request was resolved, up to 500 characters.')
            position.change_request = ''
            return note
        else:
            raise ValidationError('This action is unavailable for the current booking status.')
        return ''

    def propose(self, position, form):
        if not form.is_valid():
            raise ValidationError([error for errors in form.errors.values() for error in errors])
        application_id = form.cleaned_data['application']
        name = form.cleaned_data['candidate_name']
        client_rate = form.cleaned_data['client_rate']
        if application_id:
            application = eligible_applications(position).select_related('locum', 'job').filter(pk=application_id).first()
            if not application or reserved_job_position(application.job):
                raise ValidationError('This application cannot be linked to this position.')
            if job_shift_dates(application.job) != [position.request.shift_date]:
                raise ValidationError('Choose an application for exactly this shift date.')
            if client_rate is not None and client_rate != application.job.client_billing_rate:
                raise ValidationError('Use the linked job’s client rate or leave the rate blank.')
            name = application.locum.get_full_name().strip() or application.locum.username
        position.application_id = application_id
        position.from_application = bool(application_id)
        position.candidate_name = name
        position.client_rate = client_rate
        position.proposal_note = form.cleaned_data['proposal_note']
        position.status = Status.PROPOSED
        return name

    def attendance(self, position, action, form):
        if position.request.shift_date > timezone.localdate(timezone=LONDON):
            raise ValidationError('Attendance can be recorded on or after the shift date.')
        if action == 'issue':
            # No-show recording only uses the note, even if time fields are incomplete.
            note = form.fields['note'].clean(form.data.get('note', ''))
            start = end = break_minutes = hours = None
        else:
            if not form.is_valid():
                raise ValidationError('Check the attendance details below.')
            data = form.cleaned_data
            note = data['note']
            start, end, break_minutes = data['actual_start'], data['actual_end'], data['break_minutes']
            hours = data['paid_hours']
            if start is not None or end is not None or break_minutes is not None or hours is None:
                if start is None or end is None:
                    raise ValidationError('Enter both the actual start and finish times.')
                if break_minutes is None:
                    raise ValidationError('Enter unpaid break minutes, or 0 if there was no unpaid break.')
                duration = position.shift_minutes(start, end)
                if duration <= break_minutes:
                    raise ValidationError('The shift time must be longer than the unpaid break.')
                hours = ((duration - break_minutes) / 60).quantize(Decimal('0.01'))
                if not hours:
                    raise ValidationError('Enter a shift with at least one minute of paid time.')
        position.status = action
        position.actual_start, position.actual_end = start, end
        position.break_minutes, position.paid_hours = break_minutes, hours
        position.attendance_note = note
        return note


class StaffingPositionView(PositionMixin, ManagerView):
    pass


class StaffingStaffPositionView(StaffingStaffMixin, PositionMixin, View):
    staff = True


def csv_cell(value):
    return "'" + value if value.lstrip()[:1] in ('=', '+', '-', '@') or value[:1] in ('\t', '\r', '\n') else value


class StaffingExportView(CalendarMixin, ManagerView):
    def get(self, request):
        context = self.calendar_context(request)
        if 'choose' in request.GET:
            context['export_form'] = AttendanceExportForm(initial={'period': 'week', 'start': context['selected_day']})
            return render(request, 'staffing/export.html', context)
        if 'period' in request.GET:
            form = AttendanceExportForm(request.GET)
            if not form.is_valid():
                context['export_form'] = form
                return render(request, 'staffing/export.html', context, status=400)
            first, last = form.date_range()
        else:
            first, last = context['first'], context['days'][-1]
        response = HttpResponse('\ufeff', content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="staffing-attendance-{first}-to-{last}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Branch', 'Date', 'Role', 'Candidate', 'Attendance', 'Scheduled start',
                         'Scheduled finish', 'Actual start', 'Actual finish', 'Unpaid break (minutes)',
                         'Hours on duty', 'Paid hours', 'Attendance note'])
        positions = StaffingPosition.objects.filter(
            request__branch__in=context['shown_branches'], request__shift_date__range=(first, last),
            status__in=(Status.ATTENDED, Status.ISSUE),
        ).select_related('request__branch').order_by('request__shift_date', 'request__start_time', 'pk')
        for position in positions.iterator():
            shift = position.request
            writer.writerow([csv_cell(shift.branch.name), shift.shift_date, shift.get_role_display(),
                             csv_cell(position.candidate_name), position.get_status_display(),
                             shift.start_time, shift.end_time, position.actual_start, position.actual_end,
                             position.break_minutes, position.gross_hours, position.paid_hours,
                             csv_cell(position.attendance_note)])
        return response
