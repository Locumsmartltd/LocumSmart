from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from appAdmin.models import Admin, CustomUser, Employer
from locum.models import AppliedJob, Job, Locum
from locum.staffing_models import StaffingBranch


class Command(BaseCommand):
    help = 'Create local test accounts and a sample Montu job application for the staffing portal.'

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3' or not settings.DEBUG:
            raise CommandError('Use LocumSmart.development_settings to seed the local demo.')
        employer, _ = Employer.objects.get_or_create(
            email='demo.montu.employer@locumsmart.test',
            defaults={'first_name': 'Montu', 'last_name': 'Demo', 'pharmacy_name': 'Montu Pharmacy (Demo)',
                      'phone_number': '07000000000', 'post_code': 'E1 1AA', 'city': 'London'},
        )
        manager_email = 'demo.montu.manager@locumsmart.test'
        call_command('provision_staffing_manager', employer.pk, manager_email,
                     first_name='Tim', last_name='Demo', branch='Montu Main Site')
        for name in ('North Branch (example)', 'South Branch (example)'):
            StaffingBranch.objects.get_or_create(employer=employer, name=name)
        admin, _ = Admin.objects.get_or_create(
            email='demo.staffing.admin@locumsmart.test',
            defaults={'first_name': 'Staffing', 'last_name': 'Demo', 'is_admin': True},
        )
        admin.user_permissions.add(*Permission.objects.filter(content_type__app_label='appAdmin',
            content_type__model='admin', codename__in=(
                'can_delete_locum', 'can_register_employer', 'can_register_staff',
            )))
        password = 'StaffingDemo123!'
        for user in (CustomUser.objects.get(email=manager_email), admin):
            user.set_password(password)
            user.save(update_fields=['password'])
        candidate, _ = Locum.objects.get_or_create(
            email='demo.staffing.locum@locumsmart.test',
            defaults={'first_name': 'Casey', 'last_name': 'Demo', 'Email': 'demo.staffing.locum@locumsmart.test',
                      'date_of_birth': date(1995, 1, 1), 'is_accepted': True, 'user_type': 'Dispenser'},
        )
        today = timezone.localdate(timezone=ZoneInfo('Europe/London'))
        job, _ = Job.objects.get_or_create(
            employer=employer, branch_no='STAFFING-DEMO', start_date=today,
            defaults={'end_date': today, 'pharmacy_name': employer.pharmacy_name, 'name': 'Montu Demo',
                      'email': employer.email, 'telephone': employer.phone_number, 'county': employer.city,
                      'post_code': employer.post_code, 'locum_rate': Decimal('18.00'),
                      'expenses_offered': Decimal('0.00'), 'times_required': '8', 'approved': True,
                      'dispenser_required': True},
        )
        AppliedJob.objects.get_or_create(job=job, locum=candidate)
        self.stdout.write(f'Employer Manager: {manager_email}')
        self.stdout.write(f'Admin: {admin.email}')
        self.stdout.write(f'Password for both: {password}')
        self.stdout.write(f'Sample Dispenser application: Job #{job.pk} on {today}.')
