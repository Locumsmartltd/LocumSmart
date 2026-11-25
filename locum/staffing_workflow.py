from django.conf import settings
from django.core.exceptions import ValidationError

from appAdmin.models import Employer
from .ledger import job_shift_dates
from .models import AppliedJob
from .staffing_models import StaffingEvent, StaffingPosition, StaffingRequest


ROLE_FIELDS = {
    StaffingRequest.Role.DISPENSER: 'dispenser_required',
    StaffingRequest.Role.ACD: 'dispenser_required',
    StaffingRequest.Role.ACT: 'technician_required',
    StaffingRequest.Role.PHARMACIST: 'pharmacist_required',
    StaffingRequest.Role.TECHNICIAN: 'technician_required',
    StaffingRequest.Role.NURSE: 'nurse_required',
    StaffingRequest.Role.ANP_NURSE: 'anp_nurse_required',
    StaffingRequest.Role.GP: 'gp_required',
    StaffingRequest.Role.OPTOMETRIST: 'optometrist_required',
    StaffingRequest.Role.DISPENSING_OPTICIAN: 'do_required',
}


def pilot_employers():
    demo_email = getattr(settings, 'STAFFING_PILOT_EMPLOYER_EMAIL', None)
    if demo_email:
        return Employer.objects.filter(email=demo_email)
    return Employer.objects.filter(pk=424, pharmacy_name__iexact='Montu Pharmacy')


def eligible_applications(position):
    shift = position.request
    role_field = ROLE_FIELDS.get(shift.role)
    if role_field is None:
        return AppliedJob.objects.none()
    return AppliedJob.objects.filter(
        rejected=False, approved=False, locum__is_accepted=True, locum__is_active=True,
        job__employer_id=shift.branch.employer_id, job__start_date=shift.shift_date,
        job__end_date=shift.shift_date, job__approved=True, job__rejected=False,
        job__applied_status=False, job__locum__isnull=True,
        **{f'job__{role_field}': True},
    )


def record_event(position, user, action, detail=''):
    StaffingEvent.objects.create(position=position, actor=user, action=action, detail=detail)


def reserved_job_position(job):
    # Call while holding the job row lock. Terminal positions keep their application link.
    return StaffingPosition.objects.select_for_update().filter(
        application__job_id=job.pk, request__branch__employer__in=pilot_employers(),
    ).exclude(status=StaffingPosition.Status.CANCELLED).first()


def check_application_booking(job, application):
    position = reserved_job_position(job)
    if position is None:
        return None
    if position.application_id != application.pk or position.status != StaffingPosition.Status.APPROVED:
        raise ValidationError('This job is reserved in Portal Handling. The manager must approve the linked proposal first.')
    if not eligible_applications(position).filter(pk=application.pk).exists():
        raise ValidationError('This application no longer matches the staffing position. Review it in Portal Handling.')
    if job_shift_dates(job) != [position.request.shift_date] or (
            position.client_rate is not None and job.client_billing_rate != position.client_rate):
        raise ValidationError('The application dates or client rate changed. Withdraw and reissue the proposal.')
    return position
