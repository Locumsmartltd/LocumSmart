from django.views.generic import ListView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView, UpdateView
from django.db.models import Q
from django.views import View
from django.contrib import messages
from locum.models import *
from django.core.mail import send_mail, EmailMessage
from appAdmin.models import *
from structure.models import Testimonial
from structure.decorators import admin_required
from structure.passwords import SITE_URL
from structure.emails import send_branded_email, send_approval_email
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from datetime import datetime, timedelta
from django.views.generic.detail import DetailView
from django.utils.html import strip_tags
import json
from django.template.loader import render_to_string
from io import BytesIO
from django.utils.crypto import get_random_string
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import random
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from .utils import (
    generate_gorgemead_invoice_pdf,
    generate_fairgreen_invoice_pdf,
    generate_tesco_invoice_pdf,
    generate_cohens_invoice_pdf,
)
import os
import mimetypes
from collections import deque
from django.http import Http404, FileResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils._os import safe_join
import logging

# 'django.*' loggers are written to the error log file configured in settings.LOGGING
logger = logging.getLogger('django.invoices')


class AdminMediaView(View):
    def get(self, request, file_path):
        if not hasattr(request.user, 'admin'):
            raise PermissionDenied

        try:
            full_path = safe_join(settings.MEDIA_ROOT, file_path)
        except Exception:
            raise Http404("Invalid file path")

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            raise Http404("File not found")

        content_type, _ = mimetypes.guess_type(full_path)
        response = FileResponse(open(full_path, 'rb'), content_type=content_type or 'application/octet-stream')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(full_path)}"'
        return response


@method_decorator(login_required, name='dispatch')
class SystemLogsView(View):
    template_name = 'systemLogs.html'
    max_lines = 200

    def get(self, request):
        if not hasattr(request.user, 'admin') or not request.user.admin.is_admin:
            raise PermissionDenied

        log_dir = getattr(settings, 'LOG_DIR', settings.BASE_DIR / 'logs')
        logs = {
            'info': self._read_recent_lines(os.path.join(log_dir, 'app.log')),
            'error': self._read_recent_lines(os.path.join(log_dir, 'error.log')),
            'security': self._read_recent_lines(os.path.join(log_dir, 'security.log')),
            'build_errors': self._read_recent_lines(os.path.join(log_dir, 'building-errors.log')),
        }

        context = {
            'max_lines': self.max_lines,
            'logs': logs,
        }
        return render(request, self.template_name, context)

    def _read_recent_lines(self, file_path):
        if not os.path.exists(file_path):
            return {
                'path': file_path,
                'exists': False,
                'content': 'Log file not found yet.',
            }

        with open(file_path, 'r', encoding='utf-8', errors='replace') as file_handle:
            lines = deque(file_handle, maxlen=self.max_lines)

        content = ''.join(lines).strip()
        if not content:
            content = 'No log entries yet.'

        return {
            'path': file_path,
            'exists': True,
            'content': content,
        }


def testimonials_list(request):
    testimonials = Testimonial.objects.all()
    return render(request, 'testimonials_list.html', {'testimonials': testimonials})

def add_or_edit_testimonial(request):
    if request.method == 'POST':
        id = request.POST.get('id', None)
        name = request.POST.get('name')
        source = request.POST.get('source')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if id:  # Editing existing testimonial
            testimonial = get_object_or_404(Testimonial, id=id)
            testimonial.name = name
            testimonial.source = source
            testimonial.rating = rating
            testimonial.comment = comment
            testimonial.save()
            messages.success(request, 'Testimonial updated successfully.')
        else:  # Adding new testimonial
            Testimonial.objects.create(
                name=name,
                source=source,
                rating=rating,
                comment=comment
            )
            messages.success(request, 'Testimonial added successfully.')
        return redirect('testimonials_list')

def delete_testimonial(request, id):
    testimonial = get_object_or_404(Testimonial, id=id)
    testimonial.delete()
    messages.success(request, 'Testimonial deleted successfully.')
    return redirect('testimonials_list')


def generate_unique_invoice_no():
    while True:
        invoice_no = random.randint(10000000, 99999999)
        if not EmailTrackingLog.objects.filter(invoice_no=invoice_no).exists():
            return invoice_no


@method_decorator(login_required, name='dispatch')
class AdminView(View):
    template_name = 'admin.html'

    def get(self, request):
        pharmacist_count = Locum.objects.filter(user_type='Pharmacist').count()
        technician_count = Locum.objects.filter(
            Q(user_type='Technician') | Q(user_type='Dispenser')).count()
        nurse_count = Locum.objects.filter(
            Q(user_type='Nurse') | Q(user_type='ANPNurse')).count()
        gp_count = Locum.objects.filter(user_type='GP').count()

        context = {
            'pharmacist_count': pharmacist_count,
            'technician_count': technician_count,
            'nurse_count': nurse_count,
            'gp_count': gp_count,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class EmployerRequestsView(View):
    template_name = 'seeEmployerRequest.html'

    def get(self, request):
        jobs = Job.objects.filter(approved=False, rejected=False)
        context = {
            'jobs': jobs
        }
        return render(request, self.template_name, context)

    def post(self, request):
        job_id = request.POST.get('job_id')
        job = get_object_or_404(Job, id=job_id)
        job.name = request.POST.get('name')
        job.times_required = request.POST.get('times_required')
        job.start_date = request.POST.get('start_date')
        job.end_date = request.POST.get('end_date')
        job.locum_rate = request.POST.get('locum_rate')
        job.any_other_information = request.POST.get('any_other_information')
        job.save()
        return redirect('employerRequests')


class ApproveJobView(View):
    def post(self, request, job_id):
        job = Job.objects.get(pk=job_id)
        job.approved = True
        job.rejected = False
        job.booking = ''
        job.agency_fee = request.POST.get('agency_fee')
        job.branch_no = request.POST.get('branch_no')
        job.save()

        employer_email = job.employer.email
        admin_email = settings.EMAIL_HOST_USER
        recipient_list = [employer_email]
        subject = 'Employer Request Approved'

        message = f"""
    Dear {job.employer.first_name} {job.employer.last_name},

    We are pleased to inform you that your Employer Request for the following position has been approved:

    **Position Details:**
    - Pharmacy Name: {job.pharmacy_name}
    - City: {job.county}
    - Locum Role Required: {self.get_locum_roles(job)}
    - Rate: £{job.locum_rate}/hr
    - Start Date: {job.start_date.strftime('%d %B %Y')}
    - End Date: {job.end_date.strftime('%d %B %Y')}

    Please note that any cancellation within 72 hours prior to the booking may result in the Pharmacy claiming loss of earnings, and our fees will still be payable. It is also advised that once you confirm a booking, we remove the shift from our listings, and it would not be appreciated if a cancellation is made for a better offer elsewhere.
    As a registered employer with LocumSmart Ltd, you are bound by the terms and conditions agreed upon during registration. Should you be offered any further bookings directly by the Pharmacy, please ensure that you inform our Coordinator before proceeding, as per our agreed terms.
    Please also note that Sundays, Bank Holidays, and specific days like Christmas Eve, New Year's Eve, New Year's Day, and Christmas Day are not considered in the 72-hour notice period. The notice period is calculated from Monday to Friday (9 am-5 pm) and Saturday (9 am-3 pm). Notices must be provided via email.
    Should you require further information, please refer to the Terms of Engagement agreed upon during registration. A hard copy can be provided upon request.
    We look forward to a successful collaboration.
    
    Best regards,
    Ammar
    LocumSmart Ltd
    Providing 8000+ Locums & Permanent Staff across the UK 🇬🇧 
    General Practitioners | Doctors | Physician Associates | Pharmacists | Technicians and Dispensers | Hospitals, and Pharma | Staffing & Recruiting
    Email: info@locum-smart.co.uk
    Phone: +44 7534749465
        """
        # send_mail(subject, message, admin_email, recipient_list)
        return redirect('employerRequests')

    def get_locum_roles(self, job):
        roles = []
        if job.pharmacist_required:
            roles.append("Pharmacist")
        if job.technician_required:
            roles.append("Technician")
        if job.dispenser_required:
            roles.append("Dispenser")
        if job.nurse_required:
            roles.append("Nurse")
        if job.anp_nurse_required:
            roles.append("ANP Nurse")
        if job.gp_required:
            roles.append("GP")
        return ', '.join(roles)



class DisapproveJobView(View):
    def post(self, request, job_id):
        job = Job.objects.get(pk=job_id)
        job.rejected = True
        job.save()

        employer_email = job.employer.email
        admin_email = settings.EMAIL_HOST_USER
        recipient_list = [employer_email]
        subject = 'Employer Request Disapproved'

        message = f"""
    Dear {job.employer.first_name} {job.employer.last_name},

    We regret to inform you that your Employer Request for the following position has not been approved:

    **Position Details:**
    - Pharmacy Name: {job.pharmacy_name}
    - City: {job.county}
    - Locum Role Required: {self.get_locum_roles(job)}
    - Rate: £{job.locum_rate}/hr

    While we understand this may be disappointing, we encourage you to review your request and resubmit with any necessary adjustments. We are committed to helping you find the right fit for your needs.
    Please remember that any cancellation within 72 hours prior to a confirmed booking may result in the Pharmacy claiming loss of earnings, and our fees will still be payable. Also, cancellations made for a better offer elsewhere are discouraged as it impacts our ability to serve other clients effectively.
    As a registered employer with LocumSmart Ltd, you are bound by the terms and conditions agreed upon during registration. If you have any questions or need further assistance, please do not hesitate to contact us.
    
    Best regards,
    Ammar
    LocumSmart Ltd
    Providing 8000+ Locums & Permanent Staff across the UK 🇬🇧 
    General Practitioners | Doctors | Physician Associates | Pharmacists | Technicians and Dispensers | Hospitals, and Pharma | Staffing & Recruiting
    Email: info@locum-smart.co.uk
    Phone: +44 7534749465
        """
        # send_mail(subject, message, admin_email, recipient_list)
        return redirect('employerRequests')

    def get_locum_roles(self, job):
        roles = []
        if job.pharmacist_required:
            roles.append("Pharmacist")
        if job.technician_required:
            roles.append("Technician")
        if job.dispenser_required:
            roles.append("Dispenser")
        if job.nurse_required:
            roles.append("Nurse")
        if job.anp_nurse_required:
            roles.append("ANP Nurse")
        if job.gp_required:
            roles.append("GP")
        return ', '.join(roles)



@method_decorator(login_required, name='dispatch')
class RegisterEmployer(View):
    template_name = 'registerEmployer.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        post_code = request.POST.get('post_code')

        # Check if an Employer with this email and post_code already exists
        if Employer.objects.filter(email=email, post_code=post_code).exists():
            # Employer with this email and post_code already registered
            messages.error(
                request, 'Employer with this email and postal code is already registered.')
        else:
            # Create new Employer object and save
            employer = Employer(
                first_name=request.POST.get('Firstname'),
                last_name=request.POST.get('Lastname'),
                email=request.POST.get('email'),
                pharmacy_name= request.POST.get('pharmacy_name'),
                street_address = request.POST.get('street_address'),
                manager_name = request.POST.get('manager_name'),
                phone_number=request.POST.get('telephone'),
                post_code=request.POST.get('post_code'),
                city=request.POST.get('city')
            )
            employer.save()
            messages.success(
                request, 'Employer has been registered successfully.')

        # Redirect to the registration page
        return redirect('registerEmployer')


@method_decorator(login_required, name='dispatch')
class DeleteLocum(View):
    template_name = 'deleteLocum.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        # Handle both bulk and individual deletion
        locum_ids = request.POST.getlist('selected_locums')  # Get a list of selected locum IDs for bulk deletion
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        user_type = request.POST.get('type')

        if locum_ids:
            # Bulk delete based on IDs
            Locum.objects.filter(id__in=locum_ids).delete()
            return redirect('locumRequests')  # Redirect to the delete locum page

        elif email and telephone and user_type:
            # Individual deletion based on specific details
            locum = get_object_or_404(Locum, email=email, telephone=telephone, user_type=user_type)
            locum.delete()
            return redirect('locumRequests')  # Redirect to the delete locum page

        else:
            # Handle the case where neither method is valid
            return redirect('seeLocum')  # Redirect to the delete locum page
    

@method_decorator(login_required, name='dispatch')
class AcceptLocum(View):

    def post(self, request):
        # Retrieve selected locum IDs from the request
        locum_ids = request.POST.getlist('selected_locums')

        if not locum_ids:
            messages.error(request, "No locums selected for approval.")
            return redirect('locumRequests')

        # Fetch locums based on the provided IDs
        locums = Locum.objects.filter(id__in=locum_ids)

        approved_emails = []
        failed_emails = []

        for locum in locums:
            # Update is_accepted to True
            locum.is_accepted = True
            locum.save()

            # Send the approval / welcome email
            try:
                send_approval_email(locum)
                approved_emails.append(locum.Email)
            except Exception as e:
                failed_emails.append((locum.Email, str(e)))

        # Add success and error messages
        if approved_emails:
            messages.success(request, f"Successfully approved locums: {', '.join(approved_emails)}")
        if failed_emails:
            failed_emails_formatted = ', '.join([f"{email} (Error: {error})" for email, error in failed_emails])
            messages.error(request, f"Failed to send approval emails to: {failed_emails_formatted}")

        return redirect('locumRequests')


@method_decorator(login_required, name='dispatch')
class LocumListView(View):
    template_name = 'seeLocums.html'

    def get(self, request):
        search_query = request.GET.get('search', '')
        locums = Locum.objects.filter(is_accepted=True)  # Filter by is_accepted=False

        if search_query:
            # Split the search query by comma to extract user_type and location
            search_terms = [term.strip() for term in search_query.split(',')]

            if len(search_terms) == 1:
                # Search for user_type or location if only one term is provided
                locums = locums.filter(
                    Q(user_type__icontains=search_terms[0]) |
                    Q(county__icontains=search_terms[0]) |
                    Q(Email__icontains=search_terms[0]) |
                    Q(firstname__icontains=search_terms[0]) |
                    Q(lastname__icontains=search_terms[0]) |
                    Q(username__icontains=search_terms[0])
                )
            elif len(search_terms) >= 2:
                # Search for user_type and location (county) if both terms are provided
                user_type_query = search_terms[0]
                # Reconstruct the location part
                location_query = ','.join(search_terms[1:])

                locums = locums.filter(
                    Q(user_type__icontains=user_type_query) &
                    Q(county__icontains=location_query)
                )

        context = {'locums': locums, 'search_query': search_query}
        return render(request, self.template_name, context)
    
    
@method_decorator(login_required, name='dispatch')
class LocumRequestsListView(View):
    template_name = 'seeLocumRequests.html'

    def get(self, request):
        search_query = request.GET.get('search', '')
        locums = Locum.objects.filter(is_accepted=False)  # Filter by is_accepted=False

        if search_query:
            # Split the search query by comma to extract user_type and location
            search_terms = [term.strip() for term in search_query.split(',')]

            if len(search_terms) == 1:
                # Search for user_type or location if only one term is provided
                locums = locums.filter(
                    Q(user_type__icontains=search_terms[0]) |
                    Q(county__icontains=search_terms[0]) |
                    Q(Email__icontains=search_terms[0]) |
                    Q(firstname__icontains=search_terms[0]) |
                    Q(lastname__icontains=search_terms[0]) |
                    Q(username__icontains=search_terms[0])
                )
            elif len(search_terms) >= 2:
                # Search for user_type and location (county) if both terms are provided
                user_type_query = search_terms[0]
                # Reconstruct the location part
                location_query = ','.join(search_terms[1:])

                locums = locums.filter(
                    Q(user_type__icontains=user_type_query) &
                    Q(county__icontains=location_query)
                )

        context = {'locums': locums, 'search_query': search_query}
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class EmployerListView(View):
    template_name = 'seeEmployers.html'

    def get(self, request):
        search_query = request.GET.get('search', '')
        employers = Employer.objects.all()
        if search_query:
            employers = employers.filter(
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(pharmacy_name__icontains=search_query) |
                Q(username__icontains=search_query)
            )
        context = {
            'employers': employers,
            'search_query': search_query,
        }
        return render(request, self.template_name, context)

@method_decorator(login_required, name='dispatch')
class LocumDetailView(DetailView):
    model = Locum
    template_name = 'locumDetails.html'
    context_object_name = 'locum'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        locum = self.get_object()
        context['expiry_dates'] = self.get_expiry_dates(locum)
        return context

    def get_expiry_dates(self, locum):
        expiry_dates = {
            'gphc_number': locum.gphc_number_expiry,
            'passport_copy': locum.passport_expiry_date,
            'visa_residence_permit': locum.visa_expiry,
            'insurance': locum.insurance_expiry_date,
            # Add more mappings as needed
        }

        current_date = datetime.now().date()
        for key, date in expiry_dates.items():
            if date:
                days_diff = (date - current_date).days
                if days_diff > 60:
                    expiry_dates[key] = {'date': date, 'css_class': 'expiry-green'}
                elif 30 < days_diff <= 60:
                    expiry_dates[key] = {'date': date, 'css_class': 'expiry-orange'}
                else:
                    expiry_dates[key] = {'date': date, 'css_class': 'expiry-red'}
            else:
                expiry_dates[key] = {'date': None, 'css_class': ''}
        return expiry_dates


@method_decorator(login_required, name='dispatch')
class RegisterStaff(View):
    template_name = 'registerStaff.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        # Retrieve form data
        firstname = request.POST.get('Firstname')
        lastname = request.POST.get('Lastname')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if staff with provided email already exists
        if Admin.objects.filter(email=email).exists():
            messages.error(
                request, f"Staff with email '{email}' already exists.")
            return redirect('registerStaff')  # Redirect to registration page

        # Create new employer if email is unique
        new_staff = Admin(
            first_name=firstname,
            last_name=lastname,
            email=email,
            # You may want to handle password hashing before saving (not recommended to store passwords in plain text)
            password=password
        )
        new_staff.save()

        messages.success(request, "Staff registered successfully.")
        return redirect('registerStaff')


@method_decorator(login_required, name='dispatch')
class StaffListView(View):
    template_name = 'seeStaff.html'

    def get(self, request):
        search_query = request.GET.get('search', '')
        staffs = Admin.objects.all()
        if search_query:
            staffs = staffs.filter(
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query)
            )
        perm_array = []
        for staff in staffs:

            perm1 = staff.has_perm('appAdmin.can_register_employer')
            perm2 = staff.has_perm('appAdmin.can_delete_locum')
            perm3 = staff.has_perm('appAdmin.can_register_staff')
            perm_info = [perm1, perm2, perm3]
            perm_array.append(perm_info)

        staff_perms = zip(staffs, perm_array)
        context = {
            'staff_perms': staff_perms,
            'search_query': search_query,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        staff_id = request.POST.get('staff_id')
        permission_name = request.POST.get('permission_name')
        action = request.POST.get('action')

        if staff_id and permission_name and action in ['grant_permission', 'revoke_permission']:
            staff = Admin.objects.get(id=staff_id)

            permission = Permission.objects.get(codename=permission_name)

            if action == 'grant_permission':
                staff.user_permissions.add(permission)
            elif action == 'revoke_permission':
                staff.user_permissions.remove(permission)

        return redirect('staffList')


@login_required
def job_applications(request):
    # Fetch all applied jobs where approved is False and rejected is False
    applied_jobs = AppliedJob.objects.filter(approved=False, rejected=False)

    # Prepare context data to pass to the template
    context = {
        'applied_jobs': applied_jobs
    }

    return render(request, 'job_applications.html', context)


def approveappliedjob(request, applied_job_id):
    applied_job = get_object_or_404(AppliedJob, id=applied_job_id)

    # Check if the applied job has a related Job
    if not applied_job.job:
        return redirect('job_applications')

    # Mark the applied job as approved
    applied_job.approved = True
    applied_job.save()

    # Update related Job object
    job = applied_job.job
    job.applied_status = True
    job.locum = applied_job.locum
    job.date_of_booking_email = datetime.now().date()
    job.save()

    if job.discrete_dates:
        date_rows = [('Discrete Dates', ', '.join(
            datetime.strptime(date, '%Y-%m-%d').strftime('%d-%m-%Y')
            for date in json.loads(job.discrete_dates)))]
    else:
        date_rows = [('Start Date', job.start_date.strftime('%d-%m-%Y')),
                     ('End Date', job.end_date.strftime('%d-%m-%Y'))]

    locum = job.locum
    locum_name = f'{locum.firstname} {locum.lastname}'
    booking_rows = [('Rate', f'£{job.locum_rate}/hr')] + date_rows + [
        ('Time Required per day', f'{job.times_required} hrs'),
        ('Address', job.county),
        ('Post Code', job.post_code),
        ('Additional Information', job.any_other_information),
    ]
    pharmacy_details = [('Locum Type', locum.user_type), ('Name', locum_name)]
    if locum.user_type.lower() == 'pharmacist':
        pharmacy_details.append(('GPhC', locum.gphc_number))
    pharmacy_details += booking_rows
    subject = f"LocumSmart Ltd: Booking Confirmation - {datetime.now().strftime('%B')} - {job.pharmacy_name}"

    # Employer (copied to admin): the booking and the employer's cancellation terms
    send_branded_email('booking_employer', subject, [job.employer.email, settings.EMAIL_HOST_USER],
                       {'job': job, 'details': pharmacy_details})

    # Locum: the booking and the locum's own terms, by type of work
    if locum.user_type.lower() in ['pharmacist', 'technician', 'dispenser']:
        send_branded_email('booking_locum_pharmacy', subject, [applied_job.locum.email],
                           {'job': job, 'details': pharmacy_details})
    else:
        send_branded_email('booking_locum_primary_care', 'Booking Confirmation', [applied_job.locum.email], {
            'job': job,
            'details': [
                ('Name', locum_name),
                ('Role', locum.user_type),
                ('NMC pin', locum.nmc_number),
                ('Date', job.start_date.strftime('%d-%m-%Y')),
                ('Rate', f'£{job.locum_rate}/hr'),
                ('Timings/Session', f'{job.times_required} hours per day'),
                ('Address', job.county),
                ('Post Code', job.post_code),
                ('Additional Information', job.any_other_information),
            ],
        })

    return redirect('job_applications')


def reject_job(request, applied_job_id):
    applied_job = get_object_or_404(AppliedJob, pk=applied_job_id)
    applied_job.rejected = True
    applied_job.save()

    # Send rejection email to the locum
    job = applied_job.job
    send_branded_email(
        'application_declined',
        f"LocumSmart Ltd: Job Application Declined – {job.pharmacy_name}",
        [applied_job.locum.email],
        {
            'job': job,
            'locum': applied_job.locum,
            'jobs_url': SITE_URL + reverse('locumjobs'),
            'details': [
                ('Role', applied_job.locum.user_type),
                ('Rate', f'£{job.locum_rate}/hr'),
                ('Location', f'{job.county}, {job.post_code}'),
            ],
        })

    # Redirect to job applications page
    return redirect('job_applications')


class JobListView(ListView):
    model = Job
    template_name = 'calander.html'
    context_object_name = 'jobs'

    def get_queryset(self):
        queryset = super().get_queryset().filter(locum__isnull=False)

        # Parse and apply filters from the search query
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(locum__user_type__icontains=search_query) |
                Q(locum__firstname__icontains=search_query) |
                Q(locum__lastname__icontains=search_query) |
                Q(pharmacy_name__icontains=search_query)
            )

        # Sorting by date if specified in query parameters
        sort_by = self.request.GET.get('sort_by')
        if sort_by == 'Latest' or sort_by == 'Earliest':
            # Check for sorting direction (default to ascending)
            queryset = queryset.order_by('-start_date' if sort_by == 'Latest' else 'start_date')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['locum_invoices'] = LocumInvoice.objects.select_related('job', 'locum')
        return context


    def post(self, request, *args, **kwargs):
        # raise Exception(request)
        action = request.POST.get('action')
        job_ids = request.POST.getlist('job_ids')  # Retrieve the list of job IDs

        # Handle the case where job_ids is a comma-separated string
        if len(job_ids) == 1 and ',' in job_ids[0]:
            job_ids = job_ids[0].split(',')

        # Convert the list of job_ids to integers
        try:
            job_ids = [int(job_id.strip()) for job_id in job_ids if job_id.strip()]
        except ValueError:
            messages.error(request, 'Invalid job ID(s) provided.')
            return redirect(reverse('calander'))

        # An invoice needs at least one job
        if not job_ids:
            messages.error(request, 'Select at least one job before generating or emailing an invoice.')
            return redirect(reverse('calander'))

        # Get the list of Job objects based on the job_ids
        jobs = Job.objects.filter(id__in=job_ids)

        pharmacy = request.POST.get('pharmacy')
        if pharmacy not in ('Gorgemead', 'Fairgreen', 'Tesco', 'Cohens'):
            messages.error(request, 'Choose a pharmacy invoice format first.')
            return redirect(reverse('calander'))

        # Hours/Day is free text on the job, but the invoice total needs a number
        for job in jobs:
            try:
                float(job.times_required)
            except (TypeError, ValueError):
                messages.error(
                    request,
                    f'Cannot invoice the {job.pharmacy_name} job: Hours/Day "{job.times_required}" is not a number.')
                return redirect(reverse('calander'))

        # Generate unique invoice number
        if request.POST.get('invoice_no'):
            invoice_no = request.POST.get('invoice_no')
        else:
            invoice_no = random.randint(10000000, 99999999)
        
        # Initialize total_amount to 0
        total_amount = 0.0

        # Process jobs to calculate the number of days and total prices
        for job in jobs:
            if job.discrete_dates:
                job.discrete_dates_list = job.discrete_dates.strip('[]').replace('"', '').split(', ')
                job.days = len(job.discrete_dates_list)
                job.working_dates = ', '.join(job.discrete_dates_list)
            else:
                # Generate all dates between start_date and end_date
                job.discrete_dates_list = []
                current_date = job.start_date
                while current_date <= job.end_date:
                    job.discrete_dates_list.append(current_date.strftime('%d/%m/%Y'))
                    current_date += timedelta(days=1)
                job.days = len(job.discrete_dates_list)
                job.working_dates = ', '.join(job.discrete_dates_list)

            # Calculate per_day_price
            job.per_day_price = float(job.locum_rate) * float(job.times_required)

            # Calculate total_price for all days combined
            job.total_price = job.per_day_price * job.days

            # Process jobs to create an array of days
            job.days_list = job.discrete_dates_list

            # Add job's total_price to total_amount
            total_amount += job.total_price
        
        # After processing all jobs, total_amount contains the sum of all total_prices
        total_amount = f"{total_amount:.2f}"


        if request.POST.get('date_time'):
            # Parsing the string into a datetime object
            stored_date_str = request.POST.get('date_time').replace("Sept.", "Sep").replace(".", "")  # Normalize the date
            try:
                stored_date = datetime.strptime(stored_date_str, "%b %d, %Y, %I:%M %p")
            except ValueError:
                # Unrecognised date format: fall back to today rather than failing
                stored_date = datetime.now()

            # Extracting the current month and year in 'Month-YY' format
            current_month = stored_date.strftime('%B-%y')
        
            # Extracting the current date in 'dd/mm/YYYY' format
            current_date = stored_date.strftime('%d/%m/%Y')
        else:
            # Get the current date
            current_date = datetime.now().strftime('%d/%m/%Y')
            
            # Get the current month in the format 'Month-Year' (e.g., 'July-24')
            current_month = datetime.now().strftime('%B-%y')

        if action == 'generate_invoice':
            self.track_invoice(job_ids, pharmacy, invoice_no, total_amount)
            context = {
                'jobs': jobs,
                'invoice_number': invoice_no,
                'created_date': current_date,
                'month': current_month,
                'total_amount': total_amount,
                'payment_terms': settings.INVOICE_PAYMENT_TERMS,
            }

            # Render the appropriate template
            template_name = self.get_template_for_pharmacy(pharmacy)
            return render(request, template_name, context)

        elif action == 'send_email':
            to_email = request.POST.get('to')
            cc_email = request.POST.get('cc')

            # Generate the PDF invoices for each pharmacy
            gorgemead_pdf = self.generate_invoice_pdf(jobs, current_date, invoice_no, current_month, total_amount, pharmacy)
            # fairgreen_pdf = self.generate_invoice_pdf(jobs, current_date, invoice_no, current_month, total_amount, 'Fairgreen')
            # tesco_pdf = self.generate_invoice_pdf(jobs, current_date, invoice_no, current_month, total_amount, 'Tesco')
            # cohens_pdf = self.generate_invoice_pdf(jobs, current_date, invoice_no, current_month, total_amount, 'Cohens')

            # Create the email with a more professional content
            email = EmailMessage(
                subject=f"LocumSmart Ltd: Invoice for Selected Jobs - Invoice #{invoice_no}",
                body=(
                    f"Dear Sir/Madam,\n\n"
                    f"Please find attached the invoice for the selected jobs. Below are the details:\n\n"
                    f"Invoice Number: {invoice_no}\n"
                    f"Total Amount: £{total_amount}\n"
                    f"Generated on: {current_date}\n\n"
                    f"If you have any questions, feel free to contact us.\n\n"
                    f"Best regards,\n"
                    f"LocumSmart Ltd"
                ),
                from_email=settings.EMAIL_HOST_USER,
                to=[to_email],
                cc=[cc_email] if cc_email else []
            )


            # Attach the PDFs to the email with the new file naming format
            file_name = f"Invoice #{invoice_no} - {jobs[0].company_name}.pdf"
            email.attach(file_name, gorgemead_pdf.read(), 'application/pdf')

            # email.attach('fairgreen_invoice.pdf', fairgreen_pdf.read(), 'application/pdf')
            # email.attach('tesco_invoice.pdf', tesco_pdf.read(), 'application/pdf')
            # email.attach('cohens_invoice.pdf', cohens_pdf.read(), 'application/pdf')

            # Send the email
            try:
                email.send()
            except Exception:
                logger.exception('Failed to email invoice %s', invoice_no)
                messages.error(request, f'Invoice #{invoice_no} could not be emailed. Please try again.')
                return redirect(reverse('calander'))

            # Record the email against the existing tracking record for this invoice
            invoice = self.track_invoice(job_ids, pharmacy, invoice_no, total_amount)
            invoice.to_email = to_email
            invoice.cc_email = cc_email
            invoice.from_email = settings.EMAIL_HOST_USER
            invoice.emailed_at = timezone.now()
            invoice.save()
            messages.success(request, f'Invoice #{invoice_no} emailed to {to_email}.')

        return redirect(reverse('calander'))

    def track_invoice(self, job_ids, pharmacy, invoice_no, total_amount):
        # One tracking record per invoice number: created as Pending the first
        # time the invoice is generated, then reused when it is shown or emailed
        invoice = EmailTrackingLog.objects.filter(invoice_no=invoice_no).order_by('-id').first()
        if invoice is None:
            invoice = EmailTrackingLog(invoice_no=invoice_no)
        elif invoice.status == EmailTrackingLog.STATUS_PAID:
            return invoice
        invoice.job_ids = job_ids
        invoice.invoice_type = pharmacy
        invoice.total_amount = total_amount
        invoice.save()
        return invoice

    def get_template_for_pharmacy(self, pharmacy):
        if pharmacy == 'Gorgemead':
            return 'invoices/Gorgemead.html'
        elif pharmacy == 'Fairgreen':
            return 'invoices/Fairgreen.html'
        elif pharmacy == 'Tesco':
            return 'invoices/Tesco.html'
        elif pharmacy == 'Cohens':
            return 'invoices/Cohens.html'

    def generate_invoice_pdf(self, jobs, created_date, invoice_number, month, total_amount, pharmacy):
        if pharmacy == 'Gorgemead':
            return generate_gorgemead_invoice_pdf(jobs, created_date, invoice_number, month, total_amount)
        elif pharmacy == 'Fairgreen':
            return generate_fairgreen_invoice_pdf(jobs, created_date, invoice_number, month, total_amount)
        elif pharmacy == 'Tesco':
            return generate_tesco_invoice_pdf(jobs, created_date, invoice_number, month, total_amount)
        elif pharmacy == 'Cohens':
            return generate_cohens_invoice_pdf(jobs, created_date, invoice_number, month, total_amount)


class UpdateJobView(View):
    def post(self, request, job_id):
        # Retrieve job object
        job = Job.objects.get(pk=job_id)
        # Update job object based on query parameters
        date_of_booking_email = request.POST.get('date_of_booking_email')
        company_name = request.POST.get('company_name')
        locum_payment_status = request.POST.get('locum_payment_status')
        status = request.POST.get('status')
        date_of_invoice_email = request.POST.get('date_of_invoice_email')
        source = request.POST.get('source')
        source_commission_date = request.POST.get('source_commission_date')
        booked_by = request.POST.get('booked_by')
        if date_of_booking_email:
            job.date_of_booking_email = date_of_booking_email
        if locum_payment_status:
            job.locum_payment_status = locum_payment_status
        if status:
            job.status = status
        if date_of_invoice_email:
            job.date_of_invoice_email = date_of_invoice_email
        if source:
            job.source = source
        if source_commission_date:
            job.source_commission_date = source_commission_date
        if booked_by:
            job.booked_by = booked_by
        if company_name:
            job.company_name = company_name

        # Save updated job object
        job.save()

        # Redirect back to calendar page with pre-filled fields
        return HttpResponseRedirect(reverse('calander'))


class LocumEditView(View):
    def get(self, request, locum_id):
        locum = Locum.objects.get(id=locum_id)
        context = {
            'locum': locum
        }
        if locum.user_type == 'Pharmacist':
            template_name = 'pharmacistRequest.html'
        elif locum.user_type == 'Nurse' or locum.user_type == 'ANPNurse':
            template_name = 'NursesRegistration.html'
        elif locum.user_type == 'GP':
            template_name = 'gpRegistration.html'
        elif locum.user_type == 'Technician' or locum.user_type == 'Dispenser':
            template_name = 'techDesRegistration.html'

        return render(request, template_name, context)

    def post(self, request, locum_id):
        locum = Locum.objects.get(id=locum_id)
        if locum.user_type == 'Pharmacist':
            # Extract form data from POST request
            title = request.POST.get('title')
            firstname = request.POST.get('firstname')
            lastname = request.POST.get('lastname')
            date_of_birth = request.POST.get('date_of_birth')
            email = request.POST.get('email')
            telephone = request.POST.get('telephone')
            county = request.POST.get('county')
            post_code = request.POST.get('post_code')
            nationality = request.POST.get('nationality')
            gphc_number = request.POST.get('gphc_number')
            qualified_date = request.POST.get('qualified_date')
            passport_expiry_date = request.POST.get('passport_expiry_date')
            dbs_service_number = request.POST.get('dbs_service_number', '')
            insurance_expiry_date = request.POST.get('insurance_expiry_date')

            visa_expiry = request.POST.get('visa_expiry')
            gphc_number_expiry = request.POST.get('gphc_number_expiry')

        # Update locum object with new data
            locum.title = title
            locum.firstname = firstname
            locum.lastname = lastname
            locum.date_of_birth = date_of_birth
            locum.email = email
            locum.telephone = telephone
            locum.county = county
            locum.post_code = post_code
            locum.nationality = nationality
            locum.gphc_number = gphc_number
            locum.qualified_date = qualified_date
            locum.passport_expiry_date = passport_expiry_date
            locum.dbs_service_number = dbs_service_number
            locum.insurance_expiry_date = insurance_expiry_date
            locum.gphc_number_expiry = gphc_number_expiry
            if visa_expiry:
                locum.visa_expiry = visa_expiry
        # Handle file uploads
            files_data = request.FILES
            if 'passport' in files_data:
                locum.passport_copy = files_data['passport']
            if 'dbs_enhanced_disclosure' in files_data:
                locum.dbs_enhanced_disclosure = files_data['dbs_enhanced_disclosure']
            if 'insurance' in files_data:
                locum.insurance = files_data['insurance']
            if 'visa_residence_permit' in files_data:
                locum.visa_residence_permit = files_data['visa_residence_permit']
            if 'safeguarding_level2' in files_data:
                locum.safeguarding_level2 = files_data['safeguarding_level2']
            for i in range(1, 16):  # Assuming up to 15 accreditations
                field_name = f'accreditations{i}'
                if field_name in files_data:
                    setattr(locum, field_name, files_data[field_name])

            locum.save()
            messages.success(request, 'Profile Updated')

            return redirect('edit_locum', locum.id)
        elif locum.user_type == 'Nurse' or locum.user_type == 'ANPNurse':
            # Extract form data from POST request
            title = request.POST.get('title')
            firstname = request.POST.get('firstname')
            lastname = request.POST.get('lastname')
            date_of_birth = request.POST.get('date_of_birth')
            email = request.POST.get('email')
            telephone = request.POST.get('telephone')
            county = request.POST.get('county')
            post_code = request.POST.get('post_code')
            nationality = request.POST.get('nationality')
            nmc_number = request.POST.get('nmc_number')
            dbs_service_number = request.POST.get('dbs_service_number', '')
            nmc_expiry = request.POST.get('nmc_expiry')

            visa_expiry = request.POST.get('visa_expiry')
            gphc_number_expiry = request.POST.get('gphc_number_expiry')

        # Update locum object with new data
            locum.title = title
            locum.firstname = firstname
            locum.lastname = lastname
            locum.date_of_birth = date_of_birth
            locum.email = email
            locum.telephone = telephone
            locum.county = county
            locum.post_code = post_code
            locum.nationality = nationality
            locum.nmc_number = nmc_number
            locum.nmc_expiry = nmc_expiry
            locum.dbs_service_number = dbs_service_number
            # handling files:
            files_data = request.FILES
            if 'nmc_certificate' in files_data:
                locum.nmc_certificate = files_data['nmc_certificate']
            if 'dbs_enhanced_disclosure' in files_data:
                locum.dbs_enhanced_disclosure = files_data['dbs_enhanced_disclosure']
            for i in range(1, 16):  # Assuming up to 15 accreditations
                field_name = f'accreditations{i}'
                if field_name in files_data:
                    setattr(locum, field_name, files_data[field_name])

            locum.save()
            messages.success(request, 'Profile Updated')

            return redirect('edit_locum', locum.id)

        elif locum.user_type == 'GP':
            # Extract form data from POST request
            title = request.POST.get('title')
            firstname = request.POST.get('firstname')
            lastname = request.POST.get('lastname')
            date_of_birth = request.POST.get('date_of_birth')
            email = request.POST.get('email')
            telephone = request.POST.get('telephone')
            county = request.POST.get('county')
            post_code = request.POST.get('post_code')
            nationality = request.POST.get('nationality')
            smartcard_number = request.POST.get('smartcard_number')
            gmc_number = request.POST.get('gmc_number', '')
            insurance_expiry_date = request.POST.get('insurance_expiry_date')
            gmc_expiry = request.POST.get('gmc_expiry')

        # Update locum object with new data
            locum.title = title
            locum.firstname = firstname
            locum.lastname = lastname
            locum.date_of_birth = date_of_birth
            locum.email = email
            locum.telephone = telephone
            locum.county = county
            locum.post_code = post_code
            locum.nationality = nationality
            locum.smartcard_number = smartcard_number
            locum.gmc_number = gmc_number
            locum.insurance_expiry_date = insurance_expiry_date
            if gmc_expiry:
                locum.gmc_expiry = gmc_expiry

            # handling files:
            files_data = request.FILES
            if 'insurance' in files_data:
                locum.insurance = files_data['insurance']
            if 'gmc_certificate' in files_data:
                locum.gmc_certificate = files_data['gmc_certificate']
            for i in range(1, 16):  # Assuming up to 15 accreditations
                field_name = f'accreditations{i}'
                if field_name in files_data:
                    setattr(locum, field_name, files_data[field_name])

            locum.save()
            messages.success(request, 'Profile Updated')

            return redirect('edit_locum', locum.id)

        elif locum.user_type == 'Technician' or locum.user_type == 'Dispenser':
            # Extract form data from POST request
            title = request.POST.get('title')
            firstname = request.POST.get('firstname')
            lastname = request.POST.get('lastname')
            date_of_birth = request.POST.get('date_of_birth')
            email = request.POST.get('email')
            telephone = request.POST.get('telephone')
            county = request.POST.get('county')
            post_code = request.POST.get('post_code')
            nationality = request.POST.get('nationality')
            qualified_date = request.POST.get('qualified_date')
            passport_expiry_date = request.POST.get('passport_expiry_date')
            visa_expiry = request.POST.get('visa_expiry')

        # Update locum object with new data
            locum.title = title
            locum.firstname = firstname
            locum.lastname = lastname
            locum.date_of_birth = date_of_birth
            locum.email = email
            locum.telephone = telephone
            locum.county = county
            locum.post_code = post_code
            locum.nationality = nationality
            # The technician/dispenser form has no GPhC field; leave any stored number untouched
            locum.qualified_date = qualified_date
            locum.passport_expiry_date = passport_expiry_date
            if visa_expiry:
                locum.visa_expiry = visa_expiry
        # Handle file uploads
            files_data = request.FILES
            if 'passport' in files_data:
                locum.passport_copy = files_data['passport']
            if 'qualification_certificate' in files_data:
                locum.qualification_certificate = files_data['qualification_certificate']
            if 'visa_residence_permit' in files_data:
                locum.visa_residence_permit = files_data['visa_residence_permit']

            for i in range(1, 16):  # Assuming up to 15 accreditations
                field_name = f'accreditations{i}'
                if field_name in files_data:
                    setattr(locum, field_name, files_data[field_name])

            locum.save()
            messages.success(request, 'Profile Updated')

            return redirect('edit_locum', locum.id)


class EditEmployer(View):
    template_name = 'registerEmployer.html'

    def get(self, request, employer_id):
        employer = get_object_or_404(Employer, pk=employer_id)
        context = {
            'employer': employer,
        }
        return render(request, self.template_name, context)

    def post(self, request, employer_id):
        employer = get_object_or_404(Employer, pk=employer_id)
        email = request.POST.get('email')
        post_code = request.POST.get('post_code')

        # Update the Employer object and save
        employer.first_name = request.POST.get('Firstname')
        employer.last_name = request.POST.get('Lastname')
        employer.email = email
        employer.pharmacy_name = request.POST.get('pharmacy_name')
        employer.manager_name = request.POST.get('manager_name')
        employer.street_address = request.POST.get('1')
        employer.phone_number = request.POST.get('telephone')
        employer.post_code = post_code
        employer.city = request.POST.get('city')
        employer.save()

        messages.success(request, 'Employer has been updated successfully.')
        return redirect('employersList')


class DeleteEmployer(View):
    def post(self, request, employer_id):
        employer = get_object_or_404(Employer, pk=employer_id)
        employer.delete()
        messages.success(request, 'Employer has been deleted successfully.')
        # Change 'locum_list' to your actual list view name if differen
        return redirect('employersList')

@method_decorator(login_required, name='dispatch')
class EmailTrackingLogView(View):
    template_name = 'emailTrackingLog.html'

    def get(self, request):
        email_logs = EmailTrackingLog.objects.order_by('-timestamp')
        return render(request, self.template_name, {'email_logs': email_logs})


@login_required
@require_POST
def mark_agency_invoice_paid(request, invoice_id):
    # Only admin/staff accounts can confirm payment of an agency invoice
    if not Admin.objects.filter(id=request.user.id).exists():
        raise PermissionDenied

    invoice = get_object_or_404(EmailTrackingLog, pk=invoice_id)
    if invoice.status != EmailTrackingLog.STATUS_PAID:
        invoice.status = EmailTrackingLog.STATUS_PAID
        invoice.paid_at = timezone.now()
        invoice.save()
        messages.success(request, f'Invoice #{invoice.invoice_no} marked as paid.')

    return redirect('email_tracking_log')
    

def send_email_to_locums(request, job_id):
    if request.method == "POST":
        selected_locums = request.POST.getlist('selected_locums')
        job = get_object_or_404(Job, id=job_id)
        job_url = f'https://locumsmart.co.uk/login/?next=/job/{job_id}/'

        sent_emails = set()  # To keep track of unique emails

        # Deserialize discrete_dates if necessary
        if isinstance(job.discrete_dates, str):
            discrete_dates = json.loads(job.discrete_dates)
        else:
            discrete_dates = job.discrete_dates

        # Determine the job date details
        if discrete_dates:
            job_dates = ', '.join(discrete_dates)
            job_dates_message = f'The job is scheduled on the following days: {job_dates}.'
        else:
            job_dates_message = f'The job starts on {job.start_date} and ends on {job.end_date}.'

        for locum_id in selected_locums:
            locum = Locum.objects.get(id=locum_id)
            if locum.Email not in sent_emails:
                send_branded_email('job_opportunity', 'LocumSmart Ltd: Job Opportunity', [locum.Email], {
                    'locum': locum,
                    'job_url': job_url,
                    'job_dates_message': job_dates_message,
                })
                sent_emails.add(locum.Email)  # Add the email to the set after sending

        # Redirect to the job details page after sending the emails
        return redirect('job_details', job_id=job_id)

    return redirect('seeLocums')  # Redirect back if not POST