import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.leads.models import Lead
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class LeadViewSetTestCase(TestCase):
    """
    Integration test suite for Lead CRUD endpoints (BE-061), mirroring
    apps.clients.tests.test_views.ClientViewSetTestCase's structure.
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

        self.revoked_user = User.objects.create_user(
            email="carol@company1.com", name="Carol Revoked", password="StrongPassword123!"
        )
        self.revoked_token = str(CompanyUserAccessToken.for_user(self.revoked_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(self.company1, self.member_user)
        CompanyMembership.objects.create(
            company=self.company1, user=self.revoked_user, status=CompanyMembershipStatus.REVOKED
        )

        self.lead1 = Lead.objects.create(company=self.company1, name="Jane Prospect", email="jane@example.com")
        self.lead2 = Lead.objects.create(
            company=self.company1, name="Prospect Interiors", company_name="Prospect Interiors"
        )
        self.lead_c2 = Lead.objects.create(company=self.company2, name="John Other")

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        resp_list = self.client.get("/leads")
        self.assertEqual(resp_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp_list.json()["error"]["code"], "AUTHENTICATION_ERROR")

        resp_create = self.client.post("/leads", {"name": "New Lead"})
        self.assertEqual(resp_create.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_detail = self.client.get(f"/leads/{self.lead1.id}")
        self.assertEqual(resp_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_active_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_member_token}")
        response = self.client.get("/leads")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        resp_create = self.client.post("/leads", {"name": "Test Lead"})
        self.assertEqual(resp_create.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_revoked_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.revoked_token}")
        response = self.client.get("/leads")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- List / Search / Ordering / Pagination --------------------------

    def test_list_leads_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/leads")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("pagination", data)
        self.assertEqual(len(data["data"]), 2)
        names = [lead["name"] for lead in data["data"]]
        self.assertIn("Jane Prospect", names)
        self.assertIn("Prospect Interiors", names)
        self.assertNotIn("John Other", names)

    def test_list_leads_as_platform_admin_sees_all_companies(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get("/leads")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 3)

    def test_search_leads(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/leads?search=Interiors")

        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Prospect Interiors")

    def test_filter_leads_by_status(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/leads?status=new")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_invalid_ordering_query_param_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/leads?ordering=not_a_real_field")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_empty_list_shape(self):
        Lead.objects.filter(company=self.company1).delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/leads")

        data = response.json()
        self.assertEqual(data["data"], [])
        self.assertEqual(data["pagination"]["totalItems"], 0)

    def test_soft_deleted_lead_excluded_from_list(self):
        self.lead1.delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/leads")

        names = [lead["name"] for lead in response.json()["data"]]
        self.assertNotIn("Jane Prospect", names)

    # --- Create ----------------------------------------------------------

    def test_create_lead_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "New Lead", "email": "new@example.com", "mobile": "9999999999", "source": "website"}
        response = self.client.post("/leads", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["name"], "New Lead")
        self.assertEqual(data["data"]["companyId"], str(self.company1.id))
        self.assertEqual(data["data"]["status"], "new")
        self.assertIn("requestId", data)

    def test_create_lead_as_platform_admin_with_explicit_company_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        payload = {"name": "Admin Created Lead", "companyId": str(self.company2.id)}
        response = self.client.post("/leads", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["companyId"], str(self.company2.id))

    def test_create_lead_platform_admin_without_company_id_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.post("/leads", {"name": "No Company Lead"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lead_company_injection_by_member_denied(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Injected Lead", "companyId": str(self.company2.id)}
        response = self.client.post("/leads", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Lead.objects.filter(name="Injected Lead").exists())

    def test_create_lead_validation_error_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/leads", {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_create_lead_invalid_email_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            "/leads", {"name": "Bad Email Lead", "email": "not-an-email"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_lead_with_assignee_not_a_member_returns_400(self):
        outsider = User.objects.create_user(
            email="outsider2@example.com", name="Outsider Two", password="StrongPassword123!"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            "/leads", {"name": "Bad Assignee Lead", "assignedToId": str(outsider.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Retrieve ----------------------------------------------------------

    def test_get_lead_detail_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/leads/{self.lead1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], str(self.lead1.id))
        self.assertEqual(data["name"], "Jane Prospect")

    def test_cross_tenant_idor_get_lead_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/leads/{self.lead_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    def test_cross_tenant_get_lead_and_nonexistent_lead_are_indistinguishable(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

        real_cross_tenant_response = self.client.get(f"/leads/{self.lead_c2.id}")
        nonexistent_response = self.client.get(f"/leads/{uuid.uuid4()}")

        self.assertEqual(real_cross_tenant_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            real_cross_tenant_response.json()["error"]["code"],
            nonexistent_response.json()["error"]["code"],
        )

    def test_platform_admin_can_retrieve_any_tenant_lead(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get(f"/leads/{self.lead_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Update ----------------------------------------------------------

    def test_update_lead_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Jane Updated", "mobile": "8888888888"}
        response = self.client.patch(f"/leads/{self.lead1.id}", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["name"], "Jane Updated")
        self.assertEqual(data["mobile"], "8888888888")

    def test_update_lead_cannot_set_status_directly(self):
        """The plain update endpoint has no `status` field — status only moves via /status, /mark-lost, /convert."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/leads/{self.lead1.id}", {"status": "won"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lead1.refresh_from_db()
        self.assertEqual(self.lead1.status, "new")

    def test_put_behaves_like_partial_update(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.put(f"/leads/{self.lead1.id}", {"mobile": "7777777777"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["mobile"], "7777777777")
        self.assertEqual(data["name"], "Jane Prospect")

    def test_cross_tenant_idor_patch_lead_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/leads/{self.lead_c2.id}", {"name": "Hacked Name"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.lead_c2.refresh_from_db()
        self.assertEqual(self.lead_c2.name, "John Other")

    def test_platform_admin_can_update_any_tenant_lead(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.patch(
            f"/leads/{self.lead_c2.id}", {"name": "Admin Edited"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "Admin Edited")

    # --- Delete ----------------------------------------------------------

    def test_delete_lead_soft_deletes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/leads/{self.lead1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])

        get_resp = self.client.get(f"/leads/{self.lead1.id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

        self.lead1.refresh_from_db()
        self.assertTrue(self.lead1.is_deleted)

    def test_cross_tenant_idor_delete_lead_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/leads/{self.lead_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.lead_c2.refresh_from_db()
        self.assertFalse(self.lead_c2.is_deleted)

    def test_platform_admin_can_delete_any_tenant_lead(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.delete(f"/leads/{self.lead_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])
