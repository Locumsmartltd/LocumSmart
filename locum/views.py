from django.shortcuts import render, redirect
from .models import Job, Employer
from django.views import View
from django.contrib import messages
from locum.models import *
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.loader import get_template
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
from django.http import JsonResponse
import json
from django.db.models import Q
from django.conf import settings
from structure.invoicing import INVOICE_PAYMENT_TERMS
from django.core.mail import send_mail
from django.utils.html import strip_tags
import pandas as pd
from django.core.mail import EmailMultiAlternatives
from appAdmin.models import Admin
from structure.passwords import SITE_URL
from structure.emails import send_branded_email, send_approval_email
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from functools import wraps
from urllib.parse import urlencode
from . import ledger, reports
import logging

# 'django.*' loggers are written to the error log file configured in settings.LOGGING
logger = logging.getLogger('django.registration')

# Fields every registration form requires: (POST name, label shown to the user)
COMMON_REGISTRATION_FIELDS = [
    ('title', 'Title'),
    ('firstname', 'Forename'),
    ('lastname', 'Surname'),
    ('date_of_birth', 'Date of Birth'),
    ('email', 'Email Address'),
    ('telephone', 'Telephone'),
    ('county', 'City'),
    ('nationality', 'Nationality'),
    ('post_code', 'Post Code'),
]


def missing_registration_fields(request, required_fields, required_files):
    # Labels of the required fields/uploads that were not submitted
    missing = [label for name, label in required_fields
               if not (request.POST.get(name) or '').strip()]
    missing += [label for name, label in required_files
                if name not in request.FILES]
    return missing


def send_registration_emails(firstname, lastname, email, telephone, user_type):
    # Tell the admin about the new request and confirm receipt to the applicant.
    # The registration is already saved at this point, so a mail server problem
    # must not turn it into a server error for the applicant.
    context = {
        'firstname': firstname,
        'lastname': lastname,
        'user_type': user_type,
        'requests_url': SITE_URL + reverse('locumRequests'),
        'details': [('Name', f'{firstname} {lastname}'), ('Email', email),
                    ('Phone', telephone), ('User Type', user_type)],
    }
    for template, subject, to_email in [
        ('registration_admin', f'LocumSmart Ltd: New {user_type} Registration Request', settings.EMAIL_HOST_USER),
        ('registration_received', f'LocumSmart Ltd: {user_type} Registration Request Submitted', email),
    ]:
        try:
            send_branded_email(template, subject, [to_email], context)
        except Exception:
            logger.exception("Registration email '%s' to %s could not be sent", subject, to_email)


def registration_submitted(request):
    # Back to the (now empty) form, where base.html shows the 'Registered Successfully'
    # dialog; closing it leads to the jobs page, which shows the awaiting-approval notice.
    messages.success(request, 'Your registration request has been submitted.', extra_tags='registered')
    request.session['awaiting_approval'] = True
    return redirect(request.path)

# Create your views here.

def sendEmailsToPharmacist(request):
    # Load the corrected Excel file
    file_path = 'locum/Pharmacist_Locum_Registration.xlsx'
    data = pd.read_excel(file_path)

    # Iterate through the rows and save to database
    for index, row in data.iterrows():
        
        locum = Locum.objects.get(
            email=row['email'], user_type='Pharmacist')
        
        # Send the approval / welcome email
        try:
            send_approval_email(locum)
            print(f"Successfully approved locums: {locum.Email} - {locum.id}")
        except Exception as e:
            print(f"Failed approval: {locum.Email} - {locum.id}")
            
def sendEmailsToTech(request):
    # Load the corrected Excel file
    file_path = 'locum/Technician_or_Dispenser_Records.xlsx'
    data = pd.read_excel(file_path)

    # Iterate through the rows and save to database
    for index, row in data.iterrows():
        
        locum = Locum.objects.get(
            email=row['email'], user_type='Technician')
        
        # Send the approval / welcome email
        try:
            send_approval_email(locum)
            print(f"Successfully approved locums: {locum.Email} - {locum.id}")
        except Exception as e:
            print(f"Failed approval: {locum.Email} - {locum.id}")

def addPharmacistManual(request):
    # Load the corrected Excel file
    file_path = 'locum/Pharmacist_Locum_Registration.xlsx'
    data = pd.read_excel(file_path)

    # Iterate through the rows and save to database
    for index, row in data.iterrows():
        # Skip if the email already exists for a 'Pharmacist' role
        if Locum.objects.filter(email=row['email'], user_type='Pharmacist').exists():
            print(f"Skipped: A user with email {row['email']} already exists.")
            continue

        date_of_birth = row['date_of_birth (YYYY-MM-DD)'] if pd.notna(row['date_of_birth (YYYY-MM-DD)']) else None
        qualified_date = row['qualified_date (YYYY-MM-DD)'] if pd.notna(row['qualified_date (YYYY-MM-DD)']) else None
        passport_expiry_date = row['passport_expiry_date (YYYY-MM-DD)'] if pd.notna(row['passport_expiry_date (YYYY-MM-DD)']) else None
        gphc_number_expiry = row['gphc_number_expiry (YYYY-MM-DD)'] if pd.notna(row['gphc_number_expiry (YYYY-MM-DD)']) else None


        # Create a new Locum instance
        locum = Locum(
            title=row['title'],
            password='password',
            first_name=row['firstname'],
            last_name=row['lastname'],
            gender=row['gender (Male, Female, Other)'],
            date_of_birth=date_of_birth,
            email=row['email'],
            telephone=row['telephone'],
            county=row['county'],
            post_code=row['post_code'],
            nationality=row['nationality'],
            gphc_number=row['gphc_number'],
            qualified_date=qualified_date,
            passport_expiry_date=passport_expiry_date,
            gphc_number_expiry=gphc_number_expiry,
            user_type='Pharmacist',
            can_provide_references=row['can_provide_references (yes, no)'].lower() == 'yes'
        )


        # Save the instance
        try:
            locum.save()
            print(f"Saved: {row['email']}")
        except Exception as e:
            print(f"Error saving record for {row['email']}: {e}")


def addtechManual(request):
    file_path = 'locum/Technician_or_Dispenser_Records.xlsx'
    technician_df = pd.read_excel(file_path)

    # Columns with dates to validate and correct
    date_columns = [
        'date_of_birth (YYYY-MM-DD)',
        'qualified_date (YYYY-MM-DD)',
        'passport_expiry_date (YYYY-MM-DD)'
    ]

    # Correct date formats
    for column in date_columns:
        technician_df[column] = pd.to_datetime(technician_df[column], errors='coerce').dt.strftime('%Y-%m-%d')
        technician_df[column] = technician_df[column].replace({pd.NaT: None})  # Replace NaT with None

    # Iterate through the rows and save to database
    for index, row in technician_df.iterrows():
        # Skip if the email already exists for the same user type
        if Locum.objects.filter(email=row['email']).exists():
            print(f"Skipped: User with email {row['email']} and type {row['user_type (Technician, Dispenser)']} already exists.")
            continue

        # Handle missing or default user_type
        user_type = row['user_type (Technician, Dispenser)']
        if pd.isna(user_type):
            user_type = 'Technician'  # Default user_type if missing

        # Create a new Locum instance
        locum = Locum(
            title=row['title'],
            password='password',
            first_name=row['firstname'],
            last_name=row['lastname'],
            gender=row['gender(Male,Female,Other)'],
            date_of_birth=row['date_of_birth (YYYY-MM-DD)'],
            email=row['email'],
            telephone=row['telephone'],
            county=row['county'],
            post_code=row['post_code'],
            nationality=row['nationality'],
            gphc_number=row.get('gphc_number', None),
            qualified_date=row['qualified_date (YYYY-MM-DD)'],
            passport_expiry_date=row['passport_expiry_date (YYYY-MM-DD)'],
            can_provide_references=row['can_provide_references (yes, no)'].lower() == 'yes',
            user_type=user_type  # Technician or Dispenser
        )

        # Save the instance
        try:
            locum.save()
            print(f"Saved: {row['email']} as {user_type}")
        except Exception as e:
            print(f"Error saving record for {row['email']}: {e}")

class EmployerRequestView(View):
    template_name = 'EmployerRequest.html'

    def get(self, request, employer_id=None):
        if employer_id:
            employer = get_object_or_404(Employer, id=employer_id)
            initial_data = {
                'employer_name': employer.pharmacy_name,
                'company_name': '',  # Assuming you don't have this in Employer model
                'name': f'{employer.first_name} {employer.last_name}',
                'email': employer.email,
                'telephone': employer.phone_number,
                'county': employer.city,  # Assuming city is stored as county
                'post_code': employer.post_code,
            }
        else:
            initial_data = {}
        return render(request, self.template_name, {'initial_data': initial_data})

    def post(self, request, employer_id=None):
        company_name = request.POST.get('company_name', '')
        email = request.POST.get('email')
        post_code = request.POST.get('post_code')
        locum_rate = float(request.POST.get('locum_rate'))
        expenses_offered = request.POST.get('expenses_offered')
        times_required = request.POST.get('times_required')
        any_other_information = request.POST.get('any_other_information')
        date_type = request.POST.get('date_type')

        # New employer registration fields
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        street_address = request.POST.get('street_address')
        city = request.POST.get('city')
        manager_name = request.POST.get('manager_name')
        telephone = request.POST.get('telephone')
    

        if expenses_offered and expenses_offered.strip():
            expenses_offered = float(expenses_offered)
        else:
            expenses_offered = 0

        # Handle boolean fields
        pharmacist_required = 'pharmacist_required' in request.POST
        Technician_required = 'Technician_required' in request.POST
        Nurse_required = 'Nurse_required' in request.POST
        ANP_required = 'ANP_required' in request.POST
        GP_required = 'GP_required' in request.POST
        Dispenser_required = 'Dispenser_required' in request.POST
        Optometrist_required = 'Optometrist_required' in request.POST
        DO_required = 'DO_required' in request.POST

        # Process dates
        start_date = None
        end_date = None
        discrete_dates_json = None
        if date_type == 'continuous':
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
        elif date_type == 'discrete':
            discrete_dates = request.POST.getlist('discrete_dates[]')
            discrete_dates = [date for date in discrete_dates if date]
            discrete_dates = sorted(discrete_dates)
            start_date = discrete_dates[0]
            end_date = discrete_dates[-1]
            discrete_dates_json = json.dumps(discrete_dates)

        # Check if the employer exists
        employer = Employer.objects.filter(email=email, post_code=post_code).first()

        if not employer:
            # If employer is new, validate required fields
            missing_fields = []
            if not first_name:
                missing_fields.append("First Name")
            if not last_name:
                missing_fields.append("Last Name")
            if not street_address:
                missing_fields.append("Street Address")
            if not city:
                missing_fields.append("City")
            if not manager_name:
                missing_fields.append("Manager Name")
            if not telephone:
                missing_fields.append("Telephone")

            if missing_fields:
                messages.error(
                    request,
                    f"Missing required fields for new employer: {', '.join(missing_fields)}."
                )
                return redirect('employerrequest')

            # Create a new employer
            employer = Employer.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                pharmacy_name=company_name,
                street_address=street_address,
                city=city,
                manager_name=manager_name,
                phone_number=telephone,
                post_code=post_code,
            )
            messages.success(request, "Thank you for registering at LocumSmart.")

        # Create a new Job instance
        job = Job(
            pharmacy_name=employer.pharmacy_name,
            company_name=company_name,
            name=employer.base_username(),
            email=email,
            telephone=employer.phone_number,
            county=employer.city,
            post_code=post_code,
            locum_rate=locum_rate,
            expenses_offered=expenses_offered,
            start_date=start_date,
            end_date=end_date,
            times_required=times_required,
            any_other_information=any_other_information,
            pharmacist_required=pharmacist_required,
            technician_required=Technician_required,
            dispenser_required=Dispenser_required,
            nurse_required=Nurse_required,
            anp_nurse_required=ANP_required,
            gp_required=GP_required,
            optometrist_required=Optometrist_required,
            do_required=DO_required,
            employer=employer
        )

        if date_type == 'discrete':
            job.discrete_dates = discrete_dates_json

        # Email notification to the employer and admin
        if job.discrete_dates:
            date_rows = [('Selected Dates', ', '.join(
                datetime.strptime(date, '%Y-%m-%d').strftime('%d-%m-%Y')
                for date in json.loads(job.discrete_dates)))]
        else:
            date_rows = [('Start Date', datetime.strptime(job.start_date, '%Y-%m-%d').strftime('%d-%m-%Y')),
                         ('End Date', datetime.strptime(job.end_date, '%Y-%m-%d').strftime('%d-%m-%Y'))]
        request_rows = [
            ('Pharmacy Name', job.pharmacy_name),
            ('Location', job.county),
            ('Post Code', job.post_code),
            ('Locum Role Required', self.get_locum_roles(job)),
        ]
        subject = 'LocumSmart Ltd: Employer Request Submitted'

        # A request entered by an admin on the employer's behalf is not confirmed to the employer
        admin = Admin.objects.filter(customuser_ptr_id=request.user.id).first()
        if not admin:
            send_branded_email('employer_request_received', subject, [job.employer.email], {
                'job': job,
                'details': request_rows + [('Rate', f'£{job.locum_rate}/hr')] + date_rows,
            })

        send_branded_email('employer_request_admin', subject, [settings.EMAIL_HOST_USER], {
            'job': job,
            'requests_url': SITE_URL + reverse('employerRequests'),
            'details': request_rows + [('Rate', f'£{job.locum_rate:.0f}/hr')] + date_rows + [
                ('Expenses Offered', f'£{job.expenses_offered:.0f}'),
                ('Time Required Per Day', f'{job.times_required} hrs'),
                ('Additional Information', job.any_other_information.strip() or 'None'),
            ],
        })

        # Save the Job object
        job.save()

        if employer_id:
            return redirect('employerRequests')
        else:
            messages.success(request, "Your request has been submitted successfully. You will be notified via email, if your request is approved by LocumSmart!")
            return redirect('employerrequest')

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
        if job.optometrist_required:
            roles.append("Optometrist")
        if job.do_required:
            roles.append("Dispensing Optician")
        return ', '.join(roles)



class locumTypesView(View):
    template_name = 'locumTypes.html'

    def get(self, request):
        locum_count_pharmacist = Locum.objects.filter(
            user_type='Pharmacist').count()
        locum_count_gp = Locum.objects.filter(user_type='GP').count()
        locum_count_nurses = Locum.objects.filter(
            Q(user_type='Nurse') | Q(user_type='ANPNurse')).count()
        locum_count_technician = Locum.objects.filter(
            Q(user_type='Technician') | Q(user_type='Dispenser')).count()

        # Ensure the count is at least 20
        locum_count_pharmacist = max(locum_count_pharmacist, 5)
        locum_count_gp = max(locum_count_gp, 5)
        locum_count_nurses = max(locum_count_nurses, 5)
        locum_count_technician = max(locum_count_technician, 5)

        context = {
            'locum_count_pharmacist': locum_count_pharmacist,
            'locum_count_gp': locum_count_gp,
            'locum_count_nurses': locum_count_nurses,
            'locum_count_technician': locum_count_technician,
        }
        return render(request, self.template_name, context)


class PharmacistRegisterView(View):
    template_name = 'pharmacistRequest.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        # Extract form data from POST request
        title = request.POST.get('title')
        password = None  # no usable password until the locum sets one from the approval email
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        county = request.POST.get('county')
        post_code = request.POST.get('post_code')
        nationality = request.POST.get('nationality')
        gphc_number = request.POST.get('gphc_number')
        qualified_date = request.POST.get('qualified_date')
        passport_expiry_date = request.POST.get('passport_expiry_date')
        can_provide_references = request.POST.get('can_provide_references')
        dbs_service_number = request.POST.get('dbs_service_number', '')
        insurance_expiry_date = request.POST.get('insurance_expiry_date')

        visa_expiry = request.POST.get('visa_expiry')
        gphc_number_expiry = request.POST.get('gphc_number_expiry')

        missing = missing_registration_fields(request, COMMON_REGISTRATION_FIELDS + [
            ('gender', 'Gender'),
            ('gphc_number', 'GPHC Number'),
            ('gphc_number_expiry', 'GPHC Number Expiry Date'),
            ('qualified_date', 'Qualified Date'),
            ('passport_expiry_date', 'Passport Expiry Date'),
            ('insurance_expiry_date', 'Insurance Expiry Date'),
        ], [
            ('passport', 'Passport'),
            ('insurance', 'Insurance'),
            ('dbs_enhanced_disclosure', 'DBS Enhanced Disclosure'),
        ])
        if missing:
            messages.error(request, f"Please complete the required fields: {', '.join(missing)}")
            return render(request, self.template_name)
        # Check if a user with the same email and user_type 'Pharmacist' already exists
        if Locum.objects.filter(email=email, user_type='Pharmacist').exists():
            messages.error(
                request, "A user with this email and role already exists.")
            return render(request, self.template_name)
        locum = Locum(
            title=title,
            password=password,
            first_name=firstname,
            last_name=lastname,
            gender=gender,
            date_of_birth=date_of_birth,
            email=email,
            telephone=telephone,
            county=county,
            post_code=post_code,
            nationality=nationality,
            gphc_number=gphc_number,
            qualified_date=qualified_date,
            passport_expiry_date=passport_expiry_date,
            can_provide_references=can_provide_references,
            dbs_service_number=dbs_service_number,
            insurance_expiry_date=insurance_expiry_date,
            gphc_number_expiry=gphc_number_expiry,
            user_type='Pharmacist',  # Set user_type accordingly
            is_accepted=False # false as not accepted by admin yet
        )

        if visa_expiry:
            locum.visa_expiry = visa_expiry

        if (can_provide_references == 'yes'):
            locum.can_provide_references = True
            # capture two references
            locum.recent_ref_branch_address = request.POST.get('recent_ref_branch_address')
            locum.recent_ref_manager_name = request.POST.get('recent_ref_manager_name')
            locum.recent_ref_manager_email = request.POST.get('recent_ref_manager_email')
            locum.recent_ref_manager_phone = request.POST.get('recent_ref_manager_phone')
            locum.recent_ref_last_worked = request.POST.get('recent_ref_last_worked')

            locum.previous_ref_branch_address = request.POST.get('previous_ref_branch_address')
            locum.previous_ref_manager_name = request.POST.get('previous_ref_manager_name')
            locum.previous_ref_manager_email = request.POST.get('previous_ref_manager_email')
            locum.previous_ref_manager_phone = request.POST.get('previous_ref_manager_phone')
            locum.previous_ref_last_worked = request.POST.get('previous_ref_last_worked')
            # simple server-side validation
            missing = []
            for field_name, label in [
                ('recent_ref_branch_address','Recent Branch Address'),
                ('recent_ref_manager_name','Recent Manager Name'),
                ('recent_ref_manager_email','Recent Manager Email'),
                ('recent_ref_manager_phone','Recent Manager Phone'),
                ('recent_ref_last_worked','Recent Last Worked'),
                ('previous_ref_branch_address','Previous Branch Address'),
                ('previous_ref_manager_name','Previous Manager Name'),
                ('previous_ref_manager_email','Previous Manager Email'),
                ('previous_ref_manager_phone','Previous Manager Phone'),
                ('previous_ref_last_worked','Previous Last Worked'),
            ]:
                if not getattr(locum, field_name):
                    missing.append(label)
            if missing:
                messages.error(request, f"Missing required reference fields: {', '.join(missing)}")
                return render(request, self.template_name)
        else:
            locum.can_provide_references = False
            locum.no_reference_reason = request.POST.get('no_reference_reason')
            if not locum.no_reference_reason:
                messages.error(request, "Please provide a reason for not providing references.")
                return render(request, self.template_name)

        # handling files:
        files_data = request.FILES
        locum.passport_copy = files_data['passport']
        locum.dbs_enhanced_disclosure = files_data['dbs_enhanced_disclosure']
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

        send_registration_emails(firstname, lastname, email, telephone, 'Pharmacist')

        return registration_submitted(request)


class GPRegisterView(View):
    template_name = 'gpRegistration.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        # Extract form data from POST request
        title = request.POST.get('title')
        password = None  # no usable password until the locum sets one from the approval email
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        date_of_birth = request.POST.get('date_of_birth')
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        county = request.POST.get('county')
        post_code = request.POST.get('post_code')
        nationality = request.POST.get('nationality')
        smartcard_number = request.POST.get('smartcard_number', '')
        gmc_number = request.POST.get('gmc_number')
        insurance_expiry_date = request.POST.get('insurance_expiry_date')
        gmc_expiry = request.POST.get('gmc_expiry', '')

        missing = missing_registration_fields(request, COMMON_REGISTRATION_FIELDS + [
            ('gmc_number', 'GMC Number'),
            ('insurance_expiry_date', 'Insurance Expiry Date'),
        ], [
            ('insurance', 'Insurance'),
        ])
        if missing:
            messages.error(request, f"Please complete the required fields: {', '.join(missing)}")
            return render(request, self.template_name)
        # Check if a user with the same email and user_type 'Pharmacist' already exists
        if Locum.objects.filter(email=email, user_type='GP').exists():
            messages.error(
                request, "A user with this email and role already exists.")
            return render(request, self.template_name)
        locum = Locum(
            title=title,
            password=password,
            first_name=firstname,
            last_name=lastname,
            date_of_birth=date_of_birth,
            email=email,
            telephone=telephone,
            county=county,
            post_code=post_code,
            nationality=nationality,
            smartcard_number=smartcard_number,
            gmc_number=gmc_number,
            insurance_expiry_date=insurance_expiry_date,

            user_type='GP',  # Set user_type accordingly
            is_accepted=False # false as not accepted by admin yet
        )
        if gmc_expiry:
            locum.gmc_expiry = gmc_expiry
        # references
        can_provide_references = request.POST.get('can_provide_references')
        if can_provide_references == 'yes':
            locum.can_provide_references = True
            locum.recent_ref_branch_address = request.POST.get('recent_ref_branch_address')
            locum.recent_ref_manager_name = request.POST.get('recent_ref_manager_name')
            locum.recent_ref_manager_email = request.POST.get('recent_ref_manager_email')
            locum.recent_ref_manager_phone = request.POST.get('recent_ref_manager_phone')
            locum.recent_ref_last_worked = request.POST.get('recent_ref_last_worked')
            
            locum.previous_ref_branch_address = request.POST.get('previous_ref_branch_address')
            locum.previous_ref_manager_name = request.POST.get('previous_ref_manager_name')
            locum.previous_ref_manager_email = request.POST.get('previous_ref_manager_email')
            locum.previous_ref_manager_phone = request.POST.get('previous_ref_manager_phone')
            locum.previous_ref_last_worked = request.POST.get('previous_ref_last_worked')
            missing = []
            for field_name, label in [
                ('recent_ref_branch_address','Recent Branch Address'),
                ('recent_ref_manager_name','Recent Manager Name'),
                ('recent_ref_manager_email','Recent Manager Email'),
                ('recent_ref_manager_phone','Recent Manager Phone'),
                ('recent_ref_last_worked','Recent Last Worked'),
                ('previous_ref_branch_address','Previous Branch Address'),
                ('previous_ref_manager_name','Previous Manager Name'),
                ('previous_ref_manager_email','Previous Manager Email'),
                ('previous_ref_manager_phone','Previous Manager Phone'),
                ('previous_ref_last_worked','Previous Last Worked'),
            ]:
                if not getattr(locum, field_name):
                    missing.append(label)
            if missing:
                messages.error(request, f"Missing required reference fields: {', '.join(missing)}")
                return render(request, self.template_name)
        else:
            locum.can_provide_references = False
            locum.no_reference_reason = request.POST.get('no_reference_reason')
            if not locum.no_reference_reason:
                messages.error(request, "Please provide a reason for not providing references.")
                return render(request, self.template_name)
        # handling files:
        files_data = request.FILES
        locum.insurance = files_data['insurance']
        if 'gmc_certificate' in files_data:
            locum.visa_residence_permit = files_data['gmc_certificate']

        for i in range(1, 16):  # Assuming up to 15 accreditations
            field_name = f'accreditations{i}'
            if field_name in files_data:
                setattr(locum, field_name, files_data[field_name])

        locum.save()

        send_registration_emails(firstname, lastname, email, telephone, 'GP')

        return registration_submitted(request)


class TechDesRegisterView(View):
    template_name = 'techDesRegistration.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        # Extract form data from POST request
        title = request.POST.get('title')
        password = None  # no usable password until the locum sets one from the approval email
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        county = request.POST.get('county')
        post_code = request.POST.get('post_code')
        nationality = request.POST.get('nationality')
        gphc_number = request.POST.get('gphc_number', '')
        qualified_date = request.POST.get('qualified_date')
        passport_expiry_date = request.POST.get('passport_expiry_date')
        visa_expiry = request.POST.get('visa_expiry')
        can_provide_references = request.POST.get('can_provide_references')
        user_type = request.POST.get('type')

        missing = missing_registration_fields(request, COMMON_REGISTRATION_FIELDS + [
            ('gender', 'Gender'),
            ('type', 'Role'),
            ('qualified_date', 'Qualified Date'),
            ('passport_expiry_date', 'Passport Expiry Date'),
        ], [
            ('passport', 'Passport'),
            ('qualification_certificate', 'Qualification Certificate'),
        ])
        if missing:
            messages.error(request, f"Please complete the required fields: {', '.join(missing)}")
            return render(request, self.template_name)
        # Check if a user with the same email and user_type 'Pharmacist' already exists
        if Locum.objects.filter(email=email, user_type__in=['Technician', 'Dispenser']).exists():
            messages.error(
                request, "A user with this email and role already exists.")
            return render(request, self.template_name)
        locum = Locum(
            title=title,
            password=password,
            first_name=firstname,
            last_name=lastname,
            gender=gender,
            date_of_birth=date_of_birth,
            email=email,
            telephone=telephone,
            county=county,
            post_code=post_code,
            nationality=nationality,
            gphc_number=gphc_number,
            qualified_date=qualified_date,
            passport_expiry_date=passport_expiry_date,
            can_provide_references=can_provide_references,
            user_type=user_type,  # Set user_type accordingly
            is_accepted=False # false as not accepted by admin yet
        )
        if visa_expiry:
            locum.visa_expiry = visa_expiry
        if (can_provide_references == 'yes'):
            locum.can_provide_references = True
            # capture two references
            locum.recent_ref_branch_address = request.POST.get('recent_ref_branch_address')
            locum.recent_ref_manager_name = request.POST.get('recent_ref_manager_name')
            locum.recent_ref_manager_email = request.POST.get('recent_ref_manager_email')
            locum.recent_ref_manager_phone = request.POST.get('recent_ref_manager_phone')
            locum.recent_ref_last_worked = request.POST.get('recent_ref_last_worked')
            
            locum.previous_ref_branch_address = request.POST.get('previous_ref_branch_address')
            locum.previous_ref_manager_name = request.POST.get('previous_ref_manager_name')
            locum.previous_ref_manager_email = request.POST.get('previous_ref_manager_email')
            locum.previous_ref_manager_phone = request.POST.get('previous_ref_manager_phone')
            locum.previous_ref_last_worked = request.POST.get('previous_ref_last_worked')
            # simple server-side validation
            missing = []
            for field_name, label in [
                ('recent_ref_branch_address','Recent Branch Address'),
                ('recent_ref_manager_name','Recent Manager Name'),
                ('recent_ref_manager_email','Recent Manager Email'),
                ('recent_ref_manager_phone','Recent Manager Phone'),
                ('recent_ref_last_worked','Recent Last Worked'),
                ('previous_ref_branch_address','Previous Branch Address'),
                ('previous_ref_manager_name','Previous Manager Name'),
                ('previous_ref_manager_email','Previous Manager Email'),
                ('previous_ref_manager_phone','Previous Manager Phone'),
                ('previous_ref_last_worked','Previous Last Worked'),
            ]:
                if not getattr(locum, field_name):
                    missing.append(label)
            if missing:
                messages.error(request, f"Missing required reference fields: {', '.join(missing)}")
                return render(request, self.template_name)
        else:
            locum.can_provide_references = False
            locum.no_reference_reason = request.POST.get('no_reference_reason')
            if not locum.no_reference_reason:
                messages.error(request, "Please provide a reason for not providing references.")
                return render(request, self.template_name)

        # handling files:
        files_data = request.FILES
        locum.passport_copy = files_data['passport']
        locum.qualification_certificate = files_data['qualification_certificate']
        if 'visa_residence_permit' in files_data:
            locum.visa_residence_permit = files_data['visa_residence_permit']

        for i in range(1, 16):  # Assuming up to 15 accreditations
            field_name = f'accreditations{i}'
            if field_name in files_data:
                setattr(locum, field_name, files_data[field_name])
        locum.save()

        send_registration_emails(firstname, lastname, email, telephone, user_type)

        return registration_submitted(request)


class NursesRegisterView(View):
    template_name = 'NursesRegistration.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        # Extract form data from POST request
        title = request.POST.get('title')
        password = None  # no usable password until the locum sets one from the approval email
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        gender = request.POST.get('gender')
        date_of_birth = request.POST.get('date_of_birth')
        email = request.POST.get('email')
        telephone = request.POST.get('telephone')
        county = request.POST.get('county')
        post_code = request.POST.get('post_code')
        nationality = request.POST.get('nationality')
        nmc_number = request.POST.get('nmc_number')
        user_type = request.POST.get('type')
        dbs_service_number = request.POST.get('dbs_service_number', '')
        nmc_expiry = request.POST.get('nmc_expiry')

        missing = missing_registration_fields(request, COMMON_REGISTRATION_FIELDS + [
            ('gender', 'Gender'),
            ('type', 'Role'),
            ('nmc_number', 'NMC Number'),
            ('nmc_expiry', 'NMC Expiry Date'),
        ], [
            ('nmc_certificate', 'NMC Certificate'),
        ])
        if missing:
            messages.error(request, f"Please complete the required fields: {', '.join(missing)}")
            return render(request, self.template_name)

        if Locum.objects.filter(email=email, user_type__in=['Nurse', 'ANPNurse']).exists():
            messages.error(
                request, "A user with this email and role already exists.")
            return render(request, self.template_name)
        locum = Locum(
            title=title,
            password=password,
            first_name=firstname,
            last_name=lastname,
            gender=gender,
            date_of_birth=date_of_birth,
            email=email,
            telephone=telephone,
            county=county,
            post_code=post_code,
            nationality=nationality,
            nmc_number=nmc_number,
            dbs_service_number=dbs_service_number,
            nmc_expiry=nmc_expiry,
            user_type=user_type,  # Set user_type accordingly
            is_accepted=False # false as not accepted by admin yet
        )
        # references
        can_provide_references = request.POST.get('can_provide_references')
        if can_provide_references == 'yes':
            locum.can_provide_references = True
            locum.recent_ref_branch_address = request.POST.get('recent_ref_branch_address')
            locum.recent_ref_manager_name = request.POST.get('recent_ref_manager_name')
            locum.recent_ref_manager_email = request.POST.get('recent_ref_manager_email')
            locum.recent_ref_manager_phone = request.POST.get('recent_ref_manager_phone')
            locum.recent_ref_last_worked = request.POST.get('recent_ref_last_worked')
            
            locum.previous_ref_branch_address = request.POST.get('previous_ref_branch_address')
            locum.previous_ref_manager_name = request.POST.get('previous_ref_manager_name')
            locum.previous_ref_manager_email = request.POST.get('previous_ref_manager_email')
            locum.previous_ref_manager_phone = request.POST.get('previous_ref_manager_phone')
            locum.previous_ref_last_worked = request.POST.get('previous_ref_last_worked')
            missing = []
            for field_name, label in [
                ('recent_ref_branch_address','Recent Branch Address'),
                ('recent_ref_manager_name','Recent Manager Name'),
                ('recent_ref_manager_email','Recent Manager Email'),
                ('recent_ref_manager_phone','Recent Manager Phone'),
                ('recent_ref_last_worked','Recent Last Worked'),
                ('previous_ref_branch_address','Previous Branch Address'),
                ('previous_ref_manager_name','Previous Manager Name'),
                ('previous_ref_manager_email','Previous Manager Email'),
                ('previous_ref_manager_phone','Previous Manager Phone'),
                ('previous_ref_last_worked','Previous Last Worked'),
            ]:
                if not getattr(locum, field_name):
                    missing.append(label)
            if missing:
                messages.error(request, f"Missing required reference fields: {', '.join(missing)}")
                return render(request, self.template_name)
        else:
            locum.can_provide_references = False
            locum.no_reference_reason = request.POST.get('no_reference_reason')
            if not locum.no_reference_reason:
                messages.error(request, "Please provide a reason for not providing references.")
                return render(request, self.template_name)

        # handling files:
        files_data = request.FILES
        locum.nmc_certificate = files_data['nmc_certificate']
        if 'dbs_enhanced_disclosure' in files_data:
            locum.dbs_enhanced_disclosure = files_data['dbs_enhanced_disclosure']

        for i in range(1, 16):  # Assuming up to 15 accreditations
            field_name = f'accreditations{i}'
            if field_name in files_data:
                setattr(locum, field_name, files_data[field_name])
        locum.save()

        send_registration_emails(firstname, lastname, email, telephone, user_type)

        return registration_submitted(request)


class LocumProfile(View):
    template_name = 'locumProfile.html'

    def get(self, request):
        return render(request, self.template_name)


def locum_required(view_func):
    # Locum-only pages: the logged-in locum is passed to the view as request.locum
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to continue.')
            return redirect('login')
        locum = Locum.objects.filter(customuser_ptr_id=request.user.id).first()
        if locum is None:
            raise PermissionDenied
        request.locum = locum
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def get_own_job(locum, job_id):
    # A locum can only work with jobs they have an approved application for
    job = get_object_or_404(Job, pk=job_id)
    if not AppliedJob.objects.filter(job=job, locum=locum, approved=True).exists():
        raise PermissionDenied
    return job


def get_own_expense(locum, expense_id):
    expense = get_object_or_404(ShiftExpense, pk=expense_id)
    if expense.locum_id != locum.id:
        raise PermissionDenied
    return expense


@locum_required
def locum_jobs(request, locum_id):
    locum = request.locum
    # The id in the URL must be the logged-in locum's own
    if locum_id != locum.id:
        raise PermissionDenied

    # The locum's approved jobs
    jobs = reports.approved_jobs(locum)
    invoices = LocumInvoice.objects.filter(locum=locum).select_related('job')
    expenses = list(ShiftExpense.objects.filter(locum=locum).select_related('job'))

    # Optional date range (a UK tax year or custom dates) for the financial summary
    today = timezone.localdate()
    date_from, date_to, tax_year, error = ledger.resolve_period(request.GET, today)
    if error:
        messages.error(request, error)

    context = {
        'ledger': ledger.build_ledger(jobs, expenses, date_from, date_to),
        'invoices': invoices,
        'date_from': date_from,
        'date_to': date_to,
        'tax_year': tax_year,
        'tax_years': ledger.tax_year_options(today),
        'expense_categories': ShiftExpense.CATEGORY_CHOICES,
    }
    return render(request, 'locum_jobs.html', context)


@locum_required
def download_report(request):
    # Income and Expenditure Report for the logged-in locum only: there is no
    # locum id in the URL, so nobody else's records can be requested
    report_format = request.GET.get('format')
    if report_format not in ('pdf', 'csv'):
        return HttpResponseBadRequest('Choose PDF or CSV.')
    date_from, date_to, _tax_year, error = ledger.resolve_period(request.GET, timezone.localdate())
    if error:
        return HttpResponseBadRequest(error)

    report = reports.build_report(request.locum, date_from, date_to)
    if report_format == 'csv':
        # utf-8-sig so Excel reads names with accents correctly
        response = HttpResponse(reports.render_csv(report).encode('utf-8-sig'),
                                content_type='text/csv; charset=utf-8')
    else:
        response = HttpResponse(reports.render_pdf(report), content_type='application/pdf')
    filename = reports.report_filename(report, report_format)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'private, no-store'
    return response


def ledger_redirect(request):
    # Back to the locum's ledger, keeping the date range they were looking at
    params = {name: request.POST.get(name) for name in ('from', 'to')
              if ledger.parse_date(request.POST.get(name))}
    url = reverse('locum_jobs', args=[request.locum.id])
    return redirect(f'{url}?{urlencode(params)}' if params else url)


def read_expense_form(request):
    # Returns (cleaned fields, error message); exactly one of them is None
    category = request.POST.get('category')
    if category not in dict(ShiftExpense.CATEGORY_CHOICES):
        return None, 'Choose an expense type.'
    amount = ledger.parse_amount(request.POST.get('amount'))
    if amount is None:
        return None, 'Enter the amount as a number greater than 0, for example 12.50.'
    expense_date = ledger.parse_date(request.POST.get('expense_date'))
    if expense_date is None:
        return None, 'Enter the date of the expense.'
    note = (request.POST.get('note') or '').strip()
    if len(note) > 255:
        return None, 'Keep the note under 255 characters.'
    return {'category': category, 'amount': amount, 'expense_date': expense_date, 'note': note}, None


@require_POST
@locum_required
def add_expense(request, job_id):
    job = get_own_job(request.locum, job_id)
    fields, error = read_expense_form(request)
    if error:
        messages.error(request, error)
    else:
        ShiftExpense.objects.create(job=job, locum=request.locum, **fields)
        messages.success(request, 'Expense added.')
    return ledger_redirect(request)


@require_POST
@locum_required
def edit_expense(request, expense_id):
    expense = get_own_expense(request.locum, expense_id)
    fields, error = read_expense_form(request)
    if error:
        messages.error(request, error)
    else:
        for name, value in fields.items():
            setattr(expense, name, value)
        expense.save()
        messages.success(request, 'Expense updated.')
    return ledger_redirect(request)


@require_POST
@locum_required
def delete_expense(request, expense_id):
    get_own_expense(request.locum, expense_id).delete()
    messages.success(request, 'Expense deleted.')
    return ledger_redirect(request)


@require_POST
def mark_invoice_paid(request, invoice_id):
    invoice = get_object_or_404(LocumInvoice, pk=invoice_id)
    # Only the locum who raised the invoice can mark it as paid
    if not request.user.is_authenticated or invoice.locum_id != request.user.id:
        raise PermissionDenied

    if invoice.status != LocumInvoice.STATUS_PAID:
        invoice.status = LocumInvoice.STATUS_PAID
        invoice.paid_at = timezone.now()
        invoice.save()
        messages.success(request, 'Invoice marked as paid.')

    return redirect('locum_jobs', locum_id=request.user.id)


@locum_required
def generate_receipt_form(request, job_id):
    job = get_own_job(request.locum, job_id)
    # Determine if the job spans multiple days
    has_multiple_days = job.start_date != job.end_date

    # Prepare context based on job details
    context = {
        'job': job,
        'has_multiple_days': has_multiple_days,
        'start_date': job.start_date,
        'end_date': job.end_date,
        'payment_terms': INVOICE_PAYMENT_TERMS,
    }

    return render(request, 'generate_receipt_form.html', context)


@locum_required
def generate_pdf_receipt(request, job_id):
    job = get_own_job(request.locum, job_id)
    locum = request.locum

    if request.method == 'POST':
        account_number = request.POST.get('account_number')
        sort_code = request.POST.get('sort_code')
        current_date = datetime.now()
        formatted_date = current_date.strftime('%d %B %Y')
        invoice_number = request.POST.get('invoice_number', ' ')

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{job_id}.pdf"'

        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter

        # Set up left and right box positions
        left_box_width = width // 2 - 50
        right_box_start_x = width // 2 + 50

        # Header and Details (Centered and Larger)
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width // 2, height - 50,
                            "Invoice for Locum Services")

        # Left Box - Locum and Bank Details
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 100, "Locum Details:")
        p.drawString(50, height - 120,
                     f"Name: {locum.firstname} {locum.lastname}")
        p.drawString(50, height - 140, f"GPhC Number: {locum.gphc_number}")
        p.drawString(50, height - 160, f"Locum Address: {locum.county}")
        p.drawString(50, height - 180, f"Contact Details: {locum.telephone}")

        p.drawString(50, height - 220, "Bank Details:")
        p.drawString(50, height - 240, f"Account no: {account_number}")
        p.drawString(50, height - 260, f"Sort Code: {sort_code}")

        # Right Box - Pharmacy and Invoice Details
        p.drawString(right_box_start_x, height - 100, "Pharmacy Details:")
        p.drawString(right_box_start_x, height - 120,
                     f"Business: {job.company_name}")
        p.drawString(right_box_start_x, height - 140, "FAO:")
        p.drawString(right_box_start_x, height - 160,
                     f"Pharmacy Address: {job.county}")
        p.drawString(right_box_start_x, height - 180,
                     f"Contact Details: {job.telephone}")

        # Add one-line space before Invoice Number and Date
        p.drawString(right_box_start_x, height - 210, "")  # Spacer line

        p.drawString(right_box_start_x, height - 230,
                     f"Invoice Number: {invoice_number}")
        p.drawString(right_box_start_x, height -
                     250, f"Date: {formatted_date}")

        # Table Headers
        table_y_position = height - 320
        headers = ["Date", "Hours Worked",
                   "No of hours worked", "Hourly Rate", "Subtotal"]
        col_widths = [100, 120, 120, 100, 100]  # Adjusted column widths

        x_position = 50
        for header, width in zip(headers, col_widths):
            p.rect(x_position, table_y_position, width, 20, fill=1)
            p.setFillColor(colors.white)
            p.drawString(x_position + 5, table_y_position + 5, header)
            p.setFillColor(colors.black)
            x_position += width

        # Table Entries
        table_y_position -= 20
        total_cost = 0.0  # Total of all subtotals
        for key in request.POST:
            if key.startswith('working_hours_'):
                date = key.split('_')[2]
                working_hours = request.POST.get(f'working_hours_{date}')
                hours_worked = request.POST.get(f'hours_worked_{date}')
                rate = float(job.locum_rate)
                subtotal = float(hours_worked) * rate
                entries = [
                    date, f"{working_hours} ", f"{hours_worked} hours", f"£{rate:.2f}", f"£{subtotal:.2f}"]

                x_position = 50
                for entry, width in zip(entries, col_widths):
                    p.rect(x_position, table_y_position, width, 20)
                    p.drawString(x_position + 5, table_y_position + 5, entry)
                    x_position += width
                total_cost += subtotal
                table_y_position -= 20

        # Additional Services Section
        additional_services = [
            ("Additional Services", "Price", "Quantity", "Subtotal"),
            ("", "", "", ""),  # Empty row 1
            ("", "", "", ""),  # Empty row 2
            ("", "", "", "")   # Empty row 3
        ]

        # Position for Additional Services Table
        additional_table_y_position = table_y_position
        # Adjusted column widths for additional services
        additional_col_widths = [220, 120, 100, 100]

        # Draw Additional Services Table Header
        x_position = 50
        for header, width in zip(additional_services[0], additional_col_widths):
            p.setFillColor(colors.lightgrey)
            p.rect(x_position, additional_table_y_position, width, 20, fill=1)
            p.setFillColor(colors.black)
            p.drawString(x_position + 5,
                         additional_table_y_position + 5, header)
            x_position += width

        # Draw Additional Services Table Entries
        for service in additional_services[1:]:
            additional_table_y_position -= 20
            x_position = 50
            for entry, width in zip(service, additional_col_widths):
                p.rect(x_position, additional_table_y_position, width, 20)
                p.drawString(x_position + 5,
                             additional_table_y_position + 5, entry)
                x_position += width
        # Additional Information Section
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, additional_table_y_position -
                     60, "Additional Information:")
        p.drawString(right_box_start_x + col_widths[-1] + 20,
                     additional_table_y_position - 60, f"Total: £{total_cost:.2f}")
        p.drawRightString(letter[0] - 40, additional_table_y_position - 80,
                          f"Payment Terms: {INVOICE_PAYMENT_TERMS}")
        # Finalize and Return PDF
        p.showPage()
        p.save()

        # Track the invoice; regenerating the same invoice number keeps its status
        LocumInvoice.objects.update_or_create(
            job=job, locum=locum, invoice_number=invoice_number.strip(),
            defaults={'total_amount': round(total_cost, 2)},
        )
        return response

    # For GET requests, show the data entry form
    return render(request, 'generate_receipt_form.html', {
        'job': job, 'payment_terms': INVOICE_PAYMENT_TERMS})


@locum_required
def locum_calander(request, user_id):
    locum = request.locum
    if user_id != locum.id:
        raise PermissionDenied
    Availability = LocumAvailability.objects.filter(locum_id=locum.id)
    currentLocum = locum
    return render(request, 'locum_calander.html', {'Availability': Availability, 'currentLocum': currentLocum})


@locum_required
def avail_added(request, user_id):
    locum = request.locum
    if user_id != locum.id:
        raise PermissionDenied
    if request.method == 'POST':
        date = request.POST.get('Date')  # Get the date from form data
        timings = request.POST.get('Timings')  # Get the timings from form data

        # Create LocumAvailability object
        LocumAvailability.objects.create(
            locum=locum,
            date=date,
            timings=timings
        )

        # Redirect back to the calendar page
        return redirect('locum_calander', user_id=user_id)

    # Handle GET request if needed (not necessary for form submission)
    return render(request, 'locum_calander.html', {'currentLocum': locum})
