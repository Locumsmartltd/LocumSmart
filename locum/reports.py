"""Income and Expenditure Report for a locum, as CSV or PDF.

All figures are calculated here on the server from the locum's own records.
"""
import csv
from decimal import Decimal
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import ledger
from .models import AppliedJob, LocumInvoice, ShiftExpense

DISCLAIMER = ('This report summarises records held in LocumSmart. It is not tax advice '
              'and has not been checked against your bank records. Confirm all figures '
              'with your own records or an accountant before using them in a tax return.')

NOTES = [
    'Booked income is hourly rate x hours per day x days, as agreed when the job was booked. '
    'It is not verified income.',
    'Invoiced and paid amounts come from invoices you generated in LocumSmart and marked as paid. '
    'A blank means no invoice is recorded for that job, not that the amount is zero.',
    'Income is listed by job start date. Expenses are listed by expense date.',
]


def approved_jobs(locum):
    """The locum's approved jobs, newest first."""
    applied_jobs = AppliedJob.objects.filter(
        locum_id=locum.id, approved=True).select_related('job', 'job__employer')
    jobs = {applied_job.job.id: applied_job.job for applied_job in applied_jobs}
    return sorted(jobs.values(), key=lambda job: job.start_date, reverse=True)


def build_report(locum, date_from=None, date_to=None):
    jobs = approved_jobs(locum)
    expenses = list(ShiftExpense.objects.filter(locum=locum).select_related('job'))
    data = ledger.build_ledger(jobs, expenses, date_from, date_to)

    invoices_by_job = {}
    for invoice in LocumInvoice.objects.filter(locum=locum):
        invoices_by_job.setdefault(invoice.job_id, []).append(invoice)

    income_rows = []
    invoiced_total = paid_total = None
    invoiced_jobs = 0
    for row in sorted(data['rows'], key=lambda row: row['job'].start_date):
        job = row['job']
        invoices = invoices_by_job.get(job.id, [])
        # No invoice on record means the amounts are unknown, not zero
        invoiced = paid = None
        if invoices:
            invoiced = sum((i.total_amount for i in invoices), Decimal('0.00'))
            paid = sum((i.total_amount for i in invoices if i.status == LocumInvoice.STATUS_PAID),
                       Decimal('0.00'))
            invoiced_total = (invoiced_total or Decimal('0.00')) + invoiced
            paid_total = (paid_total or Decimal('0.00')) + paid
            invoiced_jobs += 1
        income_rows.append({
            'job': job,
            'days': row['days'],
            'booked': row['gross'],
            'booked_reason': row['gross_reason'],
            'invoiced': invoiced,
            'paid': paid,
            'invoice_count': len(invoices),
        })

    expense_rows = sorted(data['expenses'], key=lambda expense: (expense.expense_date, expense.id))
    by_category = []
    for value, label in ShiftExpense.CATEGORY_CHOICES:
        amounts = [expense.amount for expense in expense_rows if expense.category == value]
        if amounts:
            by_category.append((label, sum(amounts, Decimal('0.00'))))

    return {
        'locum_name': f'{locum.first_name} {locum.last_name}'.strip() or locum.email,
        'locum_email': locum.email,
        'date_from': date_from,
        'date_to': date_to,
        'period': period_label(date_from, date_to),
        'generated': timezone.localtime(),
        'income_rows': income_rows,
        'expense_rows': expense_rows,
        'expenses_by_category': by_category,
        'booked_total': data['total_earnings'],
        'unavailable_count': len(data['unavailable_jobs']),
        'invoiced_total': invoiced_total,
        'paid_total': paid_total,
        'invoiced_jobs': invoiced_jobs,
        'job_count': len(income_rows),
        'expenses_total': data['total_expenses'],
        'net_booked': data['net_profit'],
    }


def period_label(date_from, date_to):
    if date_from and date_to:
        return f'{date_from:%d %b %Y} to {date_to:%d %b %Y}'
    if date_from:
        return f'From {date_from:%d %b %Y}'
    if date_to:
        return f'Up to {date_to:%d %b %Y}'
    return 'All dates'


def report_filename(report, extension):
    start = report['date_from'].isoformat() if report['date_from'] else 'start'
    end = report['date_to'].isoformat() if report['date_to'] else 'latest'
    return f'locumsmart-income-expenditure_{start}_to_{end}.{extension}'


def calculation(row):
    job = row['job']
    days = row['days'] if row['days'] is not None else '?'
    return f'{job.locum_rate} x {job.times_required} x {days}'


def booked_note(report):
    count = report['unavailable_count']
    if not count:
        return ''
    return (f'Excludes {count} job{"" if count == 1 else "s"} whose booked amount '
            'could not be calculated')


def invoiced_note(report):
    return f'{report["invoiced_jobs"]} of {report["job_count"]} jobs have an invoice on record'


# --- CSV ---------------------------------------------------------------

def csv_text(value):
    """Stop spreadsheet apps treating user-entered text as a formula."""
    text = '' if value is None else str(value)
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text


def csv_money(amount):
    return '' if amount is None else f'{amount:.2f}'


def render_csv(report):
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['LocumSmart Income and Expenditure Report'])
    writer.writerow(['Locum', csv_text(report['locum_name'])])
    writer.writerow(['Period', report['period']])
    writer.writerow(['Generated', f'{report["generated"]:%d %b %Y %H:%M}'])
    writer.writerow([])

    writer.writerow(['Section', 'Date', 'End Date', 'Employer', 'Category', 'Description',
                     'Booked (GBP)', 'Invoiced (GBP)', 'Paid (GBP)', 'Expense (GBP)', 'Note'])
    for row in report['income_rows']:
        job = row['job']
        writer.writerow([
            'Income', job.start_date.isoformat(), job.end_date.isoformat(),
            csv_text(job.pharmacy_name), '', csv_text(calculation(row)),
            csv_money(row['booked']), csv_money(row['invoiced']), csv_money(row['paid']), '',
            csv_text('; '.join(filter(None, [
                f'Booked amount unavailable: {row["booked_reason"]}' if row['booked'] is None else '',
                'No invoice on record' if row['invoiced'] is None else '',
            ]))),
        ])
    for expense in report['expense_rows']:
        writer.writerow([
            'Expense', expense.expense_date.isoformat(), '', csv_text(expense.job.pharmacy_name),
            expense.get_category_display(), csv_text(expense.note), '', '', '',
            csv_money(expense.amount), '',
        ])
    writer.writerow([])

    writer.writerow(['Summary', 'Amount (GBP)', 'Note'])
    writer.writerow(['Booked income (not verified)', csv_money(report['booked_total']), booked_note(report)])
    writer.writerow(['Invoiced', csv_money(report['invoiced_total']), invoiced_note(report)])
    writer.writerow(['Paid', csv_money(report['paid_total']), invoiced_note(report)])
    for label, amount in report['expenses_by_category']:
        writer.writerow([f'Expenses: {label}', csv_money(amount), ''])
    writer.writerow(['Total expenses', csv_money(report['expenses_total']), ''])
    writer.writerow(['Net (booked income less expenses)', csv_money(report['net_booked']),
                     'Based on booked income, not verified income'])
    writer.writerow([])

    for note in NOTES:
        writer.writerow([note])
    writer.writerow([DISCLAIMER])
    return out.getvalue()


# --- PDF ---------------------------------------------------------------

TEAL = colors.HexColor('#1BA39C')
SOFT = colors.HexColor('#F7FAFB')
BORDER = colors.HexColor('#E4EAEE')
GREY = colors.HexColor('#5A6472')


def pdf_money(amount, missing='Not recorded'):
    if amount is None:
        return missing
    return f'-£{-amount:,.2f}' if amount < 0 else f'£{amount:,.2f}'


def render_pdf(report):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title='Income and Expenditure Report', author='LocumSmart')
    base = getSampleStyleSheet()['Normal']
    title = ParagraphStyle('Title', parent=base, fontName='Helvetica-Bold', fontSize=18, leading=22)
    heading = ParagraphStyle('Heading', parent=base, fontName='Helvetica-Bold', fontSize=12,
                             leading=16, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle('Body', parent=base, fontSize=9, leading=12)
    small = ParagraphStyle('Small', parent=base, fontSize=8, leading=11, textColor=GREY)
    cell = ParagraphStyle('Cell', parent=base, fontSize=8.5, leading=11)

    def text(value):
        return Paragraph(escape('' if value is None else str(value)), cell)

    def table(rows, widths, numeric_from, total_row=False):
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), SOFT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TEXTCOLOR', (0, 0), (-1, 0), GREY),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (numeric_from, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        if total_row:
            style += [('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                      ('LINEABOVE', (0, -1), (-1, -1), 1, TEAL)]
        flowable = Table(rows, colWidths=widths, repeatRows=1)
        flowable.setStyle(TableStyle(style))
        return flowable

    width = A4[0] - 32 * mm
    story = [
        Paragraph('Income and Expenditure Report', title),
        Spacer(1, 4),
        Paragraph(f'<b>Locum:</b> {escape(report["locum_name"])} ({escape(report["locum_email"])})', body),
        Paragraph(f'<b>Period:</b> {escape(report["period"])}', body),
        Paragraph(f'<b>Generated:</b> {report["generated"]:%d %b %Y %H:%M}', body),
        Spacer(1, 6),
        Paragraph(escape(DISCLAIMER), small),
    ]

    # Summary
    story.append(Paragraph('Summary', heading))
    summary = [['', 'Amount', 'Note'],
               ['Booked income (not verified)', pdf_money(report['booked_total']), text(booked_note(report))],
               ['Invoiced', pdf_money(report['invoiced_total']), text(invoiced_note(report))],
               ['Paid', pdf_money(report['paid_total']), text(invoiced_note(report))],
               ['Total expenses', pdf_money(report['expenses_total']), ''],
               ['Net (booked income less expenses)', pdf_money(report['net_booked']),
                text('Based on booked income, not verified income')]]
    summary_table = Table(summary, colWidths=[width * 0.36, width * 0.18, width * 0.46])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SOFT),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), GREY),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, TEAL),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)

    # Income
    story.append(Paragraph('Income by job', heading))
    if report['income_rows']:
        rows = [['Dates', 'Employer', 'Rate x hours x days', 'Booked', 'Invoiced', 'Paid']]
        for row in report['income_rows']:
            job = row['job']
            dates = f'{job.start_date:%d %b %Y}'
            if job.end_date != job.start_date:
                dates += f' – {job.end_date:%d %b %Y}'
            rows.append([text(dates), text(job.pharmacy_name), text(calculation(row)),
                         pdf_money(row['booked'], 'Unavailable'),
                         pdf_money(row['invoiced']), pdf_money(row['paid'])])
        rows.append(['Total', '', '', pdf_money(report['booked_total']),
                     pdf_money(report['invoiced_total']), pdf_money(report['paid_total'])])
        story.append(table(rows, [width * f for f in (0.20, 0.24, 0.17, 0.13, 0.13, 0.13)], 3, True))
    else:
        story.append(Paragraph('No approved jobs start in this period.', body))

    # Expenditure
    story.append(Paragraph('Expenditure by type', heading))
    if report['expenses_by_category']:
        rows = [['Type', 'Amount']]
        rows += [[label, pdf_money(amount)] for label, amount in report['expenses_by_category']]
        rows.append(['Total expenses', pdf_money(report['expenses_total'])])
        story.append(table(rows, [width * 0.5, width * 0.2], 1, True))

        story.append(Paragraph('Expenditure detail', heading))
        rows = [['Date', 'Job', 'Type', 'Note', 'Amount']]
        for expense in report['expense_rows']:
            rows.append([text(f'{expense.expense_date:%d %b %Y}'), text(expense.job.pharmacy_name),
                         text(expense.get_category_display()), text(expense.note),
                         pdf_money(expense.amount)])
        rows.append(['Total', '', '', '', pdf_money(report['expenses_total'])])
        story.append(table(rows, [width * f for f in (0.15, 0.25, 0.13, 0.33, 0.14)], 4, True))
    else:
        story.append(Paragraph('No expenses recorded in this period.', body))

    story.append(Paragraph('Notes', heading))
    for note in NOTES:
        story.append(Paragraph(escape(note), small))
        story.append(Spacer(1, 3))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f'<b>{escape(DISCLAIMER)}</b>', small))

    doc.build(story)
    return buffer.getvalue()
