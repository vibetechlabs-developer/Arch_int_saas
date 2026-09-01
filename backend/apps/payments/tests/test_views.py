from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.invoices.models import Invoice
from apps.invoices.services import InvoiceService
from apps.payments.models import Payment
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class PaymentViewsTestCase(TestCase):
    """
    Integration test suite for the Payment HTTP endpoints (BE-043):
    `GET`/`POST /invoices/{invoiceId}/payments`, `DELETE /payments/{id}`.
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

        self.invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("500.00")}],
        )
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_unauthenticated_list_fails_401(self):
        self.client.credentials()
        response = self.client.get(f"/invoices/{self.invoice.id}/payments")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_record_payment(self):
        response = self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "200.00", "method": "bank_transfer"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["amount"], "200.00")
        self.assertEqual(data["method"], "bank_transfer")

        invoice_resp = self.client.get(f"/invoices/{self.invoice.id}")
        self.assertEqual(invoice_resp.json()["data"]["status"], "partially_paid")

    def test_record_payment_against_draft_invoice_returns_409(self):
        draft_invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Y", "quantity": Decimal("1.00"), "rate": Decimal("50.00")}],
        )
        response = self.client.post(
            f"/invoices/{draft_invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_record_payment_cross_tenant_invoice_returns_404(self):
        invoice_c2 = Invoice.objects.create(
            company=self.company2, project=self.project_c2, client=self.client2, invoice_number="INV-000001",
        )
        response = self.client.post(
            f"/invoices/{invoice_c2.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_payments(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "100.00"},
            format="json",
        )
        response = self.client.get(f"/invoices/{self.invoice.id}/payments")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_void_payment(self):
        create_resp = self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "500.00"},
            format="json",
        )
        payment_id = create_resp.json()["data"]["id"]

        void_resp = self.client.delete(f"/payments/{payment_id}")
        self.assertEqual(void_resp.status_code, status.HTTP_200_OK)

        list_resp = self.client.get(f"/invoices/{self.invoice.id}/payments")
        self.assertEqual(len(list_resp.json()["data"]), 0)

        invoice_resp = self.client.get(f"/invoices/{self.invoice.id}")
        self.assertEqual(invoice_resp.json()["data"]["status"], "sent")

    def test_void_payment_cross_tenant_returns_404(self):
        payment = Payment.objects.create(
            company=self.company2, invoice=Invoice.objects.create(
                company=self.company2, project=self.project_c2, client=self.client2, invoice_number="INV-000001",
            ),
            client=self.client2, project=self.project_c2, payment_date="2026-09-01", amount=Decimal("10.00"),
        )
        response = self.client.delete(f"/payments/{payment.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
