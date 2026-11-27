import csv
from datetime import date, time, timedelta
from decimal import Decimal
from io import StringIO
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appAdmin.models import Admin, CustomUser, Employer
from locum.models import AppliedJob, Job, Locum
from locum.staffing_models import StaffingBranch, StaffingManager, StaffingPosition, StaffingRequest


@override_settings(STAFFING_PILOT_EMPLOYER_EMAIL='montu-office@example.test')
class StaffingPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employer = Employer.objects.create(
            email='montu-office@example.test', pharmacy_name='Montu Pharmacy')
        cls.other_employer = Employer.objects.create(
            email='other-office@example.test', pharmacy_name='Other Pharmacy')
        cls.branch = StaffingBranch.objects.create(employer=cls.employer, name='Montu Main')
        cls.other_branch = StaffingBranch.objects.create(employer=cls.other_employer, name='Other Site')
        cls.manager = CustomUser.objects.create_user(
            username='manager@example.test', email='manager@example.test', password='LocalDemo123!')
        cls.other_manager = CustomUser.objects.create_user(username='other-manager')
        StaffingManager.objects.create(user=cls.manager, employer=cls.employer)
        StaffingManager.objects.create(user=cls.other_manager, employer=cls.other_employer)
        cls.staff = Admin.objects.create(email='staff@example.test', first_name='Test', last_name='Staff')
        cls.locum = Locum.objects.create(
            email='casey@example.test', Email='casey@example.test', first_name='Casey', last_name='Demo',
            date_of_birth=date(1990, 1, 1), is_accepted=True, user_type='Dispenser')
        cls.today = timezone.localdate(timezone=ZoneInfo('Europe/London'))
        cls.job = Job.objects.create(
            employer=cls.employer, pharmacy_name=cls.employer.pharmacy_name, start_date=cls.today,
            end_date=cls.today, approved=True, dispenser_required=True, times_required='8',
            locum_rate=Decimal('18.00'), agency_fee=Decimal('4.00'), expenses_offered=Decimal('0.00'),
        )
        cls.application = AppliedJob.objects.create(job=cls.job, locum=cls.locum)

    def setUp(self):
        self.client.force_login(self.manager)
        self.staff_client = Client()
        self.staff_client.force_login(self.staff)

    def request_positions(self, quantity=1, **overrides):
        data = {'branch': self.branch.pk, 'shift_date': self.today, 'role': 'dispenser',
                'start_time': '09:00', 'end_time': '17:00', 'quantity': quantity, 'budget': '26.00',
                'submission_id': uuid4()}
        data.update(overrides)
        return self.client.post(reverse('staffing_calendar'), data)

    def manager_action(self, position, action, **fields):
        return self.client.post(reverse('staffing_position', args=[position.pk]), {'action': action, **fields})

    def staff_action(self, position, action, **fields):
        return self.staff_client.post(
            reverse('staffing_staff_position', args=[self.employer.pk, position.pk]),
            {'action': action, **fields},
        )

    def test_offline_request_approval_attendance_and_export(self):
        submission_id = uuid4()
        response = self.request_positions(2, submission_id=submission_id)
        self.assertRedirects(self.request_positions(2, submission_id=submission_id), response.url)
        self.assertEqual(response.status_code, 302)
        first, second = StaffingPosition.objects.order_by('pk')
        rota = self.client.get(response.url)
        self.assertContains(rota, 'Weekly staffing rota')
        staff_rota = self.staff_client.get(reverse('staffing_staff', args=[self.employer.pk]))
        self.assertContains(staff_rota, 'Needs staff action')
        self.staff_action(first, 'propose', candidate_name='=Offline Candidate', client_rate='28.50')
        details = self.client.get(reverse('staffing_position', args=[first.pk]))
        self.assertContains(details, 'Proposed client rate')
        self.assertNotContains(details, 'Propose candidate')
        self.manager_action(first, 'approve', client_rate='0.01', candidate_name='Forged')
        self.manager_action(first, 'attended', paid_hours='7.5')
        first.refresh_from_db()
        self.assertEqual(first.status, StaffingPosition.Status.APPROVED)
        self.assertEqual(first.client_rate, Decimal('28.50'))
        self.assertEqual(first.candidate_name, '=Offline Candidate')
        waiting = self.client.get(reverse('staffing_position', args=[first.pk]))
        self.assertContains(waiting, 'still needs to confirm')
        self.assertNotContains(waiting, 'value="issue"')
        self.staff_action(first, 'book')
        rota = self.client.get(response.url)
        self.assertContains(rota, 'Mark attended')
        self.assertContains(rota, 'Mark no-show')
        self.manager_action(first, 'attended', paid_hours='7.5')
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.paid_hours, Decimal('7.50'))
        self.assertEqual(second.status, StaffingPosition.Status.REQUESTED)
        self.assertEqual(list(first.events.values_list('action', flat=True)), ['propose', 'approve', 'book', 'attended'])
        export = self.client.get(reverse('staffing_export'))
        self.assertContains(export, "'=Offline Candidate")
        self.assertContains(export, '7.50')
        self.assertNotContains(export, '28.50')
        self.assertNotContains(export, 'Amount due')

    def test_multi_date_request_creates_independent_positions_and_is_safe_to_retry(self):
        later = self.today + timedelta(days=9)
        submission = {'submission_id': uuid4(), 'shift_dates': [later, self.today, later], 'role': 'anp_nurse'}
        response = self.request_positions(2, **submission)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(self.request_positions(2, **submission), response.url)
        first, second = StaffingRequest.objects.order_by('shift_date')
        self.assertEqual((first.shift_date, second.shift_date), (self.today, later))
        self.assertEqual(second.first_request_id, first.pk)
        self.assertEqual(first.get_role_display(), 'ANP Nurse')
        self.assertEqual((first.positions.count(), second.positions.count()), (2, 2))
        self.assertEqual(self.client.get(response.url).context['daily_positions'][0].request_id, first.pk)
        later_rota = self.client.get(reverse('staffing_calendar'), {'week': later, 'day': later})
        self.assertEqual({p.request_id for p in later_rota.context['daily_positions']}, {second.pk})
        for position in (first.positions.first(), second.positions.first()):
            self.staff_action(position, 'propose', candidate_name='Local Candidate')
            self.manager_action(position, 'approve')
            self.staff_action(position, 'book')
            self.manager_action(position, 'issue')
        self.assertEqual(first.positions.first().status, StaffingPosition.Status.ISSUE)
        self.assertEqual(second.positions.first().status, StaffingPosition.Status.BOOKED)
        export = self.client.get(reverse('staffing_export'))
        self.assertContains(export, 'No-show / issue')
        self.assertNotContains(export, later.isoformat())

    def test_invalid_multi_date_request_does_not_create_partial_positions(self):
        response = self.request_positions(2, shift_dates=[self.today, self.today - timedelta(days=1)])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StaffingRequest.objects.count(), 0)
        self.assertEqual(StaffingPosition.objects.count(), 0)

    def test_proposal_note_and_next_morning_attendance_are_visible_to_both_roles(self):
        self.request_positions()
        position = StaffingPosition.objects.get()
        StaffingRequest.objects.filter(pk=position.request_id).update(shift_date=self.today - timedelta(days=1))
        self.staff_action(position, 'propose', candidate_name='Casey', proposal_note='Available for this shift.')
        detail = reverse('staffing_position', args=[position.pk])
        self.assertContains(self.client.get(detail), 'Available for this shift.')
        self.manager_action(position, 'approve')
        self.staff_action(position, 'book')
        rejected = self.manager_action(position, 'attended', actual_start='22:00', actual_end='06:00',
                                       break_minutes='480')
        self.assertContains(rejected, 'shift time must be longer than the unpaid break', status_code=400)
        self.manager_action(position, 'attended', actual_start='22:00', actual_end='06:00',
                            break_minutes='30', note='Overnight cover')
        position.refresh_from_db()
        self.assertEqual(position.gross_hours, Decimal('8.00'))
        self.assertEqual(position.paid_hours, Decimal('7.50'))
        self.manager_action(position, 'attended', actual_start='22:00', actual_end='06:00', break_minutes='45')
        position.refresh_from_db()
        self.assertEqual(position.paid_hours, Decimal('7.25'))
        admin = self.staff_client.get(reverse('staffing_staff_position', args=[self.employer.pk, position.pk]))
        self.assertContains(admin, 'Attendance recorded by Montu')
        self.assertContains(admin, '45 min')
        self.assertContains(admin, '(next day)')
        self.assertNotContains(admin, 'data-attendance-form')
        self.assertEqual(self.staff_action(position, 'attended', paid_hours='3', note='Edit attempt').status_code, 403)
        self.assertEqual(self.staff_action(position, 'issue', note='Edit attempt').status_code, 403)
        position.refresh_from_db()
        self.assertEqual(position.paid_hours, Decimal('7.25'))
        export = self.client.get(reverse('staffing_export'), {'period': 'day', 'start': position.request.shift_date})
        self.assertContains(export, '22:00:00,06:00:00,45,8.00,7.25')

    def test_manager_records_multiple_shifts_for_the_same_candidate_and_exports_each(self):
        yesterday = self.today - timedelta(days=1)
        shifts = ((yesterday, '09:00', '17:00', '30', '7.50'), (self.today, '10:00', '16:00', '15', '5.75'))
        for day, start, finish, breaks, _ in shifts:
            self.request_positions()
            position = StaffingPosition.objects.latest('pk')
            StaffingRequest.objects.filter(pk=position.request_id).update(shift_date=day)
            self.staff_action(position, 'propose', candidate_name='Casey Demo')
            self.manager_action(position, 'approve')
            self.staff_action(position, 'book')
            staff_booking = self.staff_client.get(
                reverse('staffing_staff_position', args=[self.employer.pk, position.pk]))
            self.assertContains(staff_booking, 'Awaiting attendance from Montu.')
            self.assertNotContains(staff_booking, 'data-attendance-form')
            self.assertEqual(self.staff_action(position, 'issue').status_code, 403)
            response = self.manager_action(position, 'attended', actual_start=start, actual_end=finish,
                                           break_minutes=breaks)
            self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse('staffing_export'), {
            'period': 'range', 'start': yesterday.isoformat(), 'end': self.today.isoformat(),
        })
        rows = list(csv.DictReader(StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(len(rows), 2)
        for row, (day, start, finish, breaks, hours) in zip(rows, shifts):
            self.assertEqual(
                (row['Candidate'], row['Date'], row['Actual start'], row['Actual finish'],
                 row['Unpaid break (minutes)'], row['Paid hours']),
                ('Casey Demo', day.isoformat(), f'{start}:00', f'{finish}:00', breaks, hours),
            )

    def test_no_show_replacement_keeps_original_attendance_and_is_queued(self):
        self.request_positions()
        position = StaffingPosition.objects.get()
        self.staff_action(position, 'propose', candidate_name='Original')
        self.manager_action(position, 'approve')
        self.staff_action(position, 'book')
        StaffingRequest.objects.filter(pk=position.request_id).update(shift_date=self.today - timedelta(days=1))
        self.manager_action(position, 'issue', note='Did not arrive')
        self.assertContains(self.client.get(reverse('staffing_position', args=[position.pk])), 'Request replacement')
        self.manager_action(position, 'request_replacement')
        duplicate = self.manager_action(position, 'request_replacement')
        self.assertEqual(duplicate.status_code, 400)
        position.refresh_from_db()
        self.assertEqual(position.status, StaffingPosition.Status.ISSUE)
        self.assertEqual(position.attendance_note, 'Did not arrive')
        replacement = StaffingPosition.objects.get(replacement_for=position)
        self.assertEqual(replacement.request_id, position.request_id)
        self.assertEqual(replacement.status, StaffingPosition.Status.REQUESTED)
        rota = self.staff_client.get(reverse('staffing_staff', args=[self.employer.pk]))
        self.assertIn(replacement, rota.context['queue'])

    def test_export_periods_filter_by_date_and_branch(self):
        other_branch = StaffingBranch.objects.create(employer=self.employer, name='North Branch')
        for name, day, branch in (
            ('MonCandidate', date(2026, 1, 26), self.branch),
            ('SatCandidate', date(2026, 1, 31), self.branch),
            ('SunCandidate', date(2026, 2, 1), self.branch),
            ('NorthCandidate', date(2026, 1, 31), other_branch),
        ):
            shift = StaffingRequest.objects.create(
                branch=branch, requested_by=self.manager, shift_date=day,
                start_time=time(9), end_time=time(17), role='dispenser')
            StaffingPosition.objects.create(request=shift, candidate_name=name, status=StaffingPosition.Status.ATTENDED)
        url = reverse('staffing_export')
        params = {'mode': 'multi', 'branch': self.branch.pk, 'start': '2026-01-31'}
        for period, included in {
            'day': ('SatCandidate',), 'week': ('MonCandidate', 'SatCandidate', 'SunCandidate'),
            'month': ('MonCandidate', 'SatCandidate'), 'range': ('SatCandidate', 'SunCandidate'),
        }.items():
            result = self.client.get(url, {**params, 'period': period, 'end': '2026-02-01'})
            for name in ('MonCandidate', 'SatCandidate', 'SunCandidate', 'NorthCandidate'):
                with self.subTest(period=period, candidate=name):
                    (self.assertContains if name in included else self.assertNotContains)(result, name)
        invalid = self.client.get(url, {**params, 'period': 'range', 'end': '2026-01-30'})
        self.assertContains(invalid, 'Choose an end date on or after the start date.', status_code=400)

    def test_request_form_includes_clinical_and_montu_specific_roles(self):
        response = self.client.get(reverse('staffing_calendar'))
        for role in ('Practice Nurse', 'ANP Nurse', 'GP', 'Optometrist', 'Dispensing Optician',
                     'Pharmacist', 'Pharmacy Technician', 'Dispenser', 'Packaging Assistant',
                     'ACD – Accuracy Checking Dispenser', 'ACT – Accuracy Checking Technician'):
            self.assertContains(response, role)

    def test_admin_and_staff_can_open_montu_portal_before_manager_provisioning(self):
        StaffingManager.objects.filter(employer=self.employer).delete()
        for is_admin in (True, False):
            with self.subTest(is_admin=is_admin):
                self.staff.is_admin = is_admin
                self.staff.save(update_fields=['is_admin'])
                dashboard = self.staff_client.get(reverse('admin'))
                self.assertContains(dashboard, 'Montu Staffing Portal Handling')
                portal = self.staff_client.get(reverse('staffing_staff_index'), follow=True)
                self.assertContains(portal, self.employer.pharmacy_name)
                self.assertContains(portal, '+ Add branch')
        self.assertEqual(self.client.get(reverse('staffing_calendar')).status_code, 404)

    def test_linked_application_requires_manager_approval_then_uses_normal_booking(self):
        self.request_positions(2)
        first, second = StaffingPosition.objects.order_by('pk')
        self.staff_action(first, 'propose', application=self.application.pk, client_rate='22.00')
        self.staff_action(second, 'propose', application=self.application.pk)
        second.refresh_from_db()
        self.assertEqual(second.status, StaffingPosition.Status.REQUESTED)
        approve_url = reverse('approveappliedjob', args=[self.application.pk])
        self.staff_client.post(approve_url)
        self.application.refresh_from_db()
        self.assertFalse(self.application.approved)
        self.manager_action(first, 'approve')
        response = self.staff_client.post(approve_url, {'source': 'staffing'})
        self.assertRedirects(response, reverse('staffing_staff_position', args=[self.employer.pk, first.pk]))
        self.job.refresh_from_db()
        self.application.refresh_from_db()
        first.refresh_from_db()
        self.assertEqual(self.job.locum_id, self.locum.pk)
        self.assertTrue(self.application.approved)
        self.assertEqual(first.status, StaffingPosition.Status.BOOKED)
        self.assertEqual(len(mail.outbox), 2)
        self.staff_client.post(approve_url)
        self.assertEqual(len(mail.outbox), 2)

    def test_manager_role_and_employer_are_enforced_on_server(self):
        self.assertEqual(self.request_positions(branch=self.other_branch.pk).status_code, 400)
        self.assertEqual(self.request_positions(shift_date=self.today - timedelta(days=1)).status_code, 400)
        self.request_positions()
        position = StaffingPosition.objects.get()
        self.manager_action(position, 'propose', candidate_name='Forged')
        position.refresh_from_db()
        self.assertEqual(position.status, StaffingPosition.Status.REQUESTED)
        self.assertEqual(self.client.get(reverse('staffing_staff_index')).status_code, 403)
        self.assertEqual(self.client.get(reverse('locum_detail', args=[self.locum.pk])).status_code, 403)
        self.assertEqual(self.client.get(f'/appAdmin/locums/{self.locum.pk}/edit/').status_code, 403)
        self.assertEqual(self.client.get(reverse('job_details', args=[self.job.pk])).status_code, 403)
        self.client.force_login(self.other_manager)
        self.assertEqual(self.client.get(reverse('staffing_position', args=[position.pk])).status_code, 404)
        self.assertEqual(self.manager_action(position, 'cancel').status_code, 404)
        self.assertEqual(self.client.get(reverse('staffing_export')).status_code, 404)
        self.assertEqual(self.staff_client.get(reverse('staffing_staff', args=[self.other_employer.pk])).status_code, 404)

    def test_single_and_multiple_branch_views_filter_rota_and_expose_dialogs(self):
        second_branch = StaffingBranch.objects.create(employer=self.employer, name='North Branch')
        self.request_positions()
        self.request_positions(branch=second_branch.pk)
        url = reverse('staffing_calendar')
        single = self.client.get(url, {'mode': 'single'})
        self.assertEqual([row[0] for row in single.context['rows']], [self.branch])
        self.assertEqual(list(single.context['form'].fields['branch'].queryset), [self.branch])
        self.assertNotContains(single, 'staffing-location-form')
        self.assertContains(single, 'id="staff-request"')
        self.assertContains(single, 'id="staffing-booking"')
        self.assertContains(single, 'name="submission_id"')
        self.assertNotContains(single, '+ Add branch')
        multiple = self.client.get(url, {'mode': 'multi'})
        self.assertEqual({row[0] for row in multiple.context['rows']}, {self.branch, second_branch})
        self.assertContains(multiple, 'Showing all 2 branches.')
        selected = self.client.get(url, {'mode': 'multi', 'branch': second_branch.pk})
        self.assertEqual([row[0] for row in selected.context['rows']], [second_branch])
        self.assertContains(selected, 'Showing North Branch.')
        self.assertContains(selected, f'<option value="{second_branch.pk}" selected>North Branch</option>', html=True)
        self.assertEqual([item.request.branch_id for item in selected.context['daily_positions']], [second_branch.pk])
        self.assertIn(f'branch={second_branch.pk}', selected.context['query'])
        self.assertContains(self.staff_client.get(reverse('staffing_staff', args=[self.employer.pk])), '+ Add branch')

    @override_settings(DEBUG=True, STAFFING_PILOT_EMPLOYER_EMAIL='demo.montu.employer@locumsmart.test')
    def test_demo_admin_sees_existing_permission_gated_cards(self):
        call_command('seed_staffing_demo')
        demo_admin = Admin.objects.get(email='demo.staffing.admin@locumsmart.test')
        self.staff_client.force_login(demo_admin)
        dashboard = self.staff_client.get(reverse('admin'))
        for card in ('See Your Locum Request Here', 'Register Your Employers Here',
                     'Register Your Staff Members here', 'Montu Staffing Portal Handling'):
            self.assertContains(dashboard, card)

    def test_invited_manager_can_set_password_and_see_profile_card(self):
        email = 'invited@example.test'
        call_command('provision_staffing_manager', self.employer.pk, email, branch=self.branch.name)
        client = Client()
        client.post(reverse('fpEmail'), {'email': email, 'type': 'EmployerManager'})
        self.assertEqual(len(mail.outbox), 1)
        link = next(line.split('http://testserver', 1)[1]
                    for line in mail.outbox[0].body.splitlines()
                    if 'http://testserver/changePassword/' in line)
        client.post(link, {'password': 'LocalDemo123!', 'confirm-password': 'LocalDemo123!'})
        login = client.post(reverse('login'), {'email': email, 'password': 'LocalDemo123!', 'type': 'EmployerManager'})
        self.assertRedirects(login, reverse('staffing_profile'))
        self.assertContains(client.get(reverse('staffing_profile')), 'Open Staffing Portal')
