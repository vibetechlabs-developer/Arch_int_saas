import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.leads.models import Lead
from apps.projects.models import Project
from apps.site_visits.models import SiteVisit
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class SiteVisitViewSetTestCase(TestCase):
    """
    Integration test suite for Site Visit CRUD endpoints (BE-062), mirroring
    apps.leads.tests.test_views.LeadViewSetTestCase's structure.
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

        self.client_obj = Client.objects.create(company=self.company1, name="Jane Client")
        self.project = Project.objects.create(company=self.company1, client=self.client_obj, name="Kitchen Remodel")
        self.lead = Lead.objects.create(company=self.company1, name="Jane Prospect")

        self.client_c2 = Client.objects.create(company=self.company2, name="Other Client")
        self.project_c2 = Project.objects.create(company=self.company2, client=self.client_c2, name="Other Project")

        self.visit_date = (timezone.now() + timedelta(days=2)).isoformat()

        self.visit1 = SiteVisit.objects.create(
            company=self.company1, project=self.project, visit_date=timezone.now() + timedelta(days=1)
        )
        self.visit_c2 = SiteVisit.objects.create(
            company=self.company2, project=self.project_c2, visit_date=timezone.now() + timedelta(days=1)
        )

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        resp_list = self.client.get("/site-visits")
        self.assertEqual(resp_list.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_create = self.client.post("/site-visits", {"projectId": str(self.project.id), "visitDate": self.visit_date})
        self.assertEqual(resp_create.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_active_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_member_token}")
        response = self.client.get("/site-visits")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- List --------------------------------------------------------

    def test_list_site_visits_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/site-visits")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["id"], str(self.visit1.id))

    def test_list_site_visits_as_platform_admin_sees_all_companies(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get("/site-visits")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_filter_site_visits_by_project(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/site-visits?project={self.project.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_invalid_ordering_query_param_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/site-visits?ordering=not_a_real_field")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Create ----------------------------------------------------------

    def test_create_site_visit_against_project_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"projectId": str(self.project.id), "visitDate": self.visit_date, "address": "221B Baker St"}
        response = self.client.post("/site-visits", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["projectId"], str(self.project.id))
        self.assertEqual(data["clientId"], str(self.client_obj.id))
        self.assertEqual(data["address"], "221B Baker St")

    def test_create_site_visit_against_lead(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"leadId": str(self.lead.id), "visitDate": self.visit_date}
        response = self.client.post("/site-visits", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["leadId"], str(self.lead.id))
        self.assertIsNone(data["clientId"])

    def test_create_site_visit_neither_lead_nor_project_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/site-visits", {"visitDate": self.visit_date}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_site_visit_missing_visit_date_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/site-visits", {"projectId": str(self.project.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_site_visit_cross_tenant_project_returns_400_or_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            "/site-visits", {"projectId": str(self.project_c2.id), "visitDate": self.visit_date}, format="json"
        )
        self.assertIn(response.status_code, (status.HTTP_404_NOT_FOUND,))

    def test_create_site_visit_invalid_photo_urls_type_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            "/site-visits",
            {"projectId": str(self.project.id), "visitDate": self.visit_date, "photoUrls": "not-a-list"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Retrieve ----------------------------------------------------------

    def test_get_site_visit_detail_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/site-visits/{self.visit1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(self.visit1.id))

    def test_cross_tenant_idor_get_site_visit_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/site-visits/{self.visit_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_cross_tenant_and_nonexistent_site_visit_are_indistinguishable(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

        real_cross_tenant_response = self.client.get(f"/site-visits/{self.visit_c2.id}")
        nonexistent_response = self.client.get(f"/site-visits/{uuid.uuid4()}")

        self.assertEqual(real_cross_tenant_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Update ----------------------------------------------------------

    def test_update_site_visit_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(f"/site-visits/{self.visit1.id}", {"address": "New Address"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["address"], "New Address")

    def test_cross_tenant_idor_patch_site_visit_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(f"/site-visits/{self.visit_c2.id}", {"address": "Hacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_site_visit_cannot_set_project_directly(self):
        """The plain update endpoint has no projectId/leadId field — those are only set at creation."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/site-visits/{self.visit1.id}", {"projectId": str(self.project_c2.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.visit1.refresh_from_db()
        self.assertEqual(self.visit1.project_id, self.project.id)

    # --- Delete ----------------------------------------------------------

    def test_delete_site_visit_soft_deletes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/site-visits/{self.visit1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        get_resp = self.client.get(f"/site-visits/{self.visit1.id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_idor_delete_site_visit_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/site-visits/{self.visit_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
