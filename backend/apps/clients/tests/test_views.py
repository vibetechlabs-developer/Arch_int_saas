import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ClientViewSetTestCase(TestCase):
    """
    Integration test suite for Client CRUD endpoints (BE-023).
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

        self.client1 = Client.objects.create(
            company=self.company1, name="Jane Doe", email="jane@example.com"
        )
        self.client2 = Client.objects.create(
            company=self.company1, name="Interior Designs Ltd", company_name="Interior Designs Ltd"
        )
        self.client_c2 = Client.objects.create(company=self.company2, name="John Smith")

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        resp_list = self.client.get("/clients")
        self.assertEqual(resp_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp_list.json()["error"]["code"], "AUTHENTICATION_ERROR")

        resp_create = self.client.post("/clients", {"name": "New Client"})
        self.assertEqual(resp_create.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_detail = self.client.get(f"/clients/{self.client1.id}")
        self.assertEqual(resp_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_active_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_member_token}")
        response = self.client.get("/clients")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        resp_create = self.client.post("/clients", {"name": "Test Client"})
        self.assertEqual(resp_create.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_revoked_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.revoked_token}")
        response = self.client.get("/clients")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- List / Search / Ordering / Pagination --------------------------

    def test_list_clients_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("pagination", data)
        self.assertEqual(len(data["data"]), 2)
        names = [c["name"] for c in data["data"]]
        self.assertIn("Jane Doe", names)
        self.assertIn("Interior Designs Ltd", names)
        self.assertNotIn("John Smith", names)

    def test_list_clients_as_platform_admin_sees_all_companies(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get("/clients")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 3)

    def test_search_clients(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients?search=Interior")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Interior Designs Ltd")

    def test_search_clients_by_email(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients?search=jane@example.com")

        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Jane Doe")

    def test_ordering_clients(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients?ordering=name")

        names = [c["name"] for c in response.json()["data"]]
        self.assertEqual(names, sorted(names))

    def test_invalid_ordering_query_param_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients?ordering=not_a_real_field")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_pagination_page_size(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients?pageSize=1")

        data = response.json()
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["pagination"]["pageSize"], 1)
        self.assertEqual(data["pagination"]["totalItems"], 2)
        self.assertEqual(data["pagination"]["totalPages"], 2)

    def test_empty_list_shape(self):
        Client.objects.filter(company=self.company1).delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients")

        data = response.json()
        self.assertEqual(data["data"], [])
        self.assertEqual(data["pagination"]["totalItems"], 0)

    def test_soft_deleted_client_excluded_from_list(self):
        self.client1.delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/clients")

        names = [c["name"] for c in response.json()["data"]]
        self.assertNotIn("Jane Doe", names)

    # --- Create ----------------------------------------------------------

    def test_create_client_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "New Client", "email": "new@example.com", "mobile": "9999999999"}
        response = self.client.post("/clients", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["name"], "New Client")
        self.assertEqual(data["data"]["companyId"], str(self.company1.id))
        self.assertIn("requestId", data)

    def test_create_client_as_platform_admin_with_explicit_company_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        payload = {"name": "Admin Created Client", "companyId": str(self.company2.id)}
        response = self.client.post("/clients", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["companyId"], str(self.company2.id))

    def test_create_client_platform_admin_without_company_id_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.post("/clients", {"name": "No Company Client"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_client_company_injection_by_member_denied(self):
        """
        A company member cannot create a client in another company by
        supplying a mismatched companyId.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Injected Client", "companyId": str(self.company2.id)}
        response = self.client.post("/clients", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Client.objects.filter(name="Injected Client").exists())

    def test_create_client_validation_error_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/clients", {"name": "   "}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_create_client_invalid_email_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            "/clients", {"name": "Bad Email Client", "email": "not-an-email"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_client_addresses_must_be_list(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            "/clients",
            {"name": "Bad Addresses Client", "addresses": {"not": "a list"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Retrieve ----------------------------------------------------------

    def test_get_client_detail_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/clients/{self.client1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], str(self.client1.id))
        self.assertEqual(data["name"], "Jane Doe")

    def test_cross_tenant_idor_get_client_fails(self):
        """
        Error_Handling.md §5: cross-tenant access returns 404, not 403.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/clients/{self.client_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    def test_cross_tenant_get_client_and_nonexistent_client_are_indistinguishable(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

        real_cross_tenant_response = self.client.get(f"/clients/{self.client_c2.id}")
        nonexistent_response = self.client.get(f"/clients/{uuid.uuid4()}")

        self.assertEqual(real_cross_tenant_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            real_cross_tenant_response.json()["error"]["code"],
            nonexistent_response.json()["error"]["code"],
        )

    def test_platform_admin_can_retrieve_any_tenant_client(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get(f"/clients/{self.client_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Update ----------------------------------------------------------

    def test_update_client_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Jane Updated", "mobile": "8888888888"}
        response = self.client.patch(f"/clients/{self.client1.id}", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["name"], "Jane Updated")
        self.assertEqual(data["mobile"], "8888888888")

    def test_put_behaves_like_partial_update(self):
        """
        BE-023 decision #14: PUT mirrors PATCH semantics, matching the
        existing RoleViewSet convention — not a distinct full-replace PUT.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.put(f"/clients/{self.client1.id}", {"mobile": "7777777777"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["mobile"], "7777777777")
        # Fields not sent must survive unchanged, proving this isn't a
        # full-replace PUT.
        self.assertEqual(data["name"], "Jane Doe")

    def test_cross_tenant_idor_patch_client_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/clients/{self.client_c2.id}", {"name": "Hacked Name"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.client_c2.refresh_from_db()
        self.assertEqual(self.client_c2.name, "John Smith")

    def test_platform_admin_can_update_any_tenant_client(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.patch(
            f"/clients/{self.client_c2.id}", {"name": "Admin Edited"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "Admin Edited")

    # --- Delete ----------------------------------------------------------

    def test_delete_client_soft_deletes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/clients/{self.client1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])

        get_resp = self.client.get(f"/clients/{self.client1.id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

        self.client1.refresh_from_db()
        self.assertTrue(self.client1.is_deleted)

    def test_cross_tenant_idor_delete_client_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/clients/{self.client_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.client_c2.refresh_from_db()
        self.assertFalse(self.client_c2.is_deleted)

    def test_platform_admin_can_delete_any_tenant_client(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.delete(f"/clients/{self.client_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])
