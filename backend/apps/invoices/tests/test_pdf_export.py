from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import extract_pdf_text, make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.invoices.services import InvoiceService
from apps.payments.services import PaymentService
from apps.projects.models import Project

User = get_user_model()


class InvoicePdfExportTestCase(TestCase):
    """
    BE-076: `GET /invoices/{invoiceId}/pdf`.
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE, currency="INR")
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(company=self.company1, client=self.client1, name="Kitchen Remodel")
        self.project_c2 = Project.objects.create(company=self.company2, client=self.client2, name="Office Fitout")

        self.invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Design Fee", "quantity": Decimal("1.00"), "rate": Decimal("1000.00")}],
            tax=Decimal("50.00"),
        )
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    # 13. authorized PDF
    def test_authorized_pdf_returns_200(self):
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))

    # 14. correct totals
    def test_totals_match_backend_values_exactly(self):
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("INR 1,000.00", text)  # subtotal
        self.assertIn("INR 50.00", text)  # tax
        self.assertIn("INR 1,050.00", text)  # grand total

    # 15. payment summary if backend exposes it
    def test_payment_summary_reflects_backend_authoritative_aggregate(self):
        PaymentService.create_payment(invoice=self.invoice, payment_date="2026-09-01", amount=Decimal("400.00"))
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("INR 400.00", text)  # amount paid
        self.assertIn("INR 650.00", text)  # balance due: 1050 - 400

    def test_zero_payments_shows_full_outstanding_balance(self):
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("INR 0.00", text)  # amount paid
        self.assertIn("INR 1,050.00", text)  # balance due == total

    def test_overpayment_shows_real_paid_amount_with_zero_balance_never_negative(self):
        PaymentService.create_payment(invoice=self.invoice, payment_date="2026-09-01", amount=Decimal("2000.00"))
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("INR 2,000.00", text)  # real amount paid, larger than total
        self.assertNotIn("-INR", text)
        self.assertNotIn("Credit Balance", text)

    # 16. tenant isolation
    def test_cross_tenant_invoice_returns_404(self):
        other_invoice = InvoiceService.create_invoice(
            project=self.project_c2,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("10.00")}],
        )
        response = self.client.get(f"/invoices/{other_invoice.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 17. invalid id 404
    def test_nonexistent_invoice_returns_404(self):
        response = self.client.get("/invoices/00000000-0000-0000-0000-000000000000/pdf")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_preview_mode_uses_inline_disposition(self):
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf?mode=preview")
        self.assertIn("inline", response["Content-Disposition"])

    def test_filename_includes_invoice_number(self):
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        self.assertIn(f'filename="Invoice-{self.invoice.invoice_number}.pdf"', response["Content-Disposition"])

    def test_status_label_reflects_real_effective_status(self):
        response = self.client.get(f"/invoices/{self.invoice.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("SENT", text)

    def test_draft_invoice_can_still_be_exported(self):
        draft_invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Draft item", "quantity": Decimal("1.00"), "rate": Decimal("80.00")}],
        )
        response = self.client.get(f"/invoices/{draft_invoice.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        text = extract_pdf_text(response.content)
        self.assertIn("DRAFT", text)
