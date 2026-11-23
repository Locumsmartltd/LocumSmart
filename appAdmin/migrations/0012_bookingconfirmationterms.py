from django.db import migrations, models


PHARMACY_TERMS = """Please note any cancellation within 72 hours prior to the booking may result in the pharmacy claiming loss of earnings if the shift is not covered. Cancellations made because a better offer was received elsewhere are not acceptable once a booking has been confirmed.

If you are offered further bookings directly by the pharmacy, you must inform a LocumSmart coordinator and must not book directly, in line with the terms agreed during registration.

Sundays and bank holidays are not included in the notice period. Notice hours are Monday to Friday, 9am to 5pm, and Saturday, 9am to 3pm. Cancellation notice must be provided by email.

While on the pharmacy premises, locums are expected to use their time responsibly and complete the duties normally expected of their role."""

PRIMARY_CARE_TERMS = """Please arrive 10 minutes before the scheduled start time.

Our normal invoice payment schedule is two to four weeks, depending on payment from the surgery or practice. Do not discuss hourly rates with practice staff. Further bookings offered directly by the surgery or practice must be reported to LocumSmart, and payment discussions must be made with LocumSmart only.

Locum doctors, physician associates and practice nurses must make their compliance documents available to the practice and LocumSmart on request, and must notify LocumSmart of any changes. LocumSmart carries out periodic compliance checks. The practice must confirm the accuracy of supplied information before an assignment begins.

Cancellation within 72 hours of a confirmed booking may result in the surgery claiming loss of earnings unless there is a verifiable emergency. Cancelling because a better offer was received elsewhere is considered unprofessional and may result in a complaint to the relevant registration body."""


class Migration(migrations.Migration):
    dependencies = [
        ('appAdmin', '0011_employer_candidate_invoice_details'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingConfirmationTerms',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pharmacy_candidate_terms', models.TextField(default=PHARMACY_TERMS)),
                ('primary_care_candidate_terms', models.TextField(default=PRIMARY_CARE_TERMS)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
