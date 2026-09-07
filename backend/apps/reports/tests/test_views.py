from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.expenses.services import ExpenseService
from apps.invoices.services import InvoiceService
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ReportViewsTestCase(TestCase):
    """
    Integration test suite for `GET /reports/finance` and
    `GET /reports/expenses` (BE-045).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )

        invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("500.00")}],
        )
        InvoiceService.send_invoice(invoice)

        expense = ExpenseService.create_expense(
            project=self.project1, category="Materials", amount=Decimal("100.00"), date="2026-09-01"
        )
        ExpenseService.submit_expense(expense)
        expense.refresh_from_db()
        ExpenseService.approve_expense(expense)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_unauthenticated_finance_report_fails_401(self):
        self.client.credentials()
        response = self.client.get("/reports/finance")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_finance_report(self):
        response = self.client.get("/reports/finance")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["revenue"], "500.00")
        self.assertEqual(data["expenses"], "100.00")
        self.assertEqual(data["profitLoss"], "400.00")

    def test_finance_report_scoped_to_project(self):
        other_project = Project.objects.create(
            company=self.company1, client=self.client1, name="Other Project"
        )
        other_invoice = InvoiceService.create_invoice(
            project=other_project, items=[{"description": "Y", "quantity": Decimal("1.00"), "rate": Decimal("999.00")}],
        )
        InvoiceService.send_invoice(other_invoice)

        response = self.client.get(f"/reports/finance?projectId={self.project1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["revenue"], "500.00")

    def test_expense_report(self):
        response = self.client.get("/reports/expenses")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data["byCategory"]), 1)
        self.assertEqual(data["byCategory"][0]["key"], "Materials")
        self.assertEqual(data["byCategory"][0]["total"], "100.00")

    def test_unauthenticated_expense_report_fails_401(self):
        self.client.credentials()
        response = self.client.get("/reports/expenses")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
