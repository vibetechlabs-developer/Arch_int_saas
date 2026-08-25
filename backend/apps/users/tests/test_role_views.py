import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role

User = get_user_model()


class RoleViewSetTestCase(TestCase):
    """
    Integration test suite for Role CRUD endpoints (BE-014).
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Platform Super Admin User
        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com",
            name="Super Admin",
            password="StrongPassword123!",
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        # 2. Company Member User (Company 1)
        self.member_user = User.objects.create_user(
            email="alice@company1.com",
            name="Alice Member",
            password="StrongPassword123!",
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        # 3. Non-Member User
        self.non_member_user = User.objects.create_user(
            email="bob@outsider.com",
            name="Bob Outsider",
            password="StrongPassword123!",
        )
        self.non_member_token = str(CompanyUserAccessToken.for_user(self.non_member_user))

        # 4. Companies
        self.company1 = Company.objects.create(
            name="Studio One",
            status=CompanyStatus.ACTIVE,
        )
        self.company2 = Company.objects.create(
            name="Studio Two",
            status=CompanyStatus.ACTIVE,
        )

        # 5. Memberships
        CompanyMembership.objects.create(
            company=self.company1,
            user=self.member_user,
            status=CompanyMembershipStatus.ACTIVE,
        )

        # 6. Roles
        self.role1 = Role.objects.create(
            company=self.company1,
            name="Architect",
            description="Designs blueprints",
            is_active=True,
        )
        self.role2 = Role.objects.create(
            company=self.company1,
            name="Draftsman",
            description="Drafts technical drawings",
            is_active=False,
        )
        self.role_c2 = Role.objects.create(
            company=self.company2,
            name="Structural Engineer",
            description="Calculates loads",
            is_active=True,
        )

    def test_unauthenticated_requests_fail_401(self):
        """
        Verify unauthenticated requests to /roles fail with 401.
        """
        resp_list = self.client.get("/roles")
        self.assertEqual(resp_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp_list.json()["error"]["code"], "AUTHENTICATION_ERROR")

        resp_create = self.client.post("/roles", {"name": "New Role"})
        self.assertEqual(resp_create.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_detail = self.client.get(f"/roles/{self.role1.id}")
        self.assertEqual(resp_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_roles_as_company_member(self):
        """
        Verify company member lists roles scoped strictly to their active company.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/roles")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("pagination", data)
        # Should see company1's 2 roles, but NOT company2's role
        self.assertEqual(len(data["data"]), 2)
        role_names = [r["name"] for r in data["data"]]
        self.assertIn("Architect", role_names)
        self.assertIn("Draftsman", role_names)
        self.assertNotIn("Structural Engineer", role_names)

    def test_list_roles_as_platform_admin(self):
        """
        Verify platform admin can list all roles across companies.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get("/roles")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 3)

    def test_list_roles_filtering_and_search(self):
        """
        Verify isActive filtering, search query, and pagination parameters.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

        # Filter by isActive=true
        resp_active = self.client.get("/roles?isActive=true")
        self.assertEqual(resp_active.status_code, status.HTTP_200_OK)
        data_active = resp_active.json()["data"]
        self.assertEqual(len(data_active), 1)
        self.assertEqual(data_active[0]["name"], "Architect")

        # Search by keyword
        resp_search = self.client.get("/roles?search=Drafts")
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        data_search = resp_search.json()["data"]
        self.assertEqual(len(data_search), 1)
        self.assertEqual(data_search[0]["name"], "Draftsman")

    def test_create_role_as_company_member(self):
        """
        Verify company member can create a role for their company (201 Created).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {
            "name": "3D Modeler",
            "description": "Builds 3D renderings",
            "isActive": True,
        }
        response = self.client.post("/roles", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["name"], "3D Modeler")
        self.assertEqual(data["data"]["companyId"], str(self.company1.id))
        self.assertEqual(data["data"]["companyName"], "Studio One")
        self.assertTrue(data["data"]["isActive"])
        self.assertIn("requestId", data)

    def test_create_role_as_platform_admin_with_explicit_company_id(self):
        """
        Verify Platform Admin can create a role by providing companyId in body.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        payload = {
            "name": "BIM Specialist",
            "description": "Manages building information modeling",
            "companyId": str(self.company2.id),
        }
        response = self.client.post("/roles", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["data"]["name"], "BIM Specialist")
        self.assertEqual(data["data"]["companyId"], str(self.company2.id))

    def test_create_role_duplicate_name_returns_409_conflict(self):
        """
        Verify creating duplicate role name returns 409 Conflict with standard error envelope.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Architect"}
        response = self.client.post("/roles", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "CONFLICT")

    def test_create_role_validation_error_400(self):
        """
        Verify creating role with blank name returns 400 Validation Error.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "   "}
        response = self.client.post("/roles", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_get_role_detail_success(self):
        """
        Verify retrieving single role detail by UUID.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/roles/{self.role1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["id"], str(self.role1.id))
        self.assertEqual(data["data"]["name"], "Architect")

    def test_update_role_success(self):
        """
        Verify partial update of role attributes (200 OK).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {
            "name": "Principal Architect",
            "isActive": False,
        }
        response = self.client.patch(f"/roles/{self.role1.id}", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["name"], "Principal Architect")
        self.assertFalse(data["data"]["isActive"])

    def test_delete_role_soft_deletes(self):
        """
        Verify deleting role soft-deletes the record (subsequent GET returns 404).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/roles/{self.role1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])

        # Subsequent retrieval returns 404
        get_resp = self.client.get(f"/roles/{self.role1.id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)
