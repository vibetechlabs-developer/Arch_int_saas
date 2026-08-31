import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.boq.models import BOQ, BOQSection
from apps.boq.services import BOQSectionService, BOQService
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project
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
