import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.dashboard.services import DashboardService
from apps.expenses.services import ExpenseService
from apps.invoices.services import InvoiceService
from apps.projects.models import Project, ProjectStatus
from apps.quotations.services import QuotationService


class DashboardServiceTestCase(TestCase):
    """
    Unit test suite for DashboardService.compute (BE-048).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def test_empty_dashboard(self):
        report = DashboardService.compute(self.company.id)
        self.assertEqual(report["kpis"]["totalProjects"], 1)
        self.assertEqual(report["kpis"]["activeProjects"], 1)
        self.assertEqual(report["kpis"]["totalQuotations"], 0)
        self.assertEqual(report["kpis"]["totalBilledRevenue"], Decimal("0.00"))
        self.assertEqual(report["recentProjects"], [{
            "id": self.project.id, "name": "Kitchen Remodel", "status": ProjectStatus.DRAFT,
            "clientName": "Jane Doe", "createdAt": self.project.created_at,
        }])
        self.assertEqual(report["recentQuotations"], [])
        self.assertEqual(report["pendingPayments"], [])
        self.assertEqual(report["overdueInvoices"], [])
        self.assertEqual(report["recentExpenses"], [])
        self.assertEqual(report["upcomingDeadlines"], [])
        self.assertEqual(report["recentActivities"], [])
        # The one active project still shows up, all-zero -- a project
        # with no financial activity yet is a valid profitability row,
        # not one to hide.
        self.assertEqual(report["projectProfitability"], [{
            "projectId": self.project.id, "projectName": "Kitchen Remodel",
            "revenue": Decimal("0.00"), "expenses": Decimal("0.00"), "profit": Decimal("0.00"),
        }])

    def test_active_projects_excludes_terminal_statuses(self):
        Project.objects.create(
            company=self.company, client=self.client_obj, name="Completed Project",
            status=ProjectStatus.COMPLETED,
        )
        report = DashboardService.compute(self.company.id)
        self.assertEqual(report["kpis"]["totalProjects"], 2)
        self.assertEqual(report["kpis"]["activeProjects"], 1)

    def test_total_quotations_counts_distinct_quote_numbers_not_versions(self):
        quotation = QuotationService.create_quotation(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        QuotationService.revise_quotation(quotation)

        report = DashboardService.compute(self.company.id)
        self.assertEqual(report["kpis"]["totalQuotations"], 1)

    def test_kpis_reuse_finance_report_service(self):
        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("500.00")}],
        )
        InvoiceService.send_invoice(invoice)

        report = DashboardService.compute(self.company.id)
        self.assertEqual(report["kpis"]["totalBilledRevenue"], Decimal("500.00"))
        self.assertEqual(report["kpis"]["pendingAmount"], Decimal("500.00"))

    def test_pending_payments_lists_sent_and_partially_paid(self):
        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(invoice)

        report = DashboardService.compute(self.company.id)
        self.assertEqual(len(report["pendingPayments"]), 1)
        self.assertEqual(report["pendingPayments"][0]["invoiceNumber"], "INV-000001")

    def test_overdue_invoices_lists_only_past_due_date(self):
        invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
            due_date=timezone.localdate() - datetime.timedelta(days=1),
        )
        InvoiceService.send_invoice(invoice)

        report = DashboardService.compute(self.company.id)
        self.assertEqual(len(report["overdueInvoices"]), 1)

    def test_upcoming_deadlines_within_30_days(self):
        Project.objects.create(
            company=self.company, client=self.client_obj, name="Soon Due",
            deadline=timezone.localdate() + datetime.timedelta(days=10),
        )
        Project.objects.create(
            company=self.company, client=self.client_obj, name="Far Off",
            deadline=timezone.localdate() + datetime.timedelta(days=100),
        )

        report = DashboardService.compute(self.company.id)
        names = [row["name"] for row in report["upcomingDeadlines"]]
        self.assertIn("Soon Due", names)
        self.assertNotIn("Far Off", names)

    def test_project_profitability_computed_per_project(self):
        invoice = InvoiceService.create_invoice(
            project=self.project, items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("500.00")}],
        )
        InvoiceService.send_invoice(invoice)
        expense = ExpenseService.create_expense(
            project=self.project, amount=Decimal("100.00"), date="2026-09-01"
        )
        ExpenseService.submit_expense(expense)
        expense.refresh_from_db()
        ExpenseService.approve_expense(expense)

        report = DashboardService.compute(self.company.id)
        self.assertEqual(len(report["projectProfitability"]), 1)
        row = report["projectProfitability"][0]
        self.assertEqual(row["revenue"], Decimal("500.00"))
        self.assertEqual(row["expenses"], Decimal("100.00"))
        self.assertEqual(row["profit"], Decimal("400.00"))

    def test_company_isolation(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        report = DashboardService.compute(other_company.id)
        self.assertEqual(report["kpis"]["totalProjects"], 0)
