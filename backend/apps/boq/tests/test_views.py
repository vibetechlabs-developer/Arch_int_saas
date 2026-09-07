import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.boq.models import BOQ, BOQSection
from apps.boq.services import BOQItemService, BOQSectionService, BOQService
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.products.models import Product, ProductCategory, ProductSubcategory, ProductUnit
from apps.projects.models import Project
from apps.common.test_utils import make_full_access_membership
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class BOQViewTestCase(TestCase):
    """
    Integration test suite for BOQ/BOQSection endpoints (BE-035).
    """

    def setUp(self):
        self.client = APIClient()

        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com", name="Super Admin", password="StrongPassword123!"
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.non_member_user = User.objects.create_user(
            email="bob@outsider.com", name="Bob Outsider", password="StrongPassword123!"
        )
        self.non_member_token = str(CompanyUserAccessToken.for_user(self.non_member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project_c2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

    def _boq_url(self, project_id):
        return f"/projects/{project_id}/boq"

    def _section_list_url(self, project_id):
        return f"/projects/{project_id}/boq/sections"

    def _section_detail_url(self, section_id):
        return f"/boq-sections/{section_id}"

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        response = self.client.get(self._boq_url(self.project1.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_member_denied_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_member_token}")
        response = self.client.get(self._boq_url(self.project1.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_tenant_project_returns_404_not_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(self._boq_url(self.project_c2.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Get / Auto-create -------------------------------------------------

    def test_get_boq_auto_creates_on_first_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.assertFalse(BOQ.objects.filter(project=self.project1).exists())

        response = self.client.get(self._boq_url(self.project1.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["projectId"], str(self.project1.id))
        self.assertEqual(data["sections"], [])
        self.assertTrue(BOQ.objects.filter(project=self.project1).exists())

    def test_get_boq_is_idempotent(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.get(self._boq_url(self.project1.id))
        self.client.get(self._boq_url(self.project1.id))
        self.assertEqual(BOQ.objects.filter(project=self.project1).count(), 1)

    def test_platform_admin_can_access_cross_tenant_boq(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get(self._boq_url(self.project_c2.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Sections: create ----------------------------------------------------

    def test_create_section_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._section_list_url(self.project1.id), {"name": "Flooring"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["name"], "Flooring")
        self.assertEqual(data["sortOrder"], 1)

    def test_create_section_appears_in_boq_tree(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.post(self._section_list_url(self.project1.id), {"name": "Flooring"}, format="json")

        response = self.client.get(self._boq_url(self.project1.id))
        sections = response.json()["data"]["sections"]
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["name"], "Flooring")

    def test_create_section_validation_error_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._section_list_url(self.project1.id), {"name": "   "}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_section_cross_tenant_project_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._section_list_url(self.project_c2.id), {"name": "Injected"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Sections: retrieve/update/delete (flat) ------------------------------

    def test_update_section_success(self):
        boq = BOQService.get_or_create_boq_for_project(self.project1)
        section = BOQSectionService.create_section(boq=boq, name="Flooring")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._section_detail_url(section.id), {"name": "Renamed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "Renamed")

    def test_cross_tenant_idor_patch_section_fails(self):
        boq2 = BOQService.get_or_create_boq_for_project(self.project_c2)
        section = BOQSectionService.create_section(boq=boq2, name="Other Company Section")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._section_detail_url(section.id), {"name": "Hacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        section.refresh_from_db()
        self.assertEqual(section.name, "Other Company Section")

    def test_delete_section_soft_deletes(self):
        boq = BOQService.get_or_create_boq_for_project(self.project1)
        section = BOQSectionService.create_section(boq=boq, name="Flooring")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(self._section_detail_url(section.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        section.refresh_from_db()
        self.assertTrue(section.is_deleted)

    def test_cross_tenant_idor_delete_section_fails(self):
        boq2 = BOQService.get_or_create_boq_for_project(self.project_c2)
        section = BOQSectionService.create_section(boq=boq2, name="Other Company Section")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(self._section_detail_url(section.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        section.refresh_from_db()
        self.assertFalse(section.is_deleted)

    def test_delete_section_blocked_by_active_item_returns_409(self):
        boq = BOQService.get_or_create_boq_for_project(self.project1)
        section = BOQSectionService.create_section(boq=boq, name="Flooring")
        BOQItemService.create_item(
            section=section, description="Custom", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("10.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(self._section_detail_url(section.id))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        section.refresh_from_db()
        self.assertFalse(section.is_deleted)


class BOQItemViewTestCase(TestCase):
    """
    Integration test suite for BOQItem endpoints (BE-036).
    """

    def setUp(self):
        self.client = APIClient()

        self.superadmin = User.objects.create_superuser(
            email="superadmin2@example.com", name="Super Admin", password="StrongPassword123!"
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        self.member_user = User.objects.create_user(
            email="alice2@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project_other1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Second Project"
        )
        self.project_c2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

        self.boq1 = BOQService.get_or_create_boq_for_project(self.project1)
        self.section1 = BOQSectionService.create_section(boq=self.boq1, name="Flooring")

        self.boq_other1 = BOQService.get_or_create_boq_for_project(self.project_other1)
        self.section_other1 = BOQSectionService.create_section(
            boq=self.boq_other1, name="Sibling Project Section"
        )

        self.boq_c2 = BOQService.get_or_create_boq_for_project(self.project_c2)
        self.section_c2 = BOQSectionService.create_section(boq=self.boq_c2, name="Other Company")

        self.category = ProductCategory.objects.create(company=self.company1, name="Flooring")
        self.subcategory = ProductSubcategory.objects.create(
            company=self.company1, category=self.category, name="Tiles"
        )
        self.product = Product.objects.create(
            company=self.company1,
            subcategory=self.subcategory,
            name="Ceramic Tile",
            unit=ProductUnit.SQFT,
            default_selling_rate=Decimal("120.00"),
        )

    def _list_url(self, project_id, section_id):
        return f"/projects/{project_id}/boq/sections/{section_id}/items"

    def _detail_url(self, item_id):
        return f"/boq-items/{item_id}"

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        response = self.client.post(self._list_url(self.project1.id, self.section1.id), {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cross_tenant_project_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._list_url(self.project_c2.id, self.section_c2.id),
            {"description": "Injected", "quantity": "1.00", "unit": "job", "rate": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_section_from_sibling_project_returns_404(self):
        """
        A section that belongs to the SAME company but a DIFFERENT
        project must not be reachable through this project's URL.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._list_url(self.project1.id, self.section_other1.id),
            {"description": "Injected", "quantity": "1.00", "unit": "job", "rate": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Create --------------------------------------------------------------

    def test_create_free_text_item_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {
            "description": "Custom flooring work",
            "quantity": "10.00",
            "unit": "sqft",
            "rate": "50.00",
        }
        response = self.client.post(
            self._list_url(self.project1.id, self.section1.id), payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["description"], "Custom flooring work")
        self.assertEqual(data["amount"], "500.00")

    def test_create_item_with_product_inherits_defaults(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"productId": str(self.product.id), "quantity": "5.00"}
        response = self.client.post(
            self._list_url(self.project1.id, self.section1.id), payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["description"], "Ceramic Tile")
        self.assertEqual(data["unit"], "sqft")
        self.assertEqual(data["rate"], "120.00")
        self.assertEqual(data["amount"], "600.00")

    def test_create_item_missing_description_and_product_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._list_url(self.project1.id, self.section1.id),
            {"quantity": "1.00", "unit": "job", "rate": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_item_appears_in_boq_tree(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.post(
            self._list_url(self.project1.id, self.section1.id),
            {"description": "Custom", "quantity": "1.00", "unit": "job", "rate": "1.00"},
            format="json",
        )

        response = self.client.get(f"/projects/{self.project1.id}/boq")
        items = response.json()["data"]["sections"][0]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["description"], "Custom")

    # --- Update / Delete (flat) --------------------------------------------

    def test_update_item_recomputes_amount(self):
        item = BOQItemService.create_item(
            section=self.section1, description="Custom", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("10.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._detail_url(item.id), {"quantity": "3.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["amount"], "30.00")

    def test_cross_tenant_idor_patch_item_fails(self):
        item = BOQItemService.create_item(
            section=self.section_c2, description="Other Company Item", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("1.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._detail_url(item.id), {"description": "Hacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        item.refresh_from_db()
        self.assertEqual(item.description, "Other Company Item")

    def test_delete_item_soft_deletes(self):
        item = BOQItemService.create_item(
            section=self.section1, description="Custom", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("1.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(self._detail_url(item.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.is_deleted)

    def test_cross_tenant_idor_delete_item_fails(self):
        item = BOQItemService.create_item(
            section=self.section_c2, description="Other Company Item", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("1.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(self._detail_url(item.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        item.refresh_from_db()
        self.assertFalse(item.is_deleted)
