from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import extract_pdf_text, make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project
from apps.quotations.services import QuotationService

User = get_user_model()


class QuotationPdfExportTestCase(TestCase):
    """
    BE-076: `GET /quotations/{quotationId}/pdf`.
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

        self.quotation = QuotationService.create_quotation(
            project=self.project1,
            items=[{"description": "Tiling Work", "quantity": Decimal("10.00"), "rate": Decimal("50.00")}],
            discount=Decimal("20.00"),
            tax=Decimal("10.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    # 8. authorized PDF
    def test_authorized_pdf_returns_200(self):
        response = self.client.get(f"/quotations/{self.quotation.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))

    # 9. correct version
    def test_correct_version_shown_for_a_revision(self):
        revised = QuotationService.revise_quotation(quotation=self.quotation, discount=Decimal("0.00"))
        response = self.client.get(f"/quotations/{revised.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn(f"{revised.quote_number} · v{revised.version}", text.replace("\n", ""))
        self.assertEqual(revised.version, 2)

    def test_viewing_older_version_does_not_export_latest(self):
        """
        Requesting the original (v1) quotation's PDF must reflect v1's own
        data, never silently substitute the newer revision.
        """
        revised = QuotationService.revise_quotation(
            quotation=self.quotation,
            items=[{"description": "Completely different scope", "quantity": Decimal("1.00"), "rate": Decimal("999999.00")}],
        )
        self.assertNotEqual(revised.id, self.quotation.id)

        response = self.client.get(f"/quotations/{self.quotation.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("Tiling Work", text)
        self.assertNotIn("Completely different scope", text)
        self.assertNotIn("999999", text.replace(",", ""))

    # 10. totals present from backend
    def test_totals_match_backend_values_exactly(self):
        response = self.client.get(f"/quotations/{self.quotation.id}/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("INR 500.00", text)  # subtotal: 10 * 50
        self.assertIn("INR 20.00", text)  # discount
        self.assertIn("INR 10.00", text)  # tax
        self.assertIn("INR 490.00", text)  # grand total: 500 - 20 + 10

    # 11. tenant isolation
    def test_cross_tenant_project_returns_404(self):
        other_quotation = QuotationService.create_quotation(
            project=self.project_c2,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("10.00")}],
        )
        response = self.client.get(f"/quotations/{other_quotation.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 12. invalid id 404
    def test_nonexistent_quotation_returns_404(self):
        response = self.client.get("/quotations/00000000-0000-0000-0000-000000000000/pdf")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(f"/quotations/{self.quotation.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_preview_mode_uses_inline_disposition(self):
        response = self.client.get(f"/quotations/{self.quotation.id}/pdf?mode=preview")
        self.assertIn("inline", response["Content-Disposition"])

    def test_filename_includes_quote_number_and_version(self):
        response = self.client.get(f"/quotations/{self.quotation.id}/pdf")
        self.assertIn(
            f'filename="Quotation-{self.quotation.quote_number}-v{self.quotation.version}.pdf"',
            response["Content-Disposition"],
        )

    def test_draft_quotation_downloads_and_labels_status(self):
        self.assertEqual(self.quotation.status, "draft")
        response = self.client.get(f"/quotations/{self.quotation.id}/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        text = extract_pdf_text(response.content)
        self.assertIn("DRAFT", text)
