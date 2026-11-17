from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from appAdmin.models import Admin, Employer
from locum.models import AppliedJob, Job, Locum


class Command(BaseCommand):
    help = 'Create repeatable local employers and jobs for the job-management workflow.'

    def handle(self, *args, **options):
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            self.stderr.write(self.style.ERROR(
                'Refusing to seed a non-SQLite database. Use LocumSmart.development_settings.'))
            return

        admin, admin_created = Admin.objects.get_or_create(
            email='demo.admin@locumsmart.test',
            defaults={
                'first_name': 'Local', 'last_name': 'Admin',
                'password': 'temporary-demo-password', 'is_admin': True,
            })
        if admin_created:
            admin.set_password('LocumSmartDemo123!')
            admin.save(update_fields=['password'])

        green, _ = Employer.objects.get_or_create(
            email='demo.green@locumsmart.test',
            defaults={
                'first_name': 'Grace', 'last_name': 'Green',
                'pharmacy_name': 'Green Cross Pharmacy',
                'manager_name': 'Grace Green', 'phone_number': '07000000001',
                'post_code': 'M1 1AA', 'city': 'Manchester',
                'street_address': '10 Market Street', 'password': 'demo-only',
            })
        blue, _ = Employer.objects.get_or_create(
            email='demo.blue@locumsmart.test',
            defaults={
                'first_name': 'Ben', 'last_name': 'Blue',
                'pharmacy_name': 'Blue Health Pharmacy',
                'manager_name': 'Ben Blue', 'phone_number': '07000000002',
                'post_code': 'B1 1AA', 'city': 'Birmingham',
                'street_address': '22 New Street', 'password': 'demo-only',
            })

        locum, _ = Locum.objects.get_or_create(
            email='demo.locum@locumsmart.test',
            defaults={
                'title': 'Ms', 'first_name': 'Lena', 'last_name': 'Locum',
                'gender': 'Female', 'date_of_birth': date(1990, 1, 1),
                'Email': 'demo.locum@locumsmart.test',
                'telephone': '07000000003', 'county': 'Manchester',
                'post_code': 'M2 2AA', 'nationality': 'British',
                'user_type': 'Pharmacist', 'password': 'demo-only',
            })

        definitions = [
            (green, 'DEMO-LIVE-CONTINUOUS', date(2027, 1, 12), date(2027, 1, 14),
             {'approved': True, 'pharmacist_required': True}),
            (green, 'DEMO-PENDING', date(2027, 2, 3), date(2027, 2, 3),
             {'approved': False, 'technician_required': True}),
            (green, 'DEMO-REJECTED', date(2027, 2, 10), date(2027, 2, 10),
             {'approved': False, 'rejected': True, 'dispenser_required': True}),
            (blue, 'DEMO-LIVE-DISCRETE', date(2027, 3, 1), date(2027, 3, 8),
             {'approved': True, 'gp_required': True,
              'discrete_dates': '["2027-03-01", "2027-03-04", "2027-03-08"]'}),
            (blue, 'DEMO-FILLED', date(2027, 3, 15), date(2027, 3, 15),
             {'approved': True, 'applied_status': True, 'pharmacist_required': True,
              'locum': locum}),
        ]

        jobs = {}
        for employer, marker, start, end, special in definitions:
            role_defaults = {
                'pharmacist_required': False, 'technician_required': False,
                'dispenser_required': False, 'nurse_required': False,
                'anp_nurse_required': False, 'gp_required': False,
                'optometrist_required': False, 'do_required': False,
            }
            role_defaults.update(special)
            job, _ = Job.objects.update_or_create(
                employer=employer, branch_no=marker,
                defaults={
                    'pharmacy_name': employer.pharmacy_name,
                    'company_name': employer.pharmacy_name,
                    'name': employer.base_username(), 'email': employer.email,
                    'telephone': employer.phone_number, 'county': employer.city,
                    'post_code': employer.post_code, 'locum_rate': Decimal('35.00'),
                    'expenses_offered': Decimal('5.00'), 'start_date': start,
                    'end_date': end, 'times_required': '8',
                    'any_other_information': 'Local demo job for workflow testing.',
                    'rejected': False, 'applied_status': False, 'locum': None,
                    'discrete_dates': None, **role_defaults,
                })
            jobs[marker] = job

        AppliedJob.objects.update_or_create(
            locum=locum, job=jobs['DEMO-FILLED'],
            defaults={'approved': True, 'rejected': False})

        self.stdout.write(self.style.SUCCESS(
            'Demo job data is ready: 2 employers and 5 jobs (live, pending, rejected and filled).'))
        self.stdout.write(
            'Local admin: demo.admin@locumsmart.test / LocumSmartDemo123!')
