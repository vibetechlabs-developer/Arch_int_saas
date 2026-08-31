from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.boq.services import BOQItemService, BOQSectionService, BOQService, BOQSummaryService
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.products.models import ProductUnit
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class BOQSummaryServiceTestCase(TestCase):
    """
    Unit test suite for BOQSummaryService.compute_summary (BE-037).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Client One")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.boq = BOQService.get_or_create_boq_for_project(self.project)
        self.section = BOQSectionService.create_section(boq=self.boq, name="Flooring")

    def test_summary_with_no_items_is_all_zero(self):
        summary = BOQSummaryService.compute_summary(self.boq)
        self.assertEqual(summary["subtotal"], Decimal("0.00"))
        self.assertEqual(summary["discount"], Decimal("0.00"))
        self.assertEqual(summary["tax"], Decimal("0.00"))
        self.assertEqual(summary["total"], Decimal("0.00"))

    def test_summary_single_item_no_discount_no_tax(self):
        BOQItemService.create_item(
            section=self.section, description="A", quantity=Decimal("10.00"),
            unit=ProductUnit.SQFT, rate=Decimal("50.00"),
        )
        summary = BOQSummaryService.compute_summary(self.boq)
        self.assertEqual(summary["subtotal"], Decimal("500.00"))
        self.assertEqual(summary["discount"], Decimal("0.00"))
        self.assertEqual(summary["tax"], Decimal("0.00"))
        self.assertEqual(summary["total"], Decimal("500.00"))

    def test_summary_applies_discount_then_tax(self):
        """
        base=500.00, discount=10% -> 50.00 off -> after_discount=450.00,
        tax=18% of 450.00 -> 81.00 -> total=450.00+81.00=531.00.
        """
        BOQItemService.create_item(
            section=self.section, description="A", quantity=Decimal("10.00"),
            unit=ProductUnit.SQFT, rate=Decimal("50.00"),
            discount=Decimal("10.00"), tax=Decimal("18.00"),
        )
        summary = BOQSummaryService.compute_summary(self.boq)
        self.assertEqual(summary["subtotal"], Decimal("500.00"))
        self.assertEqual(summary["discount"], Decimal("50.00"))
        self.assertEqual(summary["tax"], Decimal("81.00"))
        self.assertEqual(summary["total"], Decimal("531.00"))

    def test_summary_excludes_optional_items(self):
        BOQItemService.create_item(
            section=self.section, description="Included", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        BOQItemService.create_item(
            section=self.section, description="Optional", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("999.00"), is_optional=True,
        )
        summary = BOQSummaryService.compute_summary(self.boq)
        self.assertEqual(summary["subtotal"], Decimal("100.00"))
        self.assertEqual(summary["total"], Decimal("100.00"))

    def test_summary_excludes_alternative_items(self):
        BOQItemService.create_item(
            section=self.section, description="Included", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        BOQItemService.create_item(
            section=self.section, description="Alternative", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("999.00"), is_alternative=True,
        )
        summary = BOQSummaryService.compute_summary(self.boq)
        self.assertEqual(summary["subtotal"], Decimal("100.00"))
        self.assertEqual(summary["total"], Decimal("100.00"))

    def test_summary_excludes_soft_deleted_items(self):
        item = BOQItemService.create_item(
            section=self.section, description="Deleted", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        BOQItemService.soft_delete_item(item.id)

        summary = BOQSummaryService.compute_summary(self.boq)
        self.assertEqual(summary["subtotal"], Decimal("0.00"))

    def test_summary_aggregates_across_multiple_sections(self):
        section2 = BOQSectionService.create_section(boq=self.boq, name="Lighting")
        BOQItemService.create_item(
            section=self.section, description="A", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        BOQItemService.create_item(
            section=section2, description="B", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("200.00"),
        )
        summary = BOQSummaryService.compute_summary(self.boq)
        self.assertEqual(summary["subtotal"], Decimal("300.00"))


class BOQSummaryEndpointTestCase(TestCase):
    """
    Integration tests for GET /projects/{id}/boq/summary (BE-037).
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

    def _url(self, project_id):
        return f"/projects/{project_id}/boq/summary"

    def test_unauthenticated_requests_fail_401(self):
        response = self.client.get(self._url(self.project1.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cross_tenant_project_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(self._url(self.project_c2.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_summary_with_no_boq_yet_returns_zeros(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(self._url(self.project1.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["subtotal"], "0.00")
        self.assertEqual(data["total"], "0.00")

    def test_summary_reflects_created_items(self):
        boq = BOQService.get_or_create_boq_for_project(self.project1)
        section = BOQSectionService.create_section(boq=boq, name="Flooring")
        BOQItemService.create_item(
            section=section, description="A", quantity=Decimal("2.00"),
            unit=ProductUnit.JOB, rate=Decimal("50.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(self._url(self.project1.id))

        data = response.json()["data"]
        self.assertEqual(data["subtotal"], "100.00")
        self.assertEqual(data["total"], "100.00")
