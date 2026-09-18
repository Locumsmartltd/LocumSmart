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
    pharmacy_name = models.CharField(max_length=255)
    manager_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    post_code = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    street_address = models.CharField(max_length=100, null=True, blank=True)

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


class EmailTrackingLog(models.Model):
    to_email = models.EmailField()
    cc_email = models.EmailField(blank=True, null=True)
    from_email = models.EmailField()
    job_ids = models.JSONField(blank=True, default=list)  # Use ArrayField to store job IDs
    invoice_type = models.CharField(max_length=255)
    invoice_no = models.CharField(max_length=50)  # Invoice number column
    timestamp = models.DateTimeField(auto_now_add=True)  # Automatically set the timestamp when the record is created

    def __str__(self):
        return f"Email sent to {self.to_email} regarding {self.invoice_type} on {self.timestamp}"
