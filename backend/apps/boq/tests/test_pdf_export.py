from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.boq.services import BOQItemService, BOQSectionService, BOQService
from apps.clients.models import Client
from apps.common.test_utils import extract_pdf_text, make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project

User = get_user_model()


class BOQPdfExportTestCase(TestCase):
    """
    BE-076: `GET /projects/{projectId}/boq/pdf`.
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(
            name="Studio One", status=CompanyStatus.ACTIVE, currency="INR", gst_number="27ABCDE1234F1Z5"
        )
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(
            company=self.company1, name="Client One", email="client@one.com", gstin="27XYZAB5678G1Z9"
        )
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(company=self.company1, client=self.client1, name="Kitchen Remodel")
        self.project_c2 = Project.objects.create(company=self.company2, client=self.client2, name="Office Fitout")

        boq = BOQService.get_or_create_boq_for_project(self.project1)
        section = BOQSectionService.create_section(boq=boq, name="Civil Work")
        BOQItemService.create_item(
            section=section, product_id=None, description="Plastering", quantity=Decimal("10.00"),
            unit="sqft", rate=Decimal("50.00"),
        )
        self.boq = boq

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    # 1. authorized PDF returns 200
    def test_authorized_pdf_returns_200(self):
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # 2. content-type application/pdf
    def test_content_type_is_application_pdf(self):
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        self.assertEqual(response["Content-Type"], "application/pdf")

    # 3. valid PDF signature
    def test_valid_pdf_signature(self):
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))

    # 4. tenant isolation
    def test_cross_tenant_project_returns_404(self):
        response = self.client.get(f"/projects/{self.project_c2.id}/boq/pdf")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 5. unauthorized access
    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # 6. project/client/items included in render context
    def test_content_includes_real_project_client_items(self):
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        text = extract_pdf_text(response.content)
        self.assertIn("Kitchen Remodel", text)
        self.assertIn("Client One", text)
        self.assertIn("Plastering", text)
        self.assertIn("Civil Work", text)

    # 7. large/multi-section BOQ generation
    def test_large_multi_section_boq_generates(self):
        for section_index in range(5):
            section = BOQSectionService.create_section(boq=self.boq, name=f"Section {section_index}")
            for item_index in range(15):
                BOQItemService.create_item(
                    section=section, product_id=None, description=f"Item {section_index}-{item_index}",
                    quantity=Decimal("1.00"), unit="nos", rate=Decimal("100.00"),
                )
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.startswith(b"%PDF-"))

    # preview mode
    def test_preview_mode_uses_inline_disposition(self):
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf?mode=preview")
        self.assertIn("inline", response["Content-Disposition"])

    def test_download_mode_uses_attachment_disposition(self):
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    # filename sanitized
    def test_filename_derived_from_project_name(self):
        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        self.assertIn('filename="BOQ-Kitchen-Remodel.pdf"', response["Content-Disposition"])

    def test_filename_sanitizes_unsafe_project_name(self):
        unsafe_project = Project.objects.create(
            company=self.company1, client=self.client1, name='Villa "Deluxe" <script>'
        )
        BOQService.get_or_create_boq_for_project(unsafe_project)
        response = self.client.get(f"/projects/{unsafe_project.id}/boq/pdf")
        disposition = response["Content-Disposition"]
        self.assertNotIn("<", disposition)
        self.assertNotIn(">", disposition)
        self.assertNotIn('"Deluxe"', disposition)

    # unsafe HTML escaped
    def test_unsafe_client_name_is_escaped_not_executed(self):
        unsafe_client = Client.objects.create(company=self.company1, name="<script>alert(1)</script>")
        unsafe_project = Project.objects.create(company=self.company1, client=unsafe_client, name="Unsafe Project")
        BOQService.get_or_create_boq_for_project(unsafe_project)
        response = self.client.get(f"/projects/{unsafe_project.id}/boq/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.startswith(b"%PDF-"))
        text = extract_pdf_text(response.content)
        # Django's autoescaping renders the literal characters as text
        # (&lt;script&gt; decoded back to plain text by the PDF reader),
        # never as markup the renderer interprets.
        self.assertIn("script", text)
        self.assertIn("alert(1)", text)

    # empty BOQ (no sections yet) still generates cleanly
    def test_empty_boq_generates_without_error(self):
        empty_project = Project.objects.create(company=self.company1, client=self.client1, name="Fresh Project")
        response = self.client.get(f"/projects/{empty_project.id}/boq/pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.startswith(b"%PDF-"))

    # optional/alternative items excluded from the authoritative total,
    # never recomputed in the template
    def test_optional_items_excluded_from_total_matches_summary_service(self):
        from apps.boq.services import BOQSummaryService

        section = BOQSectionService.create_section(boq=self.boq, name="Extras")
        BOQItemService.create_item(
            section=section, product_id=None, description="Optional Marble", quantity=Decimal("1.00"),
            unit="nos", rate=Decimal("99999.00"), is_optional=True,
        )
        expected_summary = BOQSummaryService.compute_summary(self.boq)

        response = self.client.get(f"/projects/{self.project1.id}/boq/pdf")
        text = extract_pdf_text(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The rendered Total must equal the real summary service's value
        # (the pre-existing item only, 10 x 50 = 500.00) -- proving the
        # huge 99,999.00 optional item was excluded exactly as
        # BOQSummaryService.compute_summary already excludes it, not
        # recomputed independently in the template.
        self.assertEqual(expected_summary["total"], Decimal("500.00"))
        # "99,999.00" legitimately appears once, as the optional item's own
        # row (still shown, just labeled excluded) -- what must never
        # appear is a Total line that wrongly folded it in.
        self.assertNotIn("100,499.00", text)  # would appear if wrongly included
        self.assertIn("Total\n INR 500.00", text)
