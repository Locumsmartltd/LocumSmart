from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
import json
from datetime import datetime
from django.views.generic import DetailView
from django.contrib import messages
from locum.models import Locum, Job, AppliedJob, LocumAvailability
from appAdmin.models import Admin
from django.utils.text import capfirst
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from urllib.parse import urlparse, unquote
from django.core.mail import send_mail
from django.conf import settings
from structure.models import City
from structure.models import Testimonial
from appAdmin.models import *
from geopy.distance import geodesic
from django.utils.decorators import method_decorator
from datetime import date, timedelta
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from collections import defaultdict

# Create your views here.

def testimonials_view(request):
    if request.headers.get('Content-Type') == 'application/json' or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        # Redirect or display a more user-friendly page if accessed directly
        return render(request, 'error404.html', {})  # Show a placeholder template
    testimonials = Testimonial.objects.all().order_by('-created_at')  # Fetch all testimonials, newest first
    data = [
        {
            "name": testimonial.name,
            "source": testimonial.source,
            "rating": testimonial.rating,
            "comment": testimonial.comment,
        }
        for testimonial in testimonials
    ]
    return JsonResponse(data, safe=False)


class LandingPageView(View):
    template_name = 'landingpage.html'

    def get(self, request):
        cities = City.objects.all()
        cities = [capfirst(onecity.city) for onecity in cities]

        locum_count = Locum.objects.count()
        employer_count = Employer.objects.count()
        # Ensure the count is at least 20
        locum_count = max(locum_count, 10)
        employer_count = max(employer_count, 10)

        context = {
            'cities': cities,
            'locum_count': locum_count,
            'employer_count': employer_count,
        }
        context = {
            'cities': cities,
            'locum_count': locum_count,
            'employer_count': employer_count,
        }
        return render(request, self.template_name, context)


class ContactUsView(View):
    template_name = 'ContactUs.html'

    def get(self, request):
        return render(request, self.template_name)

    # def post(self, request):
    #     firstname = request.POST.get('firstname')
    #     surname = request.POST.get('surname')
    #     email = request.POST.get('email')
    #     phone = request.POST.get('phone')
    #     user_type = request.POST.get('user-type')
    #     message = request.POST.get('message')

    #     # Format email content
    #     subject = f"Contact Us Form Submission - {firstname} {surname}"
    #     from_email = settings.EMAIL_HOST_USER  # Use the user's email as the sender
    #     # Admin email to receive the contact form
    #     to_email = [settings.EMAIL_HOST_USER]
    #     contact_message = f"Name: {firstname} {surname}\nEmail: {email}\nPhone: {phone}\nUser Type: {user_type}\nMessage: {message}"

    #     # Send email
    #     send_mail(subject, contact_message, from_email,
    #               to_email, fail_silently=False)
    #     messages.success(request, 'An email has been sent to the Admin!')

    #     # Optionally, you can add a success message or redirect
    #     return render(request, self.template_name)


class aboutUsView(View):
    template_name = 'aboutUs.html'

    def get(self, request):
        return render(request, self.template_name)


class privacypolicyView(View):
    template_name = 'privacypolicy.html'

    def get(self, request):
        return render(request, self.template_name)


class CookiesView(View):
    template_name = 'cookies.html'

    def get(self, request):
        return render(request, self.template_name)


class LoginpageView(LoginView):
    template_name = 'login.html'

    def get(self, request):
        if request.GET.get('next'):
            next_url = request.GET.get('next')
            parsed_url = urlparse(next_url)
            path_parts = parsed_url.path.split('/')
            job_id = path_parts[-2] if len(path_parts) >= 3 else None
            request.session['job_id'] = job_id
        return render(request, self.template_name)

    def post(self, request):
        # Extract form data from POST request
        email = request.POST.get('email')
        password = request.POST.get('password')
        locum_role = request.POST.get('type')

        if locum_role in ['Pharmacist', 'Dispenser', 'Technician', 'Nurse', 'ANPNurse', 'GP']:
            # Check Locum table for the specified role
            user = Locum.objects.filter(
                email=email, user_type=locum_role).first()
        elif locum_role in ['Admin', 'Staff']:
            # Check AppAdmin table for Admin or Staff role
            user = Admin.objects.filter(email=email).first()

        else:
            # Invalid locum_role provided
            messages.error(request, 'Invalid user.')
            return redirect('login')

        if user is not None:
            # User authenticated successfully, log the user in
            if user.check_password(password):

                login(request, user)

                if self.request.session.get('job_id'):
                    job_id = self.request.session.get('job_id')
                    self.request.session.pop('job_id', None)
                    return redirect('job_details', job_id=job_id)

                if locum_role in ['Admin', 'Staff']:
                    return redirect('admin')
                # locum case is yet to be handled .Redirect to the home page or dashboard
                return redirect('locumProfile')
            else:
                messages.error(request, 'Wrong Password.')
                return redirect('login')
        else:
            # Authentication failed
            messages.error(request, 'Invalid email or type. Please try again.')
            return redirect('login')


class LogoutView(View):
    def get(self, request):
        logout(request)  # Logout the user
        return redirect('LandingPage')


class LocumJobs(View):
    template_name = 'locumJobs.html'

    def get(self, request):
        # Retrieve all jobs with applied_status=False (jobs not yet applied to)
        jobs = Job.objects.filter(applied_status=False)
        cities = City.objects.all()
        cities = [capfirst(onecity.city) for onecity in cities]
        # Filter jobs based on search criteria from request parameters
        locum_type = request.GET.get('locum')
        pharmacy_name = request.GET.get('pharmacy')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        min_rate = request.GET.get('min_rate')
        max_rate = request.GET.get('max_rate')
        selected_city = request.GET.get('location')
        distance = request.GET.get('distance', '0')

        # Apply filters if corresponding parameters are provided
        if locum_type:
            locum_type = locum_type.lower()

    # Map the locum_type to its corresponding boolean field in the Job model
            locum_field_map = {
                'pharmacist': 'pharmacist_required',
                'technician': 'technician_required',
                'dispenser': 'dispenser_required',
                'nurse': 'nurse_required',
                'anp_nurse': 'anp_nurse_required',
                'gp': 'gp_required'
            }
            field_name = locum_field_map.get(locum_type)
            if field_name:
                # Filter jobs where the specified field is True
                jobs = jobs.filter(**{field_name: True})

        if pharmacy_name:
            jobs = jobs.filter(pharmacy_name__icontains=pharmacy_name)

        if start_date:
            jobs = jobs.filter(start_date__gte=start_date)

        if end_date:
            jobs = jobs.filter(end_date__lte=end_date)

        if min_rate:
            jobs = jobs.filter(locum_rate__gte=float(min_rate))

        if max_rate:
            jobs = jobs.filter(locum_rate__lte=float(max_rate))

        if selected_city and distance:

            # Get the user's selected city
            user_city = selected_city.lower()

            # Find the latitude and longitude of the user's city
            user_location = City.objects.filter(city=user_city)
            user_location = user_location.first()
            if user_location:
                user_lat = user_location.lat
                user_lon = user_location.long

            # Find all cities within the specified distance from the user's city
            nearby_cities = []
            if user_location:
                for city in City.objects.all():
                    city_location = (city.lat, city.long)
                    if geodesic((user_lat, user_lon), city_location).miles <= float(distance):
                        nearby_cities.append(city.city.lower())
                print(nearby_cities)
                # Filter jobs based on nearby cities
            jobs = [job for job in jobs if job.county.lower() in nearby_cities]

        context = {'jobs': jobs, 'cities': cities}
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class JobDetailsView(View):
    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)

        # Parse discrete_dates if it exists
        discrete_dates = None
        if job.discrete_dates:
            discrete_dates = [datetime.strptime(
                date_str, '%Y-%m-%d').date() for date_str in json.loads(job.discrete_dates)]

        return render(request, 'jobDetails.html', {'job': job, 'discrete_dates': discrete_dates})

    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)

        if request.POST.get('edit') and request.user.admin:
            # Update job details if admin user submits the form
            job.pharmacy_name = request.POST.get('pharmacy_name')
            job.company_name = request.POST.get('company_name')
            job.county = request.POST.get('county')
            job.post_code = request.POST.get('post_code')
            job.locum_rate = float(request.POST.get('locum_rate'))
            job.expenses_offered = float(request.POST.get('expenses_offered'))
            job.times_required = request.POST.get('times_required')
            job.any_other_information = request.POST.get('any_other_information')

            # Update role requirements
            job.pharmacist_required = 'pharmacist' in request.POST.getlist('locum_role')
            job.technician_required = 'technician' in request.POST.getlist('locum_role')
            job.dispenser_required = 'dispenser' in request.POST.getlist('locum_role')
            job.nurse_required = 'nurse' in request.POST.getlist('locum_role')
            job.anp_nurse_required = 'anp_nurse' in request.POST.getlist('locum_role')
            job.gp_required = 'gp' in request.POST.getlist('locum_role')

            # Process dates
            date_type = request.POST.get('date_type')
            start_date = None
            end_date = None
            discrete_dates_json = None
            if date_type == 'continuous':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                job.discrete_dates = None  # Set discrete_dates to None for continuous dates
            elif date_type == 'discrete':
                discrete_dates = request.POST.getlist('discrete_dates[]')
                discrete_dates = [date for date in discrete_dates if date]
                discrete_dates = sorted(discrete_dates)
                start_date = discrete_dates[0]
                end_date = discrete_dates[-1]
                discrete_dates_json = json.dumps(discrete_dates)
                job.discrete_dates = discrete_dates_json  # Save discrete dates as JSON

            job.start_date = start_date
            job.end_date = end_date

            job.save()
            messages.success(request, "Job details updated successfully.")
            return redirect('job_details', job_id=job_id)

        # Assuming user is logged in as Locum
        locum = Locum.objects.filter(customuser_ptr_id=request.user.id).first()
        if locum:
            additional_info = request.POST.get('additional_info', '').strip()

            # Create an instance of AppliedJob
            applied_job = AppliedJob.objects.create(
                locum=locum,
                job=job,
                # Keep negotiation false by default; additional info is handled via email for now
                negotiation=False
            )

            # Send email notification to employer
            employer_email = job.employer.email
            
            subject = 'LocumSmart Ltd: Locum Job Application Notification'

            # Handle masking of post code (only first 3 digits visible)
            def mask_post_code(post_code):
                return post_code[:3] + '****' if len(post_code) > 3 else post_code
            
            # Check if discrete dates exist and prepare the dates display
            if job.discrete_dates:
                discrete_dates = json.loads(job.discrete_dates)
                date_info = f"<strong>Selected Dates:</strong> " + ', '.join(
                    [datetime.strptime(date, '%Y-%m-%d').strftime('%d %B %Y') for date in discrete_dates])
            else:
                date_info = f"<strong>Start Date:</strong> {job.start_date.strftime('%d %B %Y')}<br>" \
                            f"<strong>End Date:</strong> {job.end_date.strftime('%d %B %Y')}"
            
            # Prepare the message with masked post code for non-admins
            message = f"""
            Dear {locum.first_name} {locum.last_name},<br/>
            
            Thank You for your interest in the following Position. We have received your request and someone from our team will be in touch with you.<br><br>
            {f'<strong>Additional Information:</strong> {additional_info}<br><br>' if additional_info else ''}
            
            <strong>Locum Details:</strong><br>
            - Name: {locum.first_name} {locum.last_name}<br>
            - Email: {locum.email}<br>
            - Locum Type: {locum.user_type}<br><br>
            
            <strong>Job Details:</strong><br>
            - City/County: {job.county}<br>
            - Post Code: {mask_post_code(job.post_code)}<br>
            - Locum Rate: £{job.locum_rate}/hr<br>
            - Expenses Offered: £{job.expenses_offered}<br>
            {date_info}<br><br>
            
            Please review the application at your earliest convenience. 
            <p>Best regards,<br>
            Mustafa Amin<br>
            LocumSmart Ltd<br>
            Providing 8000+ Locums & Permanent Staff across the UK<br> 
            General Practitioners | Doctors | Physician Associates | Pharmacists | Technicians and Dispensers | Hospitals, and Pharma | Staffing & Recruiting<br>
            Email: info@locum-smart.co.uk<br>
            Phone: +44 7534749465</p>
            """
            
            # Prepare the message with post code for employer
            message2 = f"""
            Dear { job.employer.first_name} {job.employer.last_name},<br/>

            We have received the following request from locum.<br><br>
            {f'<strong>Additional Information from Locum:</strong> {additional_info}<br><br>' if additional_info else ''}
            
            <strong>Locum Details:</strong><br>
            - Name: {locum.first_name} {locum.last_name}<br>
            - Email: {locum.email}<br>
            - Locum Type: {locum.user_type}<br><br>
            
            <strong>Job Details:</strong><br>
            - City/County: {job.county}<br>
            - Post Code: {mask_post_code(job.post_code)}<br>
            - Locum Rate: £{job.locum_rate}/hr<br>
            - Expenses Offered: £{job.expenses_offered}<br>
            {date_info}<br><br>
            
            
            <p>Best regards,<br>
            Mustafa Amin<br>
            LocumSmart Ltd<br>
            Providing 8000+ Locums & Permanent Staff across the UK<br> 
            General Practitioners | Doctors | Physician Associates | Pharmacists | Technicians and Dispensers | Hospitals, and Pharma | Staffing & Recruiting<br>
            Email: info@locum-smart.co.uk<br>
            Phone: +44 7534749465</p>
            """
            
            # Convert message to plain text
            # plain_message = strip_tags(message)
            
            # Send email to employer and locum
            sender_email = settings.EMAIL_HOST_USER
            recipient_list1 = [locum.email]
            recipient_list2 = [employer_email]
            
            send_mail(subject, strip_tags(message), sender_email, recipient_list1, html_message=message)
            # send_mail(subject, strip_tags(message2), sender_email, recipient_list2, html_message=message2)

            # Send the same message to admin with full unmasked post code
            admin_message = f"""
            Dear Mustafa Amin,<br><br>
            {f'<strong>Additional Information from Locum:</strong> {additional_info}<br><br>' if additional_info else ''}

            <strong>Locum Details:</strong><br>
            - Name: {locum.first_name} {locum.last_name}<br>
            - Email: {locum.email}<br>
            - Locum Type: {locum.user_type}<br><br>
            
            <strong>Job Details:</strong><br>
            - Pharmacy Name: {job.pharmacy_name}<br>
            - Company Name: {job.company_name}<br>
            - City/County: {job.county}<br>
            - Post Code: {job.post_code}<br>
            - Locum Rate: £{job.locum_rate}/hr<br>
            - Expenses Offered: £{job.expenses_offered}<br>
            {date_info}<br><br>
            
            Best regards,
            """
            
            # Convert admin message to plain text
            # admin_plain_message = strip_tags(admin_message)
            
            # Send email to admin
            send_mail(subject, strip_tags(admin_message), sender_email, [sender_email], html_message=admin_message)

            # Optionally, you can add further logic based on the application

            return redirect('locumjobs')
        else:
            start_date = job.start_date
            end_date = job.end_date
            end_date_inclusive = end_date + timedelta(days=1)

            # Query for locum availabilities within the date range
            availability_within_range = LocumAvailability.objects.filter(
                date__range=[start_date, end_date_inclusive]
            ).select_related('locum')

            # Create a dictionary to store unique locums with concatenated dates
            locums_with_dates = defaultdict(list)

            # Populate the dictionary
            for availability in availability_within_range:
                locum = availability.locum
                locums_with_dates[locum].append(availability.date)

            # Prepare the context
            context = {
                'unique_locums': [{
                    'locum': locum,
                    'dates': sorted(dates)
                } for locum, dates in locums_with_dates.items()],
                'job_id': job.id,
            }

            # Render the template with the context
            return render(request, 'seeLocums.html', context)



def check_login(request, job_id):
    if request.user.is_authenticated:
        action = request.GET.get('action', 'view')  # Default to 'view' if no action is provided
        if action == 'delete':
            job = get_object_or_404(Job, id=job_id)
            job.delete()
            messages.success(request, 'Job has been deleted successfully.')
            return redirect('locumjobs')  # Redirect to the 'locumjobs' page after deletion
        # User is authenticated, redirect to job details page
        return redirect('job_details', job_id=job_id)
    else:
        messages.error(
            request, 'Please Login First to see the job details or sign up.')
        login_url = reverse('login')  # Get the URL of the login page
        # Append job ID to the login URL
        redirect_url = f'{login_url}?next=/job/{job_id}/'
        return redirect(redirect_url)


class SendAlertsView(View):

    def get(self, request):
        current_date = date.today()
        locums = Locum.objects.all()

        for locum in locums:
            expiry_fields = []

            if locum.user_type == 'Pharmacist':
                expiry_fields = [
                    ('Passport', locum.passport_expiry_date),
                    ('Insurance', locum.insurance_expiry_date),
                    ('GPHC Number', locum.gphc_number_expiry),
                    ('Visa', locum.visa_expiry)
                ]
            elif locum.user_type == 'GP':
                expiry_fields = [
                    ('Insurance', locum.insurance_expiry_date),
                    ('GMC Expiry', locum.gmc_expiry)
                ]
            elif locum.user_type in ['Nurse', 'ANPNurse']:
                expiry_fields = [
                    ('NMC Expiry', locum.nmc_expiry)
                ]
            elif locum.user_type in ['Technician', 'Dispenser']:
                expiry_fields = [
                    ('Passport', locum.passport_expiry_date)
                ]

            for field_name, expiry_date in expiry_fields:
                if expiry_date and expiry_date < current_date + timedelta(days=30):
                    # Expiry date is within 30 days, send alert email
                    sender_email = settings.EMAIL_HOST_USER

                    recipient_list = [locum.email]
                    subject = f'Doc Expiry Alert: {field_name} for {locum.firstname} {locum.lastname}'
                    message = f"Hello {locum.firstname},\n\nYour {field_name} is expiring on {expiry_date}. Please upload the latest documents.\n\nBest regards,\nLocum Smart."

                    # Send email to locum and admin
                    send_mail(subject, message, sender_email, recipient_list)

        # Redirect to profile page of the admin after sending alerts
        return redirect('admin')


def handler404(request, exception):
    return render(request, 'error404.html', status=404)

def handler403(request, exception=None):
    return render(request, 'error403.html', status=403)


class ForgotPasswordView(View):
    template_name = 'forgot_password.html'

    def get(self, request, uidb64, token):
        return render(request, self.template_name)

    def post(self, request, uidb64, token):
        # Extract form data from POST request
        email = request.POST.get('email')
        password = request.POST.get('password')
        locum_role = request.POST.get('type')

        if locum_role in ['Pharmacist', 'Dispenser', 'Technician', 'Nurse', 'ANPNurse', 'GP']:
            # Check Locum table for the specified role
            user = Locum.objects.filter(
                email=email, user_type=locum_role).first()
            if user:
                user.password = make_password(password)
                user.save()
                messages.success(request, 'Password Updated.')
                return redirect('login')
            else:
                messages.error(request, 'Invalid user.')
                return redirect('forgot_password')

        elif locum_role in ['Admin', 'Staff']:
            # Check AppAdmin table for Admin or Staff role
            user = Admin.objects.filter(email=email).first()
            if user:
                user.password = make_password(password)
                user.save()
                messages.success(request, 'Password Updated.')
                return redirect('login')
            else:
                messages.error(request, 'Invalid user.')
                return redirect('forgot_password')
        else:
            # Invalid locum_role provided
            messages.error(request, 'Invalid user.')
            return redirect('forgot_password')
        
        
class SetPasswordView(View):
    template_name = 'set_password.html'

    def get(self, request, token):
        return render(request, self.template_name)

    def post(self, request, token):
        # Extract form data from POST request
        password = request.POST.get('password')

        user = Locum.objects.filter(id=token).first()
        if user:
            user.password = make_password(password)
            user.save()
            return redirect('login')
        else:
            messages.error(request, 'Invalid user.')
            return redirect('forgot_password')


class FPEmailView(View):
    template_name = 'forgot_password_initial.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        locum_role = request.POST.get('type')

        if locum_role in ['Pharmacist', 'Dispenser', 'Technician', 'Nurse', 'ANPNurse', 'GP']:
            # Check Locum table for the specified role
            user = Locum.objects.filter(
                email=email, user_type=locum_role).first()

        elif locum_role in ['Admin', 'Staff']:
            # Check AppAdmin table for Admin or Staff role
            user = Admin.objects.filter(email=email).first()

        else:
            # Invalid locum_role provided
            messages.error(request, 'Invalid user.')
            return redirect('fpEmail')
        if user:
            # Generate a token for password reset
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_password_url = reverse('forgot_password', kwargs={
                                         'uidb64': uid, 'token': token})

            # Get the current domain
            current_site = get_current_site(request)
            domain = current_site.domain

            # Construct the complete reset password URL
            full_reset_password_url = request.build_absolute_uri(
                reset_password_url)

            # Render email template
            email_subject = 'Password Reset'
            email_template = 'password_reset_email.html'
            context = {'reset_password_url': full_reset_password_url}
            email_html_message = render_to_string(email_template, context)
            email_plaintext_message = strip_tags(email_html_message)

            # Send email with the reset password link
            sender_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]
            email = EmailMultiAlternatives(
                email_subject, email_plaintext_message, sender_email, recipient_list)
            email.attach_alternative(email_html_message, "text/html")
            email.send()

            # Redirect to a page confirming that the reset link has been sent
            messages.success(request, 'Check your Email to reset.')
            return redirect('fpEmail')
        else:
            # User not found
            messages.error(request, 'User not found.')
            return redirect('fpEmail')
