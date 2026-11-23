from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    # Add custom related_name for groups and user_permissions to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_groups',  # Custom related_name for groups
        related_query_name='custom_user_group',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        # Custom related_name for user_permissions
        related_name='custom_user_permissions',
        related_query_name='custom_user_permission',
        blank=True,
    )

    # No additional fields in the base user model

    class Meta(AbstractUser.Meta):
        indexes = [
            # Registration checks for an existing account by email on every submit
            models.Index(fields=['email'], name='customuser_email_idx'),
            # Admin search-as-you-type (prefix lookups on names)
            models.Index(fields=['first_name'], name='customuser_first_name_idx'),
            models.Index(fields=['last_name'], name='customuser_last_name_idx'),
        ]


class Admin(CustomUser):
    is_admin = models.BooleanField(default=False)

    class Meta:
        permissions = [
            ('can_register_employer', ('Can register employer')),
            ('can_delete_locum', ('Can delete locum')),
            ('can_register_staff', ('Can register staff')),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Check if the instance is being created (no primary key)
        if not self.pk:
            # Generate a username if not provided based on firstname and lastname
            if not self.username:
                self.username = self.generate_username()

            # Hash the password if it's a new instance
            self.password = make_password(self.password)
        super().save(*args, **kwargs)  # Call the save method of the parent class

    def generate_username(self):
        # Generate a username based on firstname and lastname
        base_username = f"{self.first_name.lower()}.{self.last_name.lower()}"
        username = base_username
        counter = 1

        # Check if the generated username is unique
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}.{counter}"
            counter += 1

        return username


class Employer(CustomUser):
    pharmacy_name = models.CharField(max_length=255, db_index=True)
    manager_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    post_code = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    city = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    street_address = models.CharField(max_length=100, null=True, blank=True)
    # The address a candidate must use on their own invoice can differ from the
    # contact details LocumSmart uses for its agency invoice.
    candidate_invoice_company = models.CharField(max_length=255, blank=True)
    candidate_invoice_contact = models.CharField(max_length=255, blank=True)
    candidate_invoice_email = models.EmailField(blank=True)
    candidate_invoice_address = models.TextField(blank=True)

    @property
    def candidate_invoice_company_display(self):
        return self.candidate_invoice_company or self.pharmacy_name

    @property
    def candidate_invoice_contact_display(self):
        return self.candidate_invoice_contact or self.manager_name or self.get_full_name()

    @property
    def candidate_invoice_email_display(self):
        return self.candidate_invoice_email or self.email

    @property
    def candidate_invoice_address_display(self):
        if self.candidate_invoice_address:
            return self.candidate_invoice_address
        return ', '.join(filter(None, (self.street_address, self.city, self.post_code)))

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Check if the instance is being created (no primary key)
        if not self.pk:
            # Generate a username if not provided based on firstname and lastname
            if not self.username:
                self.username = self.generate_username()

            # Hash the password if it's a new instance
            self.password = make_password(self.password)
        super().save(*args, **kwargs)  # Call the save method of the parent class

    def generate_username(self):
        # Generate a username based on firstname and lastname
        base_username = f"{self.first_name.lower()}.{self.last_name.lower()}"
        username = base_username
        counter = 1

        # Check if the generated username is unique
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}.{counter}"
            counter += 1

        return username
    
    def base_username(self):
        # Generate a username based on firstname and lastname
        base_username = f"{self.first_name.lower()} {self.last_name.lower()}"
        username = base_username
        return username


DEFAULT_PHARMACY_BOOKING_TERMS = """Please note any cancellation within 72 hours prior to the booking may result in the pharmacy claiming loss of earnings if the shift is not covered. Cancellations made because a better offer was received elsewhere are not acceptable once a booking has been confirmed.

If you are offered further bookings directly by the pharmacy, you must inform a LocumSmart coordinator and must not book directly, in line with the terms agreed during registration.

Sundays and bank holidays are not included in the notice period. Notice hours are Monday to Friday, 9am to 5pm, and Saturday, 9am to 3pm. Cancellation notice must be provided by email.

While on the pharmacy premises, locums are expected to use their time responsibly and complete the duties normally expected of their role."""

DEFAULT_PRIMARY_CARE_BOOKING_TERMS = """Please arrive 10 minutes before the scheduled start time.

Our normal invoice payment schedule is two to four weeks, depending on payment from the surgery or practice. Do not discuss hourly rates with practice staff. Further bookings offered directly by the surgery or practice must be reported to LocumSmart, and payment discussions must be made with LocumSmart only.

Locum doctors, physician associates and practice nurses must make their compliance documents available to the practice and LocumSmart on request, and must notify LocumSmart of any changes. LocumSmart carries out periodic compliance checks. The practice must confirm the accuracy of supplied information before an assignment begins.

Cancellation within 72 hours of a confirmed booking may result in the surgery claiming loss of earnings unless there is a verifiable emergency. Cancelling because a better offer was received elsewhere is considered unprofessional and may result in a complaint to the relevant registration body."""


class BookingConfirmationTerms(models.Model):
    """Singleton content used in booking-confirmation emails to candidates."""

    pharmacy_candidate_terms = models.TextField(default=DEFAULT_PHARMACY_BOOKING_TERMS)
    primary_care_candidate_terms = models.TextField(default=DEFAULT_PRIMARY_CARE_BOOKING_TERMS)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def current(cls):
        terms, _created = cls.objects.get_or_create(pk=1)
        return terms

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)

    def __str__(self):
        return 'Booking confirmation terms'


class EmailTrackingLog(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
    ]

    # Email fields stay empty until the invoice is actually emailed
    to_email = models.EmailField(blank=True)
    cc_email = models.EmailField(blank=True, null=True)
    from_email = models.EmailField(blank=True)
    job_ids = models.JSONField(blank=True, default=list)  # Use ArrayField to store job IDs
    invoice_type = models.CharField(max_length=255)
    invoice_no = models.CharField(max_length=50)  # Invoice number column
    timestamp = models.DateTimeField(auto_now_add=True)  # Automatically set the timestamp when the record is created
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    emailed_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Email sent to {self.to_email} regarding {self.invoice_type} on {self.timestamp}"
