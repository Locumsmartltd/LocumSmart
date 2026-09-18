from django.db import models
from appAdmin.models import CustomUser, Employer
from django.contrib.auth.hashers import make_password
from django.utils.deconstruct import deconstructible
import os
from datetime import datetime
from datetime import date


@deconstructible
class UserDocumentPath:
    def __call__(self, instance, filename):
        # Generate a folder path based on the user's telephone
        user_folder = f"user_{instance.telephone}"
        return os.path.join(user_folder, filename)

# Create your models here.


class Locum(CustomUser):
    # Add fields specific to locum users
    title = models.CharField(max_length=100)
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    is_accepted = models.BooleanField(default=True)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    Email = models.EmailField()
    telephone = models.CharField(max_length=20)
    county = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)
    nationality = models.CharField(max_length=100)
    smartcard_number = models.CharField(max_length=20, blank=True)
    gmc_number = models.CharField(max_length=20, blank=True)
    gmc_certificate = models.FileField(
        upload_to=UserDocumentPath(), blank=True)
    gmc_expiry = models.DateField(blank=True, null=True)
    gphc_number = models.CharField(max_length=20, blank=True, null=True)
    gphc_number_expiry = models.DateField(blank=True, null=True)
    qualified_date = models.DateField(blank=True, null=True)
    nmc_number = models.CharField(max_length=20, blank=True)
    nmc_certificate = models.FileField(
        upload_to=UserDocumentPath(), blank=True)
    nmc_expiry = models.DateField(blank=True, null=True)
    can_provide_references = models.BooleanField(default=False, blank=True)
    passport_copy = models.FileField(upload_to=UserDocumentPath(), blank=True)
    passport_expiry_date = models.DateField(blank=True, null=True)
    visa_residence_permit = models.FileField(
        upload_to=UserDocumentPath(), blank=True)
    visa_expiry = models.DateField(blank=True, null=True)
    dbs_enhanced_disclosure = models.FileField(
        upload_to=UserDocumentPath(), blank=True)
    dbs_service_number = models.CharField(max_length=20, blank=True, null=True)
    safeguarding_level2 = models.FileField(
        upload_to=UserDocumentPath(), blank=True)
    insurance = models.FileField(upload_to=UserDocumentPath(), blank=True)
    insurance_expiry_date = models.DateField(blank=True, null=True)
    qualification_certificate = models.FileField(
        upload_to=UserDocumentPath(), blank=True)
    accreditations1 = models.FileField(upload_to=UserDocumentPath(
    ), blank=True, null=True)  # Repeat for additional accreditations
    accreditations2 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations3 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations4 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations5 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations6 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations7 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations8 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations9 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations10 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations11 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations12 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations13 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations14 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    accreditations15 = models.FileField(
        upload_to=UserDocumentPath(), blank=True, null=True)
    user_type = models.CharField(max_length=100, null=True)
    # References: when can_provide_references is true, capture two refs; otherwise, capture reason
    recent_ref_branch_address = models.CharField(max_length=255, blank=True, null=True)
    recent_ref_manager_name = models.CharField(max_length=255, blank=True, null=True)
    recent_ref_manager_email = models.EmailField(blank=True, null=True)
    recent_ref_manager_phone = models.CharField(max_length=50, blank=True, null=True)
    recent_ref_last_worked = models.DateField(blank=True, null=True)

    previous_ref_branch_address = models.CharField(max_length=255, blank=True, null=True)
    previous_ref_manager_name = models.CharField(max_length=255, blank=True, null=True)
    previous_ref_manager_email = models.EmailField(blank=True, null=True)
    previous_ref_manager_phone = models.CharField(max_length=50, blank=True, null=True)
    previous_ref_last_worked = models.DateField(blank=True, null=True)

    no_reference_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        # Check if the instance is being created (no primary key)
        if not self.pk:
            # Generate a username if not provided based on firstname and lastname
            if not self.username:
                self.username = self.generate_username()

            self.firstname = self.first_name
            self.lastname = self.last_name
            self.Email = self.email
            # Hash the password if it's a new instance
            self.password = make_password(self.password)

        super().save(*args, **kwargs)  # Call the save method of the parent class

    def generate_username(self):
        # Generate a username based on firstname and lastname
        base_username = f"{self.firstname.lower()}.{self.lastname.lower()}"
        username = base_username
        counter = 1

        # Check if the generated username is unique
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}.{counter}"
            counter += 1

        return username


class Job(models.Model):
    pharmacy_name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    county = models.CharField(max_length=100)
    post_code = models.CharField(max_length=20)
    branch_no = models.CharField(max_length=255, blank=True)

    # Locum role requirements (Boolean fields for each role)
    pharmacist_required = models.BooleanField(default=False)
    technician_required = models.BooleanField(default=False)
    dispenser_required = models.BooleanField(default=False)
    nurse_required = models.BooleanField(default=False)
    anp_nurse_required = models.BooleanField(default=False)
    gp_required = models.BooleanField(default=False)
    optometrist_required = models.BooleanField(default=False)
    do_required = models.BooleanField(default=False)

    locum_rate = models.DecimalField(max_digits=8, decimal_places=2)
    expenses_offered = models.DecimalField(max_digits=8, decimal_places=2)
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(default=date.today)
    times_required = models.CharField(max_length=255)
    any_other_information = models.TextField()

    approved = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    applied_status = models.BooleanField(default=False)

    locum = models.ForeignKey(
        Locum, on_delete=models.CASCADE, blank=True, null=True)
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)

    # Additional Fields
    booking = models.CharField(max_length=255, blank=True)  # text type
    agency_fee = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    date_of_booking_email = models.DateField(blank=True, null=True)
    locum_payment_status = models.CharField(
        max_length=20, blank=True)  # 'paid'/'unpaid'
    status = models.CharField(max_length=20, blank=True)  # 'paid'/'unpaid'
    date_of_invoice_email = models.DateField(blank=True, null=True)
    source = models.TextField(blank=True)  # text field
    source_commission_date = models.DateField(blank=True, null=True)
    booked_by = models.CharField(max_length=255, blank=True)
    # JSON field for discrete dates
    discrete_dates = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Job - {self.name} ({self.pharmacy_name})"


class AppliedJob(models.Model):
    locum = models.ForeignKey(Locum, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    # Approved by admin (yes/no)
    approved = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    # Went into negotiation (yes/no)
    negotiation = models.BooleanField(default=False)
    # Job completed by locum (yes/no)
    completed = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.job.pharmacy_name}"


class LocumAvailability(models.Model):
    locum = models.ForeignKey(Locum, on_delete=models.CASCADE)
    timings = models.CharField(max_length=255)  # Example: "9 AM - 5 PM"
    date = models.DateField()
    location = models.CharField(max_length=255, blank=True, null=True)
    rate = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)
    # Default proximity range in kilometers
    proximity_range_km = models.DecimalField(
        max_digits=5, decimal_places=2, default=10, blank=True, null=True)

    def __str__(self):
        return f"{self.locum.user.username} - {self.date} ({self.timings}, {self.location})"

    class Meta:
        ordering = ['date', 'timings']  # Order by date and timings by default
