from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.boq.services import BOQItemService, BOQSectionService, BOQService
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.products.models import ProductUnit
from apps.projects.models import Project
from apps.quotations.models import Quotation, QuotationStatus
from apps.common.test_utils import make_full_access_membership
from apps.users.models import CompanyMembershipStatus

User = get_user_model()


class QuotationViewsTestCase(TestCase):
    """
    Integration test suite for the Quotation HTTP endpoints (BE-039):
    `GET`/`POST /projects/{projectId}/quotations`,
    `GET /quotations/{quotationId}`.
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(
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

    def _authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_unauthenticated_list_fails_401(self):
        response = self.client.get(f"/projects/{self.project1.id}/quotations")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_cross_tenant_project_returns_404(self):
        self._authenticate()
        response = self.client.get(f"/projects/{self.project_c2.id}/quotations")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_manual_quotation(self):
        self._authenticate()
        response = self.client.post(
            f"/projects/{self.project1.id}/quotations",
            {
                "items": [
                    {"description": "Custom work", "quantity": "2.00", "unit": "job", "rate": "100.00"},
                ],
                "discount": "20.00",
                "tax": "10.00",
                "terms": "50% advance",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["quoteNumber"], "QT-000001")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["status"], QuotationStatus.DRAFT)
        self.assertEqual(data["subtotal"], "200.00")
        self.assertEqual(data["total"], "190.00")
        self.assertEqual(data["clientId"], str(self.client1.id))
        self.assertEqual(len(data["items"]), 1)

    def test_create_quotation_from_boq(self):
        boq = BOQService.get_or_create_boq_for_project(self.project1)
        section = BOQSectionService.create_section(boq=boq, name="Flooring")
        BOQItemService.create_item(
            section=section, description="Tiling", quantity=Decimal("10.00"),
            unit=ProductUnit.SQFT, rate=Decimal("50.00"),
        )

        self._authenticate()
        response = self.client.post(
            f"/projects/{self.project1.id}/quotations", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["boqId"], str(boq.id))
        self.assertEqual(data["subtotal"], "500.00")

    def test_create_quotation_from_empty_boq_returns_400(self):
        self._authenticate()
        response = self.client.post(
            f"/projects/{self.project1.id}/quotations", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_manual_quotation_zero_quantity_returns_400(self):
        self._authenticate()
        response = self.client.post(
            f"/projects/{self.project1.id}/quotations",
            {"items": [{"description": "X", "quantity": "0.00", "rate": "10.00"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_quotation_cross_tenant_project_returns_404(self):
        self._authenticate()
        response = self.client.post(
            f"/projects/{self.project_c2.id}/quotations",
            {"items": [{"description": "X", "quantity": "1.00", "rate": "1.00"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_quotations_returns_all_versions(self):
        Quotation.objects.create(
            company=self.company1, project=self.project1, client=self.client1,
            quote_number="QT-000001", version=1,
        )
        Quotation.objects.create(
            company=self.company1, project=self.project1, client=self.client1,
            quote_number="QT-000001", version=2,
        )

        self._authenticate()
        response = self.client.get(f"/projects/{self.project1.id}/quotations")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_get_quotation_detail(self):
        quotation = Quotation.objects.create(
            company=self.company1, project=self.project1, client=self.client1,
            quote_number="QT-000001", version=1,
        )

        self._authenticate()
        response = self.client.get(f"/quotations/{quotation.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(quotation.id))

    def test_get_quotation_detail_cross_tenant_returns_404(self):
        quotation = Quotation.objects.create(
            company=self.company2, project=self.project_c2, client=self.client2,
            quote_number="QT-000001", version=1,
        )

        self._authenticate()
        response = self.client.get(f"/quotations/{quotation.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class QuotationReviseViewTestCase(TestCase):
    """
    Integration test suite for `POST /quotations/{quotationId}/revise`
    (BE-040).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(
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

    def test_revise_creates_new_version(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/quotations",
            {"items": [{"description": "X", "quantity": "1.00", "rate": "100.00"}]},
            format="json",
        )
        quotation_id = create_resp.json()["data"]["id"]

        response = self.client.post(f"/quotations/{quotation_id}/revise", {"terms": "New terms"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["terms"], "New terms")

    def test_revise_second_time_on_stale_version_returns_409(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/quotations",
            {"items": [{"description": "X", "quantity": "1.00", "rate": "100.00"}]},
            format="json",
        )
        quotation_id = create_resp.json()["data"]["id"]

        self.client.post(f"/quotations/{quotation_id}/revise", {}, format="json")
        stale_response = self.client.post(f"/quotations/{quotation_id}/revise", {}, format="json")
        self.assertEqual(stale_response.status_code, status.HTTP_409_CONFLICT)

    def test_revise_cross_tenant_returns_404(self):
        quotation = Quotation.objects.create(
            company=self.company2, project=self.project_c2, client=self.client2,
            quote_number="QT-000001", version=1,
        )

        response = self.client.post(f"/quotations/{quotation.id}/revise", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class QuotationApprovalWorkflowViewsTestCase(TestCase):
    """
    Integration test suite for `POST /quotations/{quotationId}/send`,
    `/approve`, `/reject` (BE-041).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(
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

        create_resp = self.client.post(
            f"/projects/{self.project1.id}/quotations",
            {"items": [{"description": "X", "quantity": "1.00", "rate": "100.00"}]},
            format="json",
        )
        self.quotation_id = create_resp.json()["data"]["id"]

    def test_send_then_approve_full_flow(self):
        send_resp = self.client.post(f"/quotations/{self.quotation_id}/send", {}, format="json")
        self.assertEqual(send_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(send_resp.json()["data"]["status"], "sent")

        approve_resp = self.client.post(f"/quotations/{self.quotation_id}/approve", {}, format="json")
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_resp.json()["data"]["status"], "approved")

    def test_send_then_reject_full_flow(self):
        self.client.post(f"/quotations/{self.quotation_id}/send", {}, format="json")

        reject_resp = self.client.post(f"/quotations/{self.quotation_id}/reject", {}, format="json")
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_resp.json()["data"]["status"], "rejected")

    def test_approve_before_send_returns_409(self):
        response = self.client.post(f"/quotations/{self.quotation_id}/approve", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_send_twice_returns_409(self):
        self.client.post(f"/quotations/{self.quotation_id}/send", {}, format="json")
        second = self.client.post(f"/quotations/{self.quotation_id}/send", {}, format="json")
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)

    def test_send_cross_tenant_returns_404(self):
        quotation = Quotation.objects.create(
            company=self.company2, project=self.project_c2, client=self.client2,
            quote_number="QT-000001", version=1,
        )

        response = self.client.post(f"/quotations/{quotation.id}/send", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_send_fails_401(self):
        self.client.credentials()
        response = self.client.post(f"/quotations/{self.quotation_id}/send", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
