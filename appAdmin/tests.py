from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from appAdmin.models import Admin, Employer
from locum.models import Job, Locum


def make_job(employer, **overrides):
    values = {
        'pharmacy_name': employer.pharmacy_name,
        'company_name': employer.pharmacy_name,
        'name': employer.base_username(),
        'email': employer.email,
        'telephone': employer.phone_number,
        'county': employer.city,
        'post_code': employer.post_code,
        'locum_rate': Decimal('35.00'),
        'expenses_offered': Decimal('5.00'),
        'start_date': date(2026, 12, 1),
        'end_date': date(2026, 12, 2),
        'times_required': '8',
        'any_other_information': '',
        'pharmacist_required': True,
        'employer': employer,
    }
    values.update(overrides)
    return Job.objects.create(**values)


class AdminCalendarJobListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Admin.objects.create(
            email='calendar-admin@example.com', first_name='Admin', last_name='User')
        cls.employer = Employer.objects.create(
            email='calendar-owner@example.com', first_name='Ava', last_name='Owner',
            pharmacy_name='Calendar Pharmacy', phone_number='07123456789',
            post_code='M1 1AA', city='Manchester')
        cls.locum = Locum.objects.create(
            email='calendar-locum@example.com', first_name='Sam', last_name='Locum',
            date_of_birth=date(1990, 1, 1), user_type='Pharmacist')
        cls.job = make_job(
            cls.employer, locum=cls.locum, start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 3), times_required='6',
            status='Booked', locum_payment_status='Pending', booked_by='Admin User',
            any_other_information='Bring the pharmacy smart card.')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_job_list_is_compact_and_exposes_modal_editing(self):
        response = self.client.get(reverse('calander'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['job_count'], 1)
        self.assertEqual(response.context['scheduled_shift_count'], 3)
        self.assertEqual(response.context['pending_payment_count'], 1)
        self.assertContains(response, '<strong>3</strong>', html=True)
        self.assertContains(response, 'shifts across these jobs')
        self.assertContains(response, 'class="btn btn-secondary btn-sm job-edit-trigger"')
        self.assertContains(response, 'id="job-edit-dialog"')
        self.assertContains(response, 'Payment and invoicing')
        self.assertNotContains(response, 'form="job-form-')

    def test_modal_update_can_save_and_clear_operational_fields(self):
        response = self.client.post(reverse('update_job', args=[self.job.id]), {
            'company_name': 'Updated Group',
            'booked_by': '',
            'status': 'Completed',
            'date_of_booking_email': '2026-12-01',
            'locum_payment_status': 'Paid',
            'date_of_invoice_email': '',
            'source': 'Direct',
            'source_commission_date': '2026-12-10',
            'search': 'Calendar',
            'sort_by': 'Latest',
        })

        self.assertRedirects(
            response, reverse('calander') + '?search=Calendar&sort_by=Latest')
        self.job.refresh_from_db()
        self.assertEqual(self.job.company_name, 'Updated Group')
        self.assertEqual(self.job.booked_by, '')
        self.assertEqual(self.job.status, 'Completed')
        self.assertEqual(self.job.locum_payment_status, 'Paid')
        self.assertEqual(self.job.date_of_booking_email, date(2026, 12, 1))
        self.assertIsNone(self.job.date_of_invoice_email)
        self.assertEqual(self.job.source, 'Direct')
        self.assertEqual(self.job.source_commission_date, date(2026, 12, 10))


class EmployerJobManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Admin.objects.create(
            email='admin@example.com', first_name='Admin', last_name='User')
        cls.employer = Employer.objects.create(
            email='owner@example.com', first_name='Ava', last_name='Owner',
            pharmacy_name='Green Pharmacy', manager_name='Maya Manager',
            phone_number='07123456789', post_code='M1 1AA', city='Manchester',
            street_address='10 High Street')
        cls.other_employer = Employer.objects.create(
            email='other@example.com', first_name='Other', last_name='Owner',
            pharmacy_name='Blue Pharmacy', phone_number='07999999999',
            post_code='L1 1AA', city='Liverpool')
        cls.job = make_job(cls.employer)
        cls.other_job = make_job(cls.other_employer)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_post_job_form_populates_and_locks_employer_information(self):
        response = self.client.get(reverse('post_job', args=[self.employer.id]))
        self.assertEqual(response.status_code, 200)
        for value in ('Green Pharmacy', 'owner@example.com', '07123456789',
                      'M1 1AA', 'Manchester', '10 High Street', 'Maya Manager'):
            self.assertContains(response, value)
        self.assertContains(response, 'readonly', count=9)

    def test_employer_jobs_page_is_scoped_to_selected_employer(self):
        response = self.client.get(reverse('employer_jobs', args=[self.employer.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Green Pharmacy')
        self.assertNotContains(response, 'Blue Pharmacy')
        self.assertEqual(list(response.context['jobs']), [self.job])

    def test_post_job_uses_selected_employer_not_submitted_company_fields(self):
        response = self.client.post(reverse('post_job', args=[self.employer.id]), {
            'company_name': 'Tampered Company', 'email': 'bad@example.com',
            'post_code': 'XX1 1XX', 'first_name': 'Wrong', 'last_name': 'Name',
            'telephone': '000', 'locum_rate': '39.50', 'expenses_offered': '0',
            'date_type': 'continuous', 'start_date': '2027-04-01',
            'end_date': '2027-04-02', 'times_required': '8',
            'any_other_information': 'New job', 'GP_required': '1',
        })
        self.assertRedirects(response, reverse('employer_jobs', args=[self.employer.id]))
        created = Job.objects.get(employer=self.employer, start_date=date(2027, 4, 1))
        self.assertEqual(created.company_name, self.employer.pharmacy_name)
        self.assertEqual(created.email, self.employer.email)
        self.assertEqual(created.post_code, self.employer.post_code)
        self.assertTrue(created.gp_required)

    def test_edit_updates_job_but_company_data_remains_authoritative(self):
        response = self.client.post(
            reverse('edit_employer_job', args=[self.employer.id, self.job.id]),
            {
                'company_name': 'Tampered Company', 'email': 'bad@example.com',
                'post_code': 'XX1', 'locum_rate': '42.50',
                'expenses_offered': '12', 'date_type': 'continuous',
                'start_date': '2027-01-05', 'end_date': '2027-01-06',
                'times_required': '7.5', 'any_other_information': 'Updated',
                'Optometrist_required': '1',
            })
        self.assertRedirects(response, reverse('employer_jobs', args=[self.employer.id]))
        self.job.refresh_from_db()
        self.assertEqual(self.job.company_name, self.employer.pharmacy_name)
        self.assertEqual(self.job.email, self.employer.email)
        self.assertEqual(self.job.post_code, self.employer.post_code)
        self.assertEqual(self.job.locum_rate, Decimal('42.50'))
        self.assertTrue(self.job.optometrist_required)
        self.assertFalse(self.job.pharmacist_required)

    def test_delete_is_post_only_and_scoped_to_employer(self):
        url = reverse('delete_employer_job', args=[self.employer.id, self.job.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        wrong_url = reverse('delete_employer_job', args=[self.other_employer.id, self.job.id])
        self.assertEqual(self.client.post(wrong_url).status_code, 404)
        self.assertTrue(Job.objects.filter(pk=self.job.id).exists())
        self.assertRedirects(self.client.post(url), reverse('employer_jobs', args=[self.employer.id]))
        self.assertFalse(Job.objects.filter(pk=self.job.id).exists())

    def test_employer_account_cannot_access_staff_job_management(self):
        self.client.force_login(self.employer)
        response = self.client.get(reverse('employer_jobs', args=[self.employer.id]))
        self.assertEqual(response.status_code, 403)
