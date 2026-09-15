from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.leads.models import Lead, LeadStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus
from apps.users.services import RoleService

User = get_user_model()


class LeadStatusEndpointTestCase(TestCase):
    """
    Integration tests for PATCH /leads/{id}/status (BE-061), mirroring
    apps.projects.tests.test_workflow.ProjectStatusEndpointTestCase.
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(self.company1, self.member_user)

        self.lead1 = Lead.objects.create(company=self.company1, name="Jane Prospect")
        self.lead_c2 = Lead.objects.create(company=self.company2, name="John Other")

    def _url(self, lead_id):
        return f"/leads/{lead_id}/status"

    def test_unauthenticated_401(self):
        response = self.client.patch(self._url(self.lead1.id), {"status": "qualified"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_transition_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(self._url(self.lead1.id), {"status": "qualified"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["status"], "qualified")

    def test_invalid_skip_ahead_returns_409(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._url(self.lead1.id), {"status": "site_visit_scheduled"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_won_via_status_endpoint_returns_409(self):
        """WON must never be reachable except through /convert."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(self._url(self.lead1.id), {"status": "won"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_garbage_status_value_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._url(self.lead1.id), {"status": "not-a-real-status"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_status_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(self._url(self.lead1.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_lead_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._url(self.lead_c2.id), {"status": "qualified"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_full_forward_chain(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        for target in ("qualified", "follow_up", "site_visit_scheduled"):
            response = self.client.patch(self._url(self.lead1.id), {"status": target}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["data"]["status"], target)


class LeadMarkLostEndpointTestCase(TestCase):
    """Integration tests for POST /leads/{id}/mark-lost (BE-061)."""

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.lead1 = Lead.objects.create(company=self.company1, name="Jane Prospect")

    def _url(self, lead_id):
        return f"/leads/{lead_id}/mark-lost"

    def test_mark_lost_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._url(self.lead1.id), {"lossReason": "Chose a competitor"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["status"], "lost")
        self.assertEqual(data["lossReason"], "Chose a competitor")

    def test_mark_lost_missing_reason_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(self.lead1.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_lost_blank_reason_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(self.lead1.id), {"lossReason": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_lost_with_follow_up_reminder(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._url(self.lead1.id),
            {"lossReason": "Budget too low", "followUpReminderAt": "2027-01-01T00:00:00Z"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.json()["data"]["followUpReminderAt"])

    def test_mark_lost_already_lost_returns_409(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.post(self._url(self.lead1.id), {"lossReason": "First"}, format="json")
        response = self.client.post(self._url(self.lead1.id), {"lossReason": "Second"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class LeadConvertEndpointTestCase(TestCase):
    """Integration tests for POST /leads/{id}/convert (BE-061)."""

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.lead1 = Lead.objects.create(company=self.company1, name="Jane Prospect", email="jane@example.com")

    def _url(self, lead_id):
        return f"/leads/{lead_id}/convert"

    def test_convert_creates_client_only_by_default(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(self.lead1.id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["status"], "won")
        self.assertIsNotNone(data["convertedClientId"])
        self.assertIsNone(data["convertedProjectId"])

        client = Client.objects.get(id=data["convertedClientId"])
        self.assertEqual(client.name, "Jane Prospect")

    def test_convert_with_create_project_true(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._url(self.lead1.id), {"createProject": True, "projectName": "New Kitchen"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIsNotNone(data["convertedProjectId"])
        self.assertEqual(data["convertedProjectName"], "New Kitchen")

    def test_convert_is_idempotent_via_api(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        first_response = self.client.post(self._url(self.lead1.id), {}, format="json")
        second_response = self.client.post(self._url(self.lead1.id), {}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            first_response.json()["data"]["convertedClientId"],
            second_response.json()["data"]["convertedClientId"],
        )
        self.assertEqual(Client.objects.filter(company=self.company1).count(), 1)

    def test_convert_lost_lead_returns_409(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.post(f"/leads/{self.lead1.id}/mark-lost", {"lossReason": "No budget"}, format="json")

        response = self.client.post(self._url(self.lead1.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class LeadGranularRbacTestCase(TestCase):
    """
    RBAC granularity tests (BE-061): a "Sales / CRM User"-style role
    (view/create/edit/convert, no delete) can convert leads but is
    forbidden from deleting them — verifying `lead.convert` is a
    distinct, independently-enforced permission code from `lead.delete`.
    """

    def setUp(self):
        self.client = APIClient()

        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)

        self.sales_role = RoleService.create_role(company_id=self.company.id, name="Sales Rep Role")
        RoleService.assign_permissions(
            role_id=self.sales_role.id,
            codes=["lead.view", "lead.create", "lead.edit", "lead.convert"],
        )

        self.sales_user = User.objects.create_user(
            email="sales@company1.com", name="Sales Rep", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.sales_user,
            role=self.sales_role,
            status=CompanyMembershipStatus.ACTIVE,
        )
        self.sales_token = str(CompanyUserAccessToken.for_user(self.sales_user))

        self.lead1 = Lead.objects.create(company=self.company, name="Jane Prospect")

    def test_sales_role_can_convert(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.sales_token}")
        response = self.client.post(f"/leads/{self.lead1.id}/convert", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sales_role_can_transition_status(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.sales_token}")
        response = self.client.patch(f"/leads/{self.lead1.id}/status", {"status": "qualified"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sales_role_cannot_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.sales_token}")
        response = self.client.delete(f"/leads/{self.lead1.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.lead1.refresh_from_db()
        self.assertFalse(self.lead1.is_deleted)

    def test_role_without_convert_code_cannot_convert(self):
        no_convert_role = RoleService.create_role(company_id=self.company.id, name="View Only Role")
        RoleService.assign_permissions(role_id=no_convert_role.id, codes=["lead.view", "lead.edit"])

        limited_user = User.objects.create_user(
            email="limited@company1.com", name="Limited User", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company, user=limited_user, role=no_convert_role, status=CompanyMembershipStatus.ACTIVE
        )
        limited_token = str(CompanyUserAccessToken.for_user(limited_user))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {limited_token}")
        response = self.client.post(f"/leads/{self.lead1.id}/convert", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SeededDefaultRoleLeadPermissionTestCase(TestCase):
    """
    Verifies the DEFAULT_ROLE_PERMISSIONS extension for Admin/Sales-CRM-User
    (BE-061) — new companies seeded after this migration get the lead.*
    codes on those roles automatically via RoleService.seed_default_roles_for_company.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Fresh Co", status=CompanyStatus.ACTIVE)
        RoleService.seed_default_roles_for_company(self.company)

    def test_admin_role_gets_all_lead_codes(self):
        from apps.users.models import Role
        from apps.users.repositories import PermissionRepository

        admin_role = Role.objects.get(company=self.company, name="Admin")
        codes = PermissionRepository.codes_for_role(admin_role.id)
        for code in ("lead.view", "lead.create", "lead.edit", "lead.delete", "lead.convert"):
            self.assertIn(code, codes)

    def test_sales_role_gets_lead_codes_but_not_delete(self):
        from apps.users.models import Role
        from apps.users.repositories import PermissionRepository

        sales_role = Role.objects.get(company=self.company, name="Sales / CRM User")
        codes = PermissionRepository.codes_for_role(sales_role.id)
        for code in ("lead.view", "lead.create", "lead.edit", "lead.convert"):
            self.assertIn(code, codes)
        self.assertNotIn("lead.delete", codes)
