from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.expenses.models import Expense
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ExpenseViewsTestCase(TestCase):
    """
    Integration test suite for the Expense HTTP endpoints (BE-044).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        CompanyMembership.objects.create(
            company=self.company1, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project_c2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_unauthenticated_list_fails_401(self):
        self.client.credentials()
        response = self.client.get(f"/projects/{self.project1.id}/expenses")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_cross_tenant_project_returns_404(self):
        response = self.client.get(f"/projects/{self.project_c2.id}/expenses")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_expense(self):
        response = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"category": "Materials", "vendor": "ABC Corp", "amount": "500.00", "date": "2026-09-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["approvalStatus"], "draft")
        self.assertEqual(data["amount"], "500.00")
        self.assertEqual(data["addedById"], str(self.member_user.id))

    def test_create_expense_missing_amount_returns_400(self):
        response = self.client.post(
            f"/projects/{self.project1.id}/expenses", {"date": "2026-09-01"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_expense_detail(self):
        expense = Expense.objects.create(
            company=self.company1, project=self.project1, amount=Decimal("100.00"), date="2026-09-01",
        )
        response = self.client.get(f"/expenses/{expense.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(expense.id))

    def test_get_expense_detail_cross_tenant_returns_404(self):
        expense = Expense.objects.create(
            company=self.company2, project=self.project_c2, amount=Decimal("100.00"), date="2026-09-01",
        )
        response = self.client.get(f"/expenses/{expense.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_draft_expense(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"amount": "100.00", "date": "2026-09-01"},
            format="json",
        )
        expense_id = create_resp.json()["data"]["id"]

        response = self.client.patch(f"/expenses/{expense_id}", {"category": "Travel"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["category"], "Travel")

    def test_delete_draft_expense(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"amount": "100.00", "date": "2026-09-01"},
            format="json",
        )
        expense_id = create_resp.json()["data"]["id"]

        response = self.client.delete(f"/expenses/{expense_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        get_resp = self.client.get(f"/expenses/{expense_id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_full_approval_workflow(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"amount": "100.00", "date": "2026-09-01"},
            format="json",
        )
        expense_id = create_resp.json()["data"]["id"]

        submit_resp = self.client.post(f"/expenses/{expense_id}/submit", {}, format="json")
        self.assertEqual(submit_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_resp.json()["data"]["approvalStatus"], "submitted")

        approve_resp = self.client.post(f"/expenses/{expense_id}/approve", {}, format="json")
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_resp.json()["data"]["approvalStatus"], "approved")

        paid_resp = self.client.post(f"/expenses/{expense_id}/mark-paid", {}, format="json")
        self.assertEqual(paid_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(paid_resp.json()["data"]["approvalStatus"], "paid")

    def test_approve_before_submit_returns_409(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"amount": "100.00", "date": "2026-09-01"},
            format="json",
        )
        expense_id = create_resp.json()["data"]["id"]

        response = self.client.post(f"/expenses/{expense_id}/approve", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_filter_by_category(self):
        self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"category": "Materials", "amount": "100.00", "date": "2026-09-01"}, format="json",
        )
        self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"category": "Labour", "amount": "200.00", "date": "2026-09-02"}, format="json",
        )

        response = self.client.get(f"/projects/{self.project1.id}/expenses?category=Materials")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["category"], "Materials")
