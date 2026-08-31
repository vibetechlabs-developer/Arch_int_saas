import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ProjectViewSetTestCase(TestCase):
    """
    Integration test suite for Project CRUD endpoints (BE-025).
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

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        resp_list = self.client.get("/projects")
        self.assertEqual(resp_list.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_create = self.client.post("/projects", {"name": "New Project"})
        self.assertEqual(resp_create.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_active_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_member_token}")
        response = self.client.get("/projects")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- List / Pagination -------------------------------------------------

    def test_list_projects_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["name"], "Kitchen Remodel")

    def test_list_projects_as_platform_admin_sees_all_companies(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get("/projects")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_empty_list_shape(self):
        Project.objects.filter(company=self.company1).delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects")

        data = response.json()
        self.assertEqual(data["data"], [])
        self.assertEqual(data["pagination"]["totalItems"], 0)

    def test_soft_deleted_project_excluded_from_list(self):
        self.project1.delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects")

        names = [p["name"] for p in response.json()["data"]]
        self.assertNotIn("Kitchen Remodel", names)

    # --- Create ----------------------------------------------------------

    def test_create_project_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "New Project", "clientId": str(self.client1.id)}
        response = self.client.post("/projects", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["name"], "New Project")
        self.assertEqual(data["companyId"], str(self.company1.id))
        self.assertEqual(data["status"], "draft")

    def test_create_project_as_platform_admin_with_explicit_company_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        payload = {
            "name": "Admin Created Project",
            "clientId": str(self.client2.id),
            "companyId": str(self.company2.id),
        }
        response = self.client.post("/projects", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["companyId"], str(self.company2.id))

    def test_create_project_cross_tenant_client_rejected(self):
        """
        A company member cannot create a project against another
        company's client by supplying its ID.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Cross Tenant Project", "clientId": str(self.client2.id)}
        response = self.client.post("/projects", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Project.objects.filter(name="Cross Tenant Project").exists())

    def test_create_project_company_injection_by_member_denied(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {
            "name": "Injected Project",
            "clientId": str(self.client1.id),
            "companyId": str(self.company2.id),
        }
        response = self.client.post("/projects", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Project.objects.filter(name="Injected Project").exists())

    def test_create_project_validation_error_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            "/projects", {"name": "   ", "clientId": str(self.client1.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_project_missing_client_id_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/projects", {"name": "No Client Project"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_project_status_field_ignored(self):
        """
        Confirms status isn't accepted as create input at all (not even
        silently) — Project_API.md's dedicated /status endpoint is BE-027.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {
            "name": "Attempted Status Project",
            "clientId": str(self.client1.id),
            "status": "completed",
        }
        response = self.client.post("/projects", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["status"], "draft")

    # --- Retrieve ----------------------------------------------------------

    def test_get_project_detail_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/projects/{self.project1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(self.project1.id))

    def test_cross_tenant_idor_get_project_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/projects/{self.project_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_cross_tenant_get_project_and_nonexistent_project_are_indistinguishable(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

        real_cross_tenant_response = self.client.get(f"/projects/{self.project_c2.id}")
        nonexistent_response = self.client.get(f"/projects/{uuid.uuid4()}")

        self.assertEqual(real_cross_tenant_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_platform_admin_can_retrieve_any_tenant_project(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get(f"/projects/{self.project_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Update ----------------------------------------------------------

    def test_update_project_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Renamed Project", "priority": "High"}
        response = self.client.patch(f"/projects/{self.project1.id}", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["name"], "Renamed Project")
        self.assertEqual(data["priority"], "High")

    def test_put_behaves_like_partial_update(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.put(f"/projects/{self.project1.id}", {"priority": "Low"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["priority"], "Low")
        self.assertEqual(data["name"], "Kitchen Remodel")

    def test_update_project_status_field_ignored(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/projects/{self.project1.id}", {"status": "completed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["status"], "draft")

    def test_update_project_client_field_ignored(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/projects/{self.project1.id}", {"clientId": str(self.client2.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["clientId"], str(self.client1.id))

    def test_cross_tenant_idor_patch_project_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/projects/{self.project_c2.id}", {"name": "Hacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.project_c2.refresh_from_db()
        self.assertEqual(self.project_c2.name, "Office Fitout")

    # --- Delete ----------------------------------------------------------

    def test_delete_project_soft_deletes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/projects/{self.project1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        get_resp = self.client.get(f"/projects/{self.project1.id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_idor_delete_project_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/projects/{self.project_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.project_c2.refresh_from_db()
        self.assertFalse(self.project_c2.is_deleted)

    def test_platform_admin_can_delete_any_tenant_project(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.delete(f"/projects/{self.project_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
