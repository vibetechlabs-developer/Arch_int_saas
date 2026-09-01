from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.invoices.models import Invoice
from apps.projects.models import Project
from apps.quotations.services import QuotationService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class InvoiceViewsTestCase(TestCase):
    """
    Integration test suite for the Invoice HTTP endpoints (BE-042):
    `GET`/`POST /projects/{projectId}/invoices`,
    `GET`/`PATCH /invoices/{invoiceId}`, `/send`, `/cancel`.
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
        response = self.client.get(f"/projects/{self.project1.id}/invoices")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_cross_tenant_project_returns_404(self):
        response = self.client.get(f"/projects/{self.project_c2.id}/invoices")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_ad_hoc_invoice(self):
        response = self.client.post(
            f"/projects/{self.project1.id}/invoices",
            {
                "items": [{"description": "Custom work", "quantity": "2.00", "unit": "job", "rate": "100.00"}],
                "discount": "20.00",
                "tax": "10.00",
                "dueDate": "2026-12-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["invoiceNumber"], "INV-000001")
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["subtotal"], "200.00")
        self.assertEqual(data["total"], "190.00")
        self.assertEqual(data["clientId"], str(self.client1.id))

    def test_create_from_approved_quotation(self):
        quotation = QuotationService.create_quotation(
            project=self.project1,
            items=[{"description": "Tiling", "quantity": Decimal("10.00"), "rate": Decimal("50.00")}],
        )
        QuotationService.send_quotation(quotation)
        quotation.refresh_from_db()
        QuotationService.approve_quotation(quotation)
        quotation.refresh_from_db()

        response = self.client.post(
            f"/projects/{self.project1.id}/invoices", {"quotationId": str(quotation.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["quotationId"], str(quotation.id))
        self.assertEqual(data["subtotal"], "500.00")

    def test_create_with_neither_quotation_nor_items_returns_400(self):
        response = self.client.post(f"/projects/{self.project1.id}/invoices", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_invoice_detail(self):
        invoice = Invoice.objects.create(
            company=self.company1, project=self.project1, client=self.client1, invoice_number="INV-000001",
        )
        response = self.client.get(f"/invoices/{invoice.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(invoice.id))

    def test_get_invoice_detail_cross_tenant_returns_404(self):
        invoice = Invoice.objects.create(
            company=self.company2, project=self.project_c2, client=self.client2, invoice_number="INV-000001",
        )
        response = self.client.get(f"/invoices/{invoice.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_draft_invoice(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/invoices",
            {"items": [{"description": "X", "quantity": "1.00", "rate": "50.00"}]},
            format="json",
        )
        invoice_id = create_resp.json()["data"]["id"]

        response = self.client.patch(f"/invoices/{invoice_id}", {"notes": "Updated"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["notes"], "Updated")

    def test_patch_sent_invoice_returns_409(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/invoices",
            {"items": [{"description": "X", "quantity": "1.00", "rate": "50.00"}]},
            format="json",
        )
        invoice_id = create_resp.json()["data"]["id"]
        self.client.post(f"/invoices/{invoice_id}/send", {}, format="json")

        response = self.client.patch(f"/invoices/{invoice_id}", {"notes": "Too late"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_send_then_cancel_flow(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/invoices",
            {"items": [{"description": "X", "quantity": "1.00", "rate": "50.00"}]},
            format="json",
        )
        invoice_id = create_resp.json()["data"]["id"]

        send_resp = self.client.post(f"/invoices/{invoice_id}/send", {}, format="json")
        self.assertEqual(send_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(send_resp.json()["data"]["status"], "sent")

        cancel_resp = self.client.post(f"/invoices/{invoice_id}/cancel", {}, format="json")
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_resp.json()["data"]["status"], "cancelled")

    def test_cancel_cross_tenant_returns_404(self):
        invoice = Invoice.objects.create(
            company=self.company2, project=self.project_c2, client=self.client2, invoice_number="INV-000001",
        )
        response = self.client.post(f"/invoices/{invoice.id}/cancel", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
