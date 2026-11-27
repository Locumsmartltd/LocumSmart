import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models


class StaffingManager(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staffing_manager')
    employer = models.ForeignKey('appAdmin.Employer', on_delete=models.PROTECT)


class StaffingBranch(models.Model):
    employer = models.ForeignKey(
        'appAdmin.Employer', on_delete=models.PROTECT, related_name='staffing_branches')
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ('name', 'pk')
        constraints = [
            models.UniqueConstraint(fields=('employer', 'name'), name='staffing_branch_name_unique'),
        ]

    def __str__(self):
        return self.name


class StaffingRequest(models.Model):
    class Role(models.TextChoices):
        PACKAGING = 'packaging', 'Packaging Assistant'
        DISPENSER = 'dispenser', 'Dispenser'
        ACD = 'acd', 'ACD – Accuracy Checking Dispenser'
        ACT = 'act', 'ACT – Accuracy Checking Technician'
        PHARMACIST = 'pharmacist', 'Pharmacist'
        TECHNICIAN = 'technician', 'Pharmacy Technician'
        NURSE = 'nurse', 'Practice Nurse'
        ANP_NURSE = 'anp_nurse', 'ANP Nurse'
        GP = 'gp', 'GP'
        OPTOMETRIST = 'optometrist', 'Optometrist'
        DISPENSING_OPTICIAN = 'dispensing_optician', 'Dispensing Optician'

    branch = models.ForeignKey(StaffingBranch, on_delete=models.PROTECT)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    shift_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    role = models.CharField(max_length=20, choices=Role.choices)
    budget = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    submission_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    first_request = models.ForeignKey(
        'self', on_delete=models.PROTECT, related_name='additional_requests', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StaffingPosition(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Staff needed'
        PROPOSED = 'proposed', 'Awaiting manager approval'
        APPROVED = 'approved', 'Manager approved'
        BOOKED = 'booked', 'Booked'
        ATTENDED = 'attended', 'Attended'
        ISSUE = 'issue', 'No-show / issue'
        CANCELLED = 'cancelled', 'Cancelled'

    request = models.ForeignKey(StaffingRequest, on_delete=models.PROTECT, related_name='positions')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    candidate_name = models.CharField(max_length=301, blank=True)
    application = models.OneToOneField(
        'locum.AppliedJob', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='staffing_position')
    from_application = models.BooleanField(default=False)
    client_rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    proposal_note = models.CharField(max_length=500, blank=True)
    actual_start = models.TimeField(blank=True, null=True)
    actual_end = models.TimeField(blank=True, null=True)
    break_minutes = models.PositiveSmallIntegerField(blank=True, null=True)
    paid_hours = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    attendance_note = models.CharField(max_length=500, blank=True)
    change_request = models.CharField(max_length=500, blank=True)
    replacement_for = models.OneToOneField(
        'self', on_delete=models.PROTECT, related_name='replacement', blank=True, null=True)

    @staticmethod
    def shift_minutes(start, end):
        day = datetime.min.date()
        elapsed = datetime.combine(day, end) - datetime.combine(day, start)
        if elapsed < timedelta(0):
            elapsed += timedelta(days=1)
        return Decimal(str(elapsed.total_seconds())) / 60

    @property
    def gross_hours(self):
        if self.actual_start is not None and self.actual_end is not None:
            return (self.shift_minutes(self.actual_start, self.actual_end) / 60).quantize(Decimal('0.01'))


class StaffingEvent(models.Model):
    position = models.ForeignKey(StaffingPosition, on_delete=models.PROTECT, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    detail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
