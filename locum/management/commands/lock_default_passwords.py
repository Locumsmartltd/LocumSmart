from django.core.management.base import BaseCommand

from locum.models import Locum

# Passwords that registration used to give every new account
DEFAULT_PASSWORDS = ['password', 'hvzdhajksjnd456787654567']


class Command(BaseCommand):
    help = ("Find locum accounts that still have a default registration password and "
            "remove it, so they must set their own from an emailed link. "
            "Lists the accounts only, unless --apply is given.")

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Remove the default passwords (without this, only report).')

    def handle(self, *args, **options):
        affected = []
        for locum in Locum.objects.all().iterator():
            if any(locum.check_password(p) for p in DEFAULT_PASSWORDS):
                affected.append(locum)
                self.stdout.write(f"{locum.id}\t{locum.user_type}\t{locum.email}")
                if options['apply']:
                    locum.set_unusable_password()
                    # Update the column directly; Locum.save() is for new registrations
                    Locum.objects.filter(pk=locum.pk).update(password=locum.password)

        action = 'Removed the default password from' if options['apply'] else 'Found'
        self.stdout.write(self.style.SUCCESS(f"{action} {len(affected)} account(s)."))
        if affected and not options['apply']:
            self.stdout.write("Run again with --apply to remove these passwords.")
