from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

from appAdmin.models import CustomUser, Employer
from locum.staffing_models import StaffingBranch, StaffingManager
from locum.staffing_workflow import pilot_employers


class Command(BaseCommand):
    help = 'Create an invite-only staffing manager and a default branch for an existing employer.'

    def add_arguments(self, parser):
        parser.add_argument('employer_id', type=int)
        parser.add_argument('email')
        parser.add_argument('--first-name', default='')
        parser.add_argument('--last-name', default='')
        parser.add_argument('--branch')

    @transaction.atomic
    def handle(self, *args, **options):
        employer = Employer.objects.select_for_update().filter(pk=options['employer_id']).first()
        if employer is None:
            raise CommandError('Employer not found.')
        if not pilot_employers().filter(pk=employer.pk).exists():
            raise CommandError('Staffing portal access is currently available only to the Montu pilot employer.')
        email = options['email'].strip().lower()
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError('Enter a valid manager email address.') from exc
        if len(email) > 150:
            raise CommandError('A manager email can have up to 150 characters.')
        branch = (options['branch'] or employer.pharmacy_name).strip()
        if not branch or len(branch) > 120:
            raise CommandError('Enter a branch name up to 120 characters.')
        names = [options['first_name'].strip(), options['last_name'].strip()]
        if any(len(name) > 150 for name in names):
            raise CommandError('Each name can have up to 150 characters.')

        users = list(CustomUser.objects.filter(email__iexact=email)[:2])
        if users:
            if len(users) != 1 or not StaffingManager.objects.filter(user=users[0], employer=employer).exists():
                raise CommandError('This email already belongs to a different account.')
        else:
            if CustomUser.objects.filter(username__iexact=email).exists():
                raise CommandError('This email is already in use as a username.')
            user = CustomUser.objects.create_user(
                username=email, email=email, first_name=names[0], last_name=names[1])
            StaffingManager.objects.create(user=user, employer=employer)

        if not employer.staffing_branches.filter(name__iexact=branch).exists():
            StaffingBranch.objects.create(employer=employer, name=branch)
        self.stdout.write(self.style.SUCCESS(f'Manager account ready for {employer.pharmacy_name}.'))
        self.stdout.write('The manager can choose Employer Manager in Forgot password to set up their password.')
