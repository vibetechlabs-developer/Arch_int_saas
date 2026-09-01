from decimal import Decimal

from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.expenses.services import ExpenseService
from apps.invoices.services import InvoiceService
from apps.payments.services import PaymentService
from apps.projects.models import Project
from apps.reports.services import ExpenseReportService, FinanceReportService


class FinanceReportServiceTestCase(TestCase):
    """
    Unit test suite for FinanceReportService.compute (BE-045).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def test_report_with_no_data_is_all_zero(self):
        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["revenue"], Decimal("0.00"))
        self.assertEqual(report["received"], Decimal("0.00"))
        self.assertEqual(report["expenses"], Decimal("0.00"))
        self.assertEqual(report["profit_loss"], Decimal("0.00"))

    def test_draft_invoice_excluded_from_revenue(self):
        InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["revenue"], Decimal("0.00"))

    def test_sent_invoice_counts_as_revenue(self):
        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(invoice)
        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["revenue"], Decimal("100.00"))
        self.assertEqual(report["receivables"], Decimal("100.00"))

    def test_payment_reduces_receivables_and_increases_received(self):
        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(invoice)
        invoice.refresh_from_db()
        PaymentService.create_payment(invoice, payment_date="2026-09-01", amount=Decimal("60.00"))

        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["received"], Decimal("60.00"))
        self.assertEqual(report["receivables"], Decimal("40.00"))

    def test_cancelled_invoice_excluded_from_revenue(self):
        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.cancel_invoice(invoice)
        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["revenue"], Decimal("0.00"))

    def test_overdue_unpaid_invoice_counts_as_outstanding(self):
        import datetime
        from django.utils import timezone

        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
            due_date=timezone.localdate() - datetime.timedelta(days=1),
        )
        InvoiceService.send_invoice(invoice)

        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["outstanding"], Decimal("100.00"))

    def test_future_due_date_not_counted_as_outstanding(self):
        import datetime
        from django.utils import timezone

        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
            due_date=timezone.localdate() + datetime.timedelta(days=5),
        )
        InvoiceService.send_invoice(invoice)

        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["outstanding"], Decimal("0.00"))

    def test_approved_expense_reduces_profit_loss(self):
        expense = ExpenseService.create_expense(
            project=self.project, amount=Decimal("50.00"), tax=Decimal("5.00"), date="2026-09-01"
        )
        ExpenseService.submit_expense(expense)
        expense.refresh_from_db()
        ExpenseService.approve_expense(expense)

        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["expenses"], Decimal("55.00"))
        self.assertEqual(report["profit_loss"], Decimal("-55.00"))

    def test_draft_expense_excluded_from_expenses(self):
        ExpenseService.create_expense(project=self.project, amount=Decimal("50.00"), date="2026-09-01")
        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["expenses"], Decimal("0.00"))

    def test_project_filter_scopes_report(self):
        other_project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Other Project"
        )
        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(invoice)
        other_invoice = InvoiceService.create_invoice(
            project=other_project, items=[{"description": "Y", "quantity": Decimal("1.00"), "rate": Decimal("200.00")}],
        )
        InvoiceService.send_invoice(other_invoice)

        report = FinanceReportService.compute(self.company.id, project_id=self.project.id)
        self.assertEqual(report["revenue"], Decimal("100.00"))

    def test_company_isolation(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        other_client = Client.objects.create(company=other_company, name="Other Client")
        other_project = Project.objects.create(
            company=other_company, client=other_client, name="Other Project"
        )
        other_invoice = InvoiceService.create_invoice(
            project=other_project, items=[{"description": "Y", "quantity": Decimal("1.00"), "rate": Decimal("999.00")}],
        )
        InvoiceService.send_invoice(other_invoice)

        report = FinanceReportService.compute(self.company.id)
        self.assertEqual(report["revenue"], Decimal("0.00"))


class ExpenseReportServiceTestCase(TestCase):
    """
    Unit test suite for ExpenseReportService.compute (BE-045).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        ExpenseService.create_expense(
            project=self.project, category="Materials", vendor="ABC", amount=Decimal("100.00"), date="2026-09-01",
        )
        ExpenseService.create_expense(
            project=self.project, category="Materials", vendor="XYZ", amount=Decimal("50.00"), date="2026-09-02",
        )
        ExpenseService.create_expense(
            project=self.project, category="Labour", vendor="ABC", amount=Decimal("200.00"), date="2026-09-01",
        )

    def test_by_category_groups_and_sums(self):
        report = ExpenseReportService.compute(self.company.id)
        by_category = {row["key"]: row["total"] for row in report["byCategory"]}
        self.assertEqual(by_category["Materials"], Decimal("150.00"))
        self.assertEqual(by_category["Labour"], Decimal("200.00"))

    def test_by_vendor_groups_and_sums(self):
        report = ExpenseReportService.compute(self.company.id)
        by_vendor = {row["key"]: row["total"] for row in report["byVendor"]}
        self.assertEqual(by_vendor["ABC"], Decimal("300.00"))
        self.assertEqual(by_vendor["XYZ"], Decimal("50.00"))

    def test_by_date_groups_and_sums(self):
        report = ExpenseReportService.compute(self.company.id)
        by_date = {row["key"]: row["total"] for row in report["byDate"]}
        self.assertEqual(by_date["2026-09-01"], Decimal("300.00"))
        self.assertEqual(by_date["2026-09-02"], Decimal("50.00"))

    def test_date_range_filters_results(self):
        report = ExpenseReportService.compute(self.company.id, date_from="2026-09-02", date_to="2026-09-02")
        by_date = {row["key"]: row["total"] for row in report["byDate"]}
        self.assertEqual(set(by_date.keys()), {"2026-09-02"})
