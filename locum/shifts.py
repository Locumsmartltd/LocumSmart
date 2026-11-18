"""Shared shift-completion workflow helpers."""
from . import ledger
from .models import AppliedJob, ShiftCompletion


def refresh_completion_status(job, locum):
    scheduled_dates = set(ledger.job_shift_dates(job))
    reports = list(ShiftCompletion.objects.filter(job=job, locum=locum))
    approved_dates = {report.shift_date for report in reports
                      if report.status == ShiftCompletion.STATUS_APPROVED}
    completed = bool(scheduled_dates) and approved_dates == scheduled_dates
    AppliedJob.objects.filter(job=job, locum=locum, approved=True).update(completed=completed)

    if completed:
        job.status = 'Completed'
    elif any(report.status == ShiftCompletion.STATUS_PENDING for report in reports):
        job.status = 'Completion review'
    elif any(report.status == ShiftCompletion.STATUS_DECLINED for report in reports):
        job.status = 'Completion declined'
    else:
        return completed
    job.save(update_fields=['status'])
    return completed


def job_review_summary(job):
    reports = list(job.shift_completions.all())
    return {
        'total': len(ledger.job_shift_dates(job)),
        'reported': len(reports),
        'pending': sum(report.status == ShiftCompletion.STATUS_PENDING for report in reports),
        'approved': sum(report.status == ShiftCompletion.STATUS_APPROVED for report in reports),
        'declined': sum(report.status == ShiftCompletion.STATUS_DECLINED for report in reports),
    }
