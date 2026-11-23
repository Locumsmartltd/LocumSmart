from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from appAdmin.models import Admin, Employer
from locum.models import AppliedJob, Job, Locum


class PublicJobListingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employer = Employer.objects.create(
            email='jobs@example.com', first_name='Job', last_name='Owner',
            pharmacy_name='Visible Pharmacy', phone_number='07000000000',
            post_code='B1 1AA', city='Birmingham')
        cls.admin = Admin.objects.create(
            email='admin@example.com', first_name='Admin', last_name='User')

    def create_job(self, pharmacy_name, **overrides):
        values = {
            'pharmacy_name': pharmacy_name, 'company_name': pharmacy_name,
            'name': 'Job Owner', 'email': self.employer.email,
            'telephone': self.employer.phone_number, 'county': 'Birmingham',
            'post_code': 'B1 1AA', 'locum_rate': Decimal('30.00'),
            'expenses_offered': Decimal('0.00'),
            'start_date': date(2027, 1, 10), 'end_date': date(2027, 1, 10),
            'times_required': '8', 'any_other_information': '',
            'pharmacist_required': True, 'employer': self.employer,
        }
        values.update(overrides)
        return Job.objects.create(**values)

    def test_count_and_cards_use_the_same_public_queryset(self):
        visible = self.create_job('Visible Job', approved=True)
        self.create_job('Pending Job', approved=False)
        self.create_job('Rejected Job', approved=True, rejected=True)
        self.create_job('Filled Job', approved=True, applied_status=True)

        response = self.client.get(reverse('locumjobs'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['jobs']), [visible])
        self.assertContains(
            response, '<span class="results-count">1</span> live opportunity', html=True)
        self.assertContains(response, 'Visible Job')
        self.assertNotContains(response, 'Pending Job')
        self.assertNotContains(response, 'Rejected Job')
        self.assertNotContains(response, 'Filled Job')

    def test_job_card_explains_shift_count_and_total_hours(self):
        self.create_job(
            'Multi-day Job', approved=True,
            start_date=date(2027, 1, 10), end_date=date(2027, 1, 13),
            times_required='6')

        response = self.client.get(reverse('locumjobs'))

        self.assertContains(response, 'Multi-day job')
        self.assertContains(response, '4 shifts · 24 total hours · 6 hours/day')

    def test_selected_dates_determine_shift_count(self):
        self.create_job(
            'Selected Dates Job', approved=True,
            start_date=date(2027, 1, 10), end_date=date(2027, 1, 13),
            times_required='6',
            discrete_dates='["2027-01-10", "2027-01-11", "2027-01-13"]')

        response = self.client.get(reverse('locumjobs'))

        self.assertContains(response, 'Selected dates')
        self.assertContains(response, '3 shifts · 18 total hours · 6 hours/day')

    def test_empty_public_queryset_has_an_empty_state(self):
        self.create_job('Pending Job', approved=False)
        response = self.client.get(reverse('locumjobs'))
        self.assertContains(response, 'No live jobs match your search')

    def test_legacy_get_delete_parameter_no_longer_deletes_jobs(self):
        job = self.create_job('Safe Job', approved=True)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('check_login', args=[job.id]) + '?action=delete')
        self.assertRedirects(response, reverse('job_details', args=[job.id]))
        self.assertTrue(Job.objects.filter(pk=job.id).exists())

    @patch('structure.views.send_branded_email')
    def test_job_application_shows_success_toast_and_prevents_duplicates(self, send_email):
        job = self.create_job('Application Job', approved=True)
        locum = Locum.objects.create(
            email='candidate@example.com', first_name='Casey', last_name='Candidate',
            date_of_birth=date(1990, 1, 1), user_type='Pharmacist')
        self.client.force_login(locum)

        response = self.client.post(
            reverse('job_details', args=[job.id]), {'additional_info': 'Available.'},
            follow=True)
        self.assertContains(response, 'Your application for Application Job was submitted successfully.')
        self.assertEqual(AppliedJob.objects.filter(job=job, locum=locum).count(), 1)

        response = self.client.post(reverse('job_details', args=[job.id]), follow=True)
        self.assertContains(response, 'You have already applied for this job.')
        self.assertEqual(AppliedJob.objects.filter(job=job, locum=locum).count(), 1)
