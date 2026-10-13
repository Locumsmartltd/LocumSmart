"""Server-side earnings and expense calculations for a locum's approved jobs."""
import json
from datetime import date
from decimal import Decimal, InvalidOperation

TWO_PLACES = Decimal('0.01')


def job_day_count(job):
    """Number of days worked on a job, or None when the dates cannot be trusted."""
    if job.discrete_dates:
        try:
            dates = json.loads(job.discrete_dates)
        except (TypeError, ValueError):
            return None
        if not isinstance(dates, list) or not dates:
            return None
        return len(set(dates))

    if not job.start_date or not job.end_date or job.end_date < job.start_date:
        return None
    return (job.end_date - job.start_date).days + 1


def job_hours_per_day(job):
    """Hours per day as a Decimal, or None when the free-text field is not a usable number."""
    try:
        hours = Decimal(str(job.times_required).strip())
    except (InvalidOperation, ValueError):
        return None
    if not hours.is_finite() or hours <= 0 or hours > 24:
        return None
    return hours


def job_gross(job):
    """Gross earnings for a job: hourly rate x hours per day x days.

    Returns (amount, reason). amount is None when it cannot be calculated
    reliably, and reason then says why.
    """
    hours = job_hours_per_day(job)
    if hours is None:
        return None, f'Hours per day "{job.times_required}" is not a number between 0 and 24'
    days = job_day_count(job)
    if days is None:
        return None, 'The job dates are missing or invalid'
    if job.locum_rate is None or job.locum_rate <= 0:
        return None, 'The hourly rate is missing'
    return (job.locum_rate * hours * days).quantize(TWO_PLACES), ''


def parse_date(value):
    """Parse a YYYY-MM-DD string from a form or query string; None if blank or invalid."""
    try:
        return date.fromisoformat((value or '').strip())
    except ValueError:
        return None


def parse_amount(value):
    """Parse a positive money amount with at most two decimal places; None if invalid."""
    try:
        amount = Decimal((value or '').strip())
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite() or amount <= 0 or amount > Decimal('99999.99'):
        return None
    if amount != amount.quantize(TWO_PLACES):
        return None
    return amount


def in_range(day, date_from, date_to):
    if date_from and day < date_from:
        return False
    if date_to and day > date_to:
        return False
    return True


def build_ledger(jobs, expenses, date_from=None, date_to=None):
    """Per-job rows and an overall summary for the given date range.

    Earnings are counted by the job's start date and expenses by their own
    date. Each job row always nets off all of that job's expenses.
    """
    expenses_by_job = {}
    for expense in expenses:
        expenses_by_job.setdefault(expense.job_id, []).append(expense)

    rows = []
    total_earnings = Decimal('0.00')
    unavailable = []
    for job in jobs:
        if not in_range(job.start_date, date_from, date_to):
            continue
        gross, reason = job_gross(job)
        job_expenses = sum((e.amount for e in expenses_by_job.get(job.id, [])), Decimal('0.00'))
        if gross is None:
            unavailable.append(job)
        else:
            total_earnings += gross
        rows.append({
            'job': job,
            'days': job_day_count(job),
            'gross': gross,
            'gross_reason': reason,
            'expenses': job_expenses,
            'net': None if gross is None else gross - job_expenses,
        })

    expenses_in_range = [e for e in expenses if in_range(e.expense_date, date_from, date_to)]
    total_expenses = sum((e.amount for e in expenses_in_range), Decimal('0.00'))

    return {
        'rows': rows,
        'expenses': expenses_in_range,
        'total_earnings': total_earnings,
        'total_expenses': total_expenses,
        'net_profit': total_earnings - total_expenses,
        'unavailable_jobs': unavailable,
    }
