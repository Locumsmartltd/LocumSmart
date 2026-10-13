import json
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from appAdmin.models import Admin, Employer
from locum import ledger
from locum.models import AppliedJob, Job, Locum, LocumInvoice, ShiftExpense


def make_locum(email):
    name = email.split('@')[0]
    return Locum.objects.create(
        email=email, first_name=name, last_name='Locum',
        date_of_birth=date(1990, 1, 1), user_type='Pharmacist')


def make_job(employer, locum, start, end, rate='30.00', hours='8', discrete_dates=None):
    job = Job.objects.create(
        pharmacy_name=employer.pharmacy_name, name='Manager', email=employer.email,
        telephone='07000000000', county='London', post_code='E1 1AA',
        locum_rate=Decimal(rate), expenses_offered=Decimal('10.00'),
        start_date=start, end_date=end, times_required=hours,
        any_other_information='', approved=True, locum=locum, employer=employer,
        discrete_dates=json.dumps(discrete_dates) if discrete_dates else None)
    AppliedJob.objects.create(locum=locum, job=job, approved=True)
    return job


class LedgerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employer = Employer.objects.create(
            email='pharmacy@example.com', first_name='Test', last_name='Employer',
            pharmacy_name='Test Pharmacy', phone_number='07000000000')
        cls.locum = make_locum('owner@example.com')
        cls.other = make_locum('other@example.com')
        # 3 days x 8 hours x £30 = £720
        cls.job = make_job(cls.employer, cls.locum, date(2026, 10, 10), date(2026, 10, 12))
        cls.other_job = make_job(cls.employer, cls.other, date(2026, 10, 10), date(2026, 10, 10))

    def setUp(self):
        self.client.force_login(self.locum)

    def ledger_url(self, locum=None, **params):
        url = reverse('locum_jobs', args=[(locum or self.locum).id])
        if params:
            url += '?' + '&'.join(f'{key}={value}' for key, value in params.items())
        return url

    def expense_data(self, **overrides):
        data = {'category': 'parking', 'amount': '12.50',
                'expense_date': '2026-10-10', 'note': 'Car park'}
        data.update(overrides)
        return data


class GrossCalculationTests(LedgerTestCase):
    def test_continuous_job_is_rate_times_hours_times_days(self):
        self.assertEqual(ledger.job_gross(self.job), (Decimal('720.00'), ''))

    def test_discrete_dates_count_only_the_listed_days(self):
        job = make_job(self.employer, self.locum, date(2026, 11, 1), date(2026, 11, 20),
                       rate='25.50', hours='7.5',
                       discrete_dates=['2026-11-01', '2026-11-20'])
        self.assertEqual(ledger.job_gross(job)[0], Decimal('382.50'))

    def test_non_numeric_hours_is_unavailable_not_guessed(self):
        for hours in ('9am-5pm', '', '8 hours', '0', '25', 'nan'):
            job = make_job(self.employer, self.locum, date(2026, 12, 1), date(2026, 12, 1), hours=hours)
            amount, reason = ledger.job_gross(job)
            self.assertIsNone(amount, hours)
            self.assertTrue(reason)

    def test_end_before_start_is_unavailable(self):
        job = make_job(self.employer, self.locum, date(2026, 12, 5), date(2026, 12, 1))
        self.assertIsNone(ledger.job_gross(job)[0])


class LedgerPageTests(LedgerTestCase):
    def test_row_shows_gross_expenses_and_net(self):
        ShiftExpense.objects.create(job=self.job, locum=self.locum, category='mileage',
                                    amount=Decimal('20.25'), expense_date=date(2026, 10, 10))
        ShiftExpense.objects.create(job=self.job, locum=self.locum, category='tolls',
                                    amount=Decimal('5.00'), expense_date=date(2026, 10, 11))
        response = self.client.get(self.ledger_url())
        self.assertEqual(response.status_code, 200)
        row = response.context['ledger']['rows'][0]
        self.assertEqual(row['gross'], Decimal('720.00'))
        self.assertEqual(row['expenses'], Decimal('25.25'))
        self.assertEqual(row['net'], Decimal('694.75'))
        self.assertContains(response, '£694.75')

    def test_unavailable_gross_is_flagged_and_left_out_of_totals(self):
        make_job(self.employer, self.locum, date(2026, 10, 20), date(2026, 10, 20), hours='9am-5pm')
        response = self.client.get(self.ledger_url())
        summary = response.context['ledger']
        self.assertEqual(summary['total_earnings'], Decimal('720.00'))
        self.assertEqual(len(summary['unavailable_jobs']), 1)
        self.assertContains(response, 'Unavailable')
        self.assertContains(response, 'could not be calculated')

    def test_summary_uses_job_start_date_and_expense_date(self):
        november_job = make_job(self.employer, self.locum, date(2026, 11, 2), date(2026, 11, 2))  # £240
        # Expense for the October job, but dated in November
        ShiftExpense.objects.create(job=self.job, locum=self.locum, category='parking',
                                    amount=Decimal('8.00'), expense_date=date(2026, 11, 3))
        ShiftExpense.objects.create(job=november_job, locum=self.locum, category='parking',
                                    amount=Decimal('4.00'), expense_date=date(2026, 10, 30))

        october = self.client.get(self.ledger_url(**{'from': '2026-10-01', 'to': '2026-10-31'})).context['ledger']
        self.assertEqual(october['total_earnings'], Decimal('720.00'))
        self.assertEqual(october['total_expenses'], Decimal('4.00'))
        self.assertEqual(october['net_profit'], Decimal('716.00'))

        november = self.client.get(self.ledger_url(**{'from': '2026-11-01', 'to': '2026-11-30'})).context['ledger']
        self.assertEqual(november['total_earnings'], Decimal('240.00'))
        self.assertEqual(november['total_expenses'], Decimal('8.00'))
        self.assertEqual(november['net_profit'], Decimal('232.00'))

        everything = self.client.get(self.ledger_url()).context['ledger']
        self.assertEqual(everything['total_earnings'], Decimal('960.00'))
        self.assertEqual(everything['total_expenses'], Decimal('12.00'))
        self.assertEqual(everything['net_profit'], Decimal('948.00'))

    def test_range_is_inclusive_and_open_ended(self):
        ShiftExpense.objects.create(job=self.job, locum=self.locum, category='parking',
                                    amount=Decimal('3.00'), expense_date=date(2026, 10, 10))
        on_the_day = self.client.get(self.ledger_url(**{'from': '2026-10-10', 'to': '2026-10-10'})).context['ledger']
        self.assertEqual(on_the_day['total_earnings'], Decimal('720.00'))
        self.assertEqual(on_the_day['total_expenses'], Decimal('3.00'))
        after = self.client.get(self.ledger_url(**{'from': '2026-10-11'})).context['ledger']
        self.assertEqual(after['total_earnings'], Decimal('0.00'))
        self.assertEqual(after['total_expenses'], Decimal('0.00'))

    def test_reversed_or_invalid_range_falls_back_to_all_dates(self):
        for params in ({'from': '2026-12-01', 'to': '2026-10-01'}, {'from': 'not-a-date'}):
            response = self.client.get(self.ledger_url(**params))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['ledger']['total_earnings'], Decimal('720.00'))

    def test_other_locums_data_is_never_included(self):
        ShiftExpense.objects.create(job=self.other_job, locum=self.other, category='parking',
                                    amount=Decimal('99.00'), expense_date=date(2026, 10, 10))
        summary = self.client.get(self.ledger_url()).context['ledger']
        self.assertEqual([row['job'].id for row in summary['rows']], [self.job.id])
        self.assertEqual(summary['total_expenses'], Decimal('0.00'))


class ExpenseCrudTests(LedgerTestCase):
    def test_add_expense(self):
        response = self.client.post(reverse('add_expense', args=[self.job.id]), self.expense_data())
        self.assertRedirects(response, self.ledger_url())
        expense = ShiftExpense.objects.get()
        self.assertEqual((expense.job, expense.locum, expense.category, expense.amount,
                          expense.expense_date, expense.note),
                         (self.job, self.locum, 'parking', Decimal('12.50'), date(2026, 10, 10), 'Car park'))

    def test_add_keeps_the_date_range_in_the_redirect(self):
        response = self.client.post(reverse('add_expense', args=[self.job.id]),
                                    self.expense_data(**{'from': '2026-10-01', 'to': '2026-10-31'}))
        self.assertRedirects(response, self.ledger_url(**{'from': '2026-10-01', 'to': '2026-10-31'}))

    def test_invalid_expenses_are_rejected(self):
        bad = [{'amount': '0'}, {'amount': '-5'}, {'amount': 'abc'}, {'amount': ''},
               {'amount': '1.999'}, {'amount': '1000000'}, {'category': 'bribes'},
               {'expense_date': ''}, {'expense_date': '10/10/2026'}, {'note': 'x' * 256}]
        for overrides in bad:
            response = self.client.post(reverse('add_expense', args=[self.job.id]),
                                        self.expense_data(**overrides))
            self.assertEqual(response.status_code, 302, overrides)
        self.assertEqual(ShiftExpense.objects.count(), 0)

    def test_edit_expense(self):
        expense = ShiftExpense.objects.create(job=self.job, locum=self.locum, category='parking',
                                              amount=Decimal('12.50'), expense_date=date(2026, 10, 10))
        self.client.post(reverse('edit_expense', args=[expense.id]),
                         self.expense_data(category='mileage', amount='30', expense_date='2026-10-11', note=''))
        expense.refresh_from_db()
        self.assertEqual((expense.category, expense.amount, expense.expense_date, expense.note),
                         ('mileage', Decimal('30.00'), date(2026, 10, 11), ''))

    def test_invalid_edit_leaves_expense_unchanged(self):
        expense = ShiftExpense.objects.create(job=self.job, locum=self.locum, category='parking',
                                              amount=Decimal('12.50'), expense_date=date(2026, 10, 10))
        self.client.post(reverse('edit_expense', args=[expense.id]), self.expense_data(amount='-1'))
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal('12.50'))

    def test_delete_expense(self):
        expense = ShiftExpense.objects.create(job=self.job, locum=self.locum, category='parking',
                                              amount=Decimal('12.50'), expense_date=date(2026, 10, 10))
        response = self.client.post(reverse('delete_expense', args=[expense.id]))
        self.assertRedirects(response, self.ledger_url())
        self.assertFalse(ShiftExpense.objects.exists())

    def test_expense_changes_must_be_posted(self):
        expense = ShiftExpense.objects.create(job=self.job, locum=self.locum, category='parking',
                                              amount=Decimal('12.50'), expense_date=date(2026, 10, 10))
        for url in (reverse('add_expense', args=[self.job.id]),
                    reverse('edit_expense', args=[expense.id]),
                    reverse('delete_expense', args=[expense.id])):
            self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(ShiftExpense.objects.count(), 1)


class AccessRestrictionTests(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.other_expense = ShiftExpense.objects.create(
            job=self.other_job, locum=self.other, category='parking',
            amount=Decimal('9.00'), expense_date=date(2026, 10, 10))
        self.other_invoice = LocumInvoice.objects.create(
            job=self.other_job, locum=self.other, invoice_number='X1', total_amount=Decimal('240.00'))

    def test_cannot_view_another_locums_pages(self):
        for url in (self.ledger_url(self.other),
                    reverse('generate_receipt_form', args=[self.other_job.id]),
                    reverse('generate_pdf_receipt', args=[self.other_job.id]),
                    reverse('locum_calander', args=[self.other.id])):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_cannot_change_another_locums_records(self):
        posts = [
            (reverse('add_expense', args=[self.other_job.id]), self.expense_data()),
            (reverse('edit_expense', args=[self.other_expense.id]), self.expense_data(amount='1.00')),
            (reverse('delete_expense', args=[self.other_expense.id]), {}),
            (reverse('mark_invoice_paid', args=[self.other_invoice.id]), {}),
            (reverse('generate_pdf_receipt', args=[self.other_job.id]),
             {'account_number': '1', 'sort_code': '1'}),
            (reverse('avail_added', args=[self.other.id]), {'Date': '2026-10-10', 'Timings': '9-5'}),
        ]
        for url, data in posts:
            self.assertEqual(self.client.post(url, data).status_code, 403, url)
        self.other_expense.refresh_from_db()
        self.other_invoice.refresh_from_db()
        self.assertEqual(self.other_expense.amount, Decimal('9.00'))
        self.assertEqual(self.other_invoice.status, LocumInvoice.STATUS_PENDING)
        self.assertEqual(ShiftExpense.objects.count(), 1)
        self.assertEqual(LocumInvoice.objects.count(), 1)

    def test_unapproved_application_gives_no_access_to_the_job(self):
        employer_job = make_job(self.employer, self.other, date(2026, 10, 15), date(2026, 10, 15))
        AppliedJob.objects.create(locum=self.locum, job=employer_job, approved=False)
        response = self.client.post(reverse('add_expense', args=[employer_job.id]), self.expense_data())
        self.assertEqual(response.status_code, 403)

    def test_logged_out_users_are_sent_to_login(self):
        self.client.logout()
        for url in (self.ledger_url(), reverse('generate_receipt_form', args=[self.job.id]),
                    reverse('locum_calander', args=[self.locum.id])):
            self.assertRedirects(self.client.get(url), reverse('login'), fetch_redirect_response=False)
        response = self.client.post(reverse('add_expense', args=[self.job.id]), self.expense_data())
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
        self.assertFalse(ShiftExpense.objects.filter(job=self.job).exists())

    def test_admin_accounts_cannot_use_locum_pages(self):
        admin = Admin.objects.create(email='admin@example.com', first_name='Ad', last_name='Min')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(self.ledger_url()).status_code, 403)

    def test_owner_can_still_generate_their_invoice_pdf(self):
        response = self.client.post(reverse('generate_pdf_receipt', args=[self.job.id]), {
            'account_number': '12345678', 'sort_code': '00-00-00', 'invoice_number': 'INV-1',
            'working_hours_2026-10-10': '9-5', 'hours_worked_2026-10-10': '8',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        invoice = LocumInvoice.objects.get(locum=self.locum)
        self.assertEqual((invoice.total_amount, invoice.status), (Decimal('240.00'), 'pending'))
