from io import BytesIO
from django.templatetags.static import static
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from datetime import timedelta

def generate_gorgemead_invoice_pdf(jobs, created_date, invoice_number, month, total_amount):
    # Build the absolute or relative URL for the logo image
    BASE_URL = getattr(settings, 'BASE_URL', 'https://locumsmart.co.uk')
    logo_url = BASE_URL + static('images/logo.JPG')

    # Create PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Draw the logo
    p.drawImage(logo_url, 50, height - 100, width=100, preserveAspectRatio=True, mask='auto')

    # Draw the title and header
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width // 2, height - 100, "Invoice")

    # Invoice details table
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 150, "Invoice Details:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 170, f"Date: {created_date}")
    p.drawString(50, height - 190, f"Invoice No: {invoice_number}")
    p.drawString(50, height - 210, f"Month Invoice: {month}")

    # Draw company details and locum details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 240, "Company Details:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 260, f"Company Name: {jobs[0].pharmacy_name}")
    p.drawString(50, height - 280, f"Manager: {jobs[0].employer.manager_name}")
    p.drawString(50, height - 300, f"Street Address: {jobs[0].employer.street_address}")
    p.drawString(50, height - 320, f"City & Postal Code: {jobs[0].employer.city}, {jobs[0].employer.post_code}")
    p.drawString(50, height - 340, f"Email Address: {jobs[0].employer.email}")

    # Locum details table (Dynamic content)
    table_data = [
        ["Locum Name", "Role", "Branch#", "Days", "Booking Date", "Total Price"]
    ]

    for job in jobs:
        table_data.append([
            f"{job.locum.first_name} {job.locum.last_name}",
            job.locum.user_type,
            job.branch_no,
            job.days,
            job.date_of_booking_email.strftime("%d/%m/%Y") if job.date_of_booking_email else "",
            f"£{job.total_price}"
        ])

    table = Table(table_data, colWidths=[120, 60, 60, 60, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Adjust table position and draw it
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 450)

    # Totals Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(width - 200, height - 520, "Subtotal:")
    p.drawString(width - 120, height - 520, f"£{total_amount}")

    p.drawString(width - 200, height - 540, "VAT:")
    p.drawString(width - 120, height - 540, "£0.00")

    p.drawString(width - 200, height - 560, "Total:")
    p.drawString(width - 120, height - 560, f"£{total_amount}")

    # Payment Details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 600, "Make Payments to:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 620, "Acc Name: LocumSmart Ltd")
    p.drawString(50, height - 640, "Bank: Clear Bank")
    p.drawString(50, height - 660, "Acct No.: 20432032")
    p.drawString(50, height - 680, "Sort Code: 04-06-05")

    # Customer Message
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 720, "* Customer Message")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 740, "For details of working days & Locum rate, Check the booking confirmation email sent from info@locum-smart.co.uk")

    # Close the PDF
    p.showPage()
    p.save()

    # Return the PDF as an HTTP response
    buffer.seek(0)
    return buffer

def generate_fairgreen_invoice_pdf(jobs, created_date, invoice_number, month, total_amount):
    
    # Build the absolute or relative URL for the logo image
    BASE_URL = getattr(settings, 'BASE_URL', 'https://locumsmart.co.uk')
    logo_url = BASE_URL + static('images/logo.JPG')

    # Create PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Draw the logo
    p.drawImage(logo_url, 50, height - 100, width=100, preserveAspectRatio=True, mask='auto')

    # Draw the title and header
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width // 2, height - 100, "Invoice")

    # Invoice details table
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 150, "Invoice Details:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 170, f"Date: {created_date}")
    p.drawString(50, height - 190, f"Invoice No: {invoice_number}")
    p.drawString(50, height - 210, f"Month Invoice: {month}")

    # Draw company details and locum details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 240, "Company Details:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 260, f"Company Name: {jobs[0].pharmacy_name}")
    p.drawString(50, height - 280, f"Manager: {jobs[0].employer.manager_name}")
    p.drawString(50, height - 300, f"Street Address: {jobs[0].employer.street_address}")
    p.drawString(50, height - 320, f"City & Postal Code: {jobs[0].employer.city}, {jobs[0].employer.post_code}")
    p.drawString(50, height - 340, f"Email Address: {jobs[0].employer.email}")

    # Define the table header with the new columns
    table_data = [
        ["Locum Name", "Role", "Pharmacy", "Days", "Booking Date", "Locum Rate", "Hours/Day", "Amount"]
    ]

    # Add job data to the table
    for job in jobs:
        table_data.append([
            f"{job.locum.first_name} {job.locum.last_name}",
            job.locum.user_type,
            job.pharmacy_name,
            job.days,
            job.date_of_booking_email.strftime("%d/%m/%Y") if job.date_of_booking_email else "",
            f"£{job.locum_rate}",
            job.times_required,
            f"£{job.total_price}"
        ])

    # Decrease the margins to give more width for the table
    left_margin = 15  # Reduced left margin
    right_margin = 15  # Reduced right margin
    total_width_available = width - left_margin - right_margin

    # Set proportional column widths to fit the new page width
    col_widths = [
        total_width_available * 0.20,  # Locum Name
        total_width_available * 0.10,  # Role
        total_width_available * 0.20,  # Pharmacy
        total_width_available * 0.05,  # Days
        total_width_available * 0.15,  # Booking Date
        total_width_available * 0.10,  # Locum Rate
        total_width_available * 0.10,  # Hours/Day
        total_width_available * 0.10   # Amount
    ]

    # Create the table with the updated column widths
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Draw the table with reduced margins
    table.wrapOn(p, width, height)
    table.drawOn(p, left_margin, height - 450)  # Adjust starting position

    # Totals Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(width - 200, height - 520, "Subtotal:")
    p.drawString(width - 120, height - 520, f"£{total_amount}")

    p.drawString(width - 200, height - 540, "VAT:")
    p.drawString(width - 120, height - 540, "£0.00")

    p.drawString(width - 200, height - 560, "Total:")
    p.drawString(width - 120, height - 560, f"£{total_amount}")

    # Payment Details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 600, "Make Payments to:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 620, "Acc Name: LocumSmart Ltd")
    p.drawString(50, height - 640, "Bank: Clear Bank")
    p.drawString(50, height - 660, "Acct No.: 20432032")
    p.drawString(50, height - 680, "Sort Code: 04-06-05")

    # Customer Message
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 720, "* Customer Message")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 740, "For details of working days & Locum rate, Check the booking confirmation email sent from info@locum-smart.co.uk")

    # Close the PDF
    p.showPage()
    p.save()

    # Return the PDF as an HTTP response
    buffer.seek(0)
    return buffer


def generate_tesco_invoice_pdf(jobs, created_date, invoice_number, month, total_amount):
    pdf_file = BytesIO()
    doc = SimpleDocTemplate(pdf_file, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(name='Title', fontSize=12, alignment=TA_CENTER)
    style_heading = ParagraphStyle(name='Heading', fontSize=10, alignment=TA_CENTER)

    elements = []

    # Title Section
    elements.append(Paragraph("Pharmacy Invoice", style_title))
    elements.append(Spacer(1, 10))

    # First part of the invoice table (first half of the columns)
    job_data_part1 = [
        ['Sl No.', 'Date Worked', 'Ref/Inv No', 'GPHC Number', 'Name of the Locum']
    ]

    for idx, job in enumerate(jobs):
        if job.discrete_dates:
            days_list = job.discrete_dates.strip('][').split(', ')
        else:
            days_list = []
            current_date = job.start_date
            while current_date <= job.end_date:
                days_list.append(current_date.strftime('%d/%m/%Y'))
                current_date += timedelta(days=1)

        # Append job data for each date in days_list
        for date in days_list:
            job_data_part1.append([
                idx + 1,
                date,
                invoice_number,
                job.locum.gphc_number,
                f"{job.locum.first_name} {job.locum.last_name}",
            ])

    job_table_part1 = Table(job_data_part1, colWidths=[10*mm, 30*mm, 35*mm, 30*mm, 45*mm])
    job_table_part1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.yellow),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(job_table_part1)
    elements.append(Spacer(1, 20))

    # Second part of the invoice table (second half of the columns)
    job_data_part2 = [
        ['Supplier Name', 'Store Number', 'Total Hours', 'Cost excluding VAT', 'VAT @ 20%', 'Gross Total']
    ]

    for idx, job in enumerate(jobs):
        if job.discrete_dates:
            days_list = job.discrete_dates.strip('][').split(', ')
        else:
            days_list = []
            current_date = job.start_date
            while current_date <= job.end_date:
                days_list.append(current_date.strftime('%d/%m/%Y'))
                current_date += timedelta(days=1)

        for date in days_list:
            job_data_part2.append([
                'Locumsmart Ltd.',
                '',  # Store Number placeholder
                job.times_required,
                f"£{float(job.locum_rate) * float(job.times_required):.2f}",
                ' ',  # VAT placeholder, assuming it might be calculated differently
                f"£{float(job.locum_rate) * float(job.times_required):.2f}",
            ])

    job_table_part2 = Table(job_data_part2, colWidths=[50*mm, 30*mm, 30*mm, 40*mm, 30*mm, 40*mm])
    job_table_part2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.yellow),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(job_table_part2)

    doc.build(elements)
    pdf_file.seek(0)

    return pdf_file


def generate_cohens_invoice_pdf(jobs, created_date, invoice_number, month, total_amount):

    # Build the absolute or relative URL for the logo image
    BASE_URL = getattr(settings, 'BASE_URL', 'https://locumsmart.co.uk')
    logo_url = BASE_URL + static('images/logo.JPG')

    # Create PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Draw the logo
    p.drawImage(logo_url, 50, height - 100, width=100, preserveAspectRatio=True, mask='auto')

    # Draw the title and header
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width // 2, height - 100, "Invoice")

    # Invoice details table
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 150, "Invoice Details:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 170, f"Date: {created_date}")
    p.drawString(50, height - 190, f"Invoice No: {invoice_number}")
    p.drawString(50, height - 210, f"Month Invoice: {month}")

    # Draw company details and locum details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 240, "Company Details:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 260, f"Company Name: {jobs[0].pharmacy_name}")
    p.drawString(50, height - 280, f"Manager: {jobs[0].employer.manager_name}")
    p.drawString(50, height - 300, f"Street Address: {jobs[0].employer.street_address}")
    p.drawString(50, height - 320, f"City & Postal Code: {jobs[0].employer.city}, {jobs[0].employer.post_code}")
    p.drawString(50, height - 340, f"Email Address: {jobs[0].employer.email}")

    # Define the table header with the new columns
    table_data = [
        ["Locum Name", "Role", "Branch#", "Days", "Booking Date", "Total Price", "Working Dates"]
    ]

    # Add job data to the table
    for job in jobs:
        table_data.append([
            f"{job.locum.first_name} {job.locum.last_name}",
            job.locum.user_type,
            job.branch_no,
            job.days,
            job.date_of_booking_email.strftime("%d/%m/%Y") if job.date_of_booking_email else "",
            f"£{job.total_price}",
            ''
        ])

    # Decrease the margins to give more width for the table
    left_margin = 15  # Reduced left margin
    right_margin = 15  # Reduced right margin
    total_width_available = width - left_margin - right_margin

    # Set proportional column widths to fit the new page width
    col_widths = [
        total_width_available * 0.20,  # Locum Name
        total_width_available * 0.10,  # Role
        total_width_available * 0.10,  # Branch#
        total_width_available * 0.05,  # Days
        total_width_available * 0.15,  # Booking Date
        total_width_available * 0.15,  # Amount
        total_width_available * 0.25   # Working Dates
    ]

    # Create the table with the updated column widths
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Draw the table with reduced margins
    table.wrapOn(p, width, height)
    table.drawOn(p, left_margin, height - 450)  # Adjust starting position

    # Totals Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(width - 200, height - 520, "Subtotal:")
    p.drawString(width - 120, height - 520, f"£{total_amount}")

    p.drawString(width - 200, height - 540, "VAT:")
    p.drawString(width - 120, height - 540, "£0.00")

    p.drawString(width - 200, height - 560, "Total:")
    p.drawString(width - 120, height - 560, f"£{total_amount}")

    # Payment Details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 600, "Make Payments to:")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 620, "Acc Name: LocumSmart Ltd")
    p.drawString(50, height - 640, "Bank: Clear Bank")
    p.drawString(50, height - 660, "Acct No.: 20432032")
    p.drawString(50, height - 680, "Sort Code: 04-06-05")

    # Customer Message
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 720, "* Customer Message")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 740, "For details of working days & Locum rate, Check the booking confirmation email sent from info@locum-smart.co.uk")

    # Close the PDF
    p.showPage()
    p.save()

    # Return the PDF as an HTTP response
    buffer.seek(0)
    return buffer

