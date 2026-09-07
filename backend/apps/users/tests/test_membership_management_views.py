from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role

User = get_user_model()


class CompanyMembershipViewSetTestCase(TestCase):
    """
    Integration test suite for Company Membership management endpoints
    (BE-052), mirroring RoleViewSetTestCase's structure.
    """

    def setUp(self):
        self.client = APIClient()

        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com", name="Super Admin", password="StrongPassword123!"
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        self.admin_user = User.objects.create_user(
            email="admin@company1.com", name="Admin User", password="StrongPassword123!"
        )
        self.admin_token = str(CompanyUserAccessToken.for_user(self.admin_user))

        self.non_member_user = User.objects.create_user(
            email="outsider@example.com", name="Outsider", password="StrongPassword123!"
        )
        self.non_member_token = str(CompanyUserAccessToken.for_user(self.non_member_user))

        self.invitee = User.objects.create_user(
            email="invitee@example.com", name="Invitee", password="StrongPassword123!"
        )

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        CompanyMembership.objects.create(
            company=self.company1, user=self.admin_user, status=CompanyMembershipStatus.ACTIVE
        )
        self.other_company_membership = CompanyMembership.objects.create(
            company=self.company2, user=self.non_member_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.role1 = Role.objects.create(company=self.company1, name="Accountant", is_active=True)
        self.role2 = Role.objects.create(company=self.company2, name="Sales", is_active=True)

    def test_unauthenticated_requests_fail_401(self):
        response = self.client.get("/company-memberships")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_memberships_scoped_to_own_company(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get("/company-memberships")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["userEmail"], "admin@company1.com")

    def test_invite_member_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(
            "/company-memberships", {"email": self.invitee.email}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["userEmail"], self.invitee.email)
        self.assertEqual(data["status"], "invited")
        self.assertEqual(data["companyId"], str(self.company1.id))

    def test_invite_member_with_role(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(
            "/company-memberships",
            {"email": self.invitee.email, "roleId": str(self.role1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["roleId"], str(self.role1.id))

    def test_invite_member_unknown_email_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(
            "/company-memberships", {"email": "ghost@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_membership_from_other_company_returns_404(self):
        """
        Cross-tenant object access by ID must return 404, never 403 or the
        real data -- Error_Handling.md's anti-enumeration rule, same
        pattern as BE-018's CompanyViewSet fix.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/company-memberships/{self.other_company_membership.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_role_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        membership = CompanyMembership.objects.create(
            company=self.company1, user=self.invitee, status=CompanyMembershipStatus.ACTIVE
        )
        response = self.client.post(
            f"/company-memberships/{membership.id}/assign-role",
            {"roleId": str(self.role1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["roleId"], str(self.role1.id))

    def test_assign_role_from_other_company_rejected_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        membership = CompanyMembership.objects.create(
            company=self.company1, user=self.invitee, status=CompanyMembershipStatus.ACTIVE
        )
        response = self.client.post(
            f"/company-memberships/{membership.id}/assign-role",
            {"roleId": str(self.role2.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_role_on_other_company_membership_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(
            f"/company-memberships/{self.other_company_membership.id}/assign-role",
            {"roleId": str(self.role1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_suspend_and_reactivate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        membership = CompanyMembership.objects.create(
            company=self.company1, user=self.invitee, status=CompanyMembershipStatus.ACTIVE
        )

        suspend_response = self.client.post(f"/company-memberships/{membership.id}/suspend")
        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(suspend_response.json()["data"]["status"], "revoked")

        reactivate_response = self.client.post(f"/company-memberships/{membership.id}/reactivate")
        self.assertEqual(reactivate_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reactivate_response.json()["data"]["status"], "active")

    def test_remove_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        membership = CompanyMembership.objects.create(company=self.company1, user=self.invitee)

        response = self.client.delete(f"/company-memberships/{membership.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CompanyMembership.objects.filter(id=membership.id).exists())

    def test_remove_member_on_other_company_membership_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.delete(f"/company-memberships/{self.other_company_membership.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            CompanyMembership.objects.filter(id=self.other_company_membership.id).exists()
        )

    def test_platform_admin_can_still_call_endpoints(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get(f"/company-memberships/{self.other_company_membership.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RolePermissionAssignmentViewTestCase(TestCase):
    """
    Integration tests for `PUT /roles/{id}/permissions` and
    `GET /permissions` (BE-049/BE-051).
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email="admin@company1.com", name="Admin User", password="StrongPassword123!"
        )
        self.admin_token = str(CompanyUserAccessToken.for_user(self.admin_user))
        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        CompanyMembership.objects.create(
            company=self.company1, user=self.admin_user, status=CompanyMembershipStatus.ACTIVE
        )
        self.role1 = Role.objects.create(company=self.company1, name="Custom", is_active=True)
        self.role_c2 = Role.objects.create(company=self.company2, name="OtherCo Role", is_active=True)

    def test_list_permissions_requires_auth(self):
        response = self.client.get("/permissions")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_permissions_returns_catalog(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get("/permissions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = {p["code"] for p in response.json()["data"]}
        self.assertIn("project.view", codes)
        self.assertIn("invoice.view", codes)

    def test_assign_permissions_to_own_company_role(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.put(
            f"/roles/{self.role1.id}/permissions",
            {"permissionCodes": ["project.view", "project.edit"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assign_permissions_unknown_code_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.put(
            f"/roles/{self.role1.id}/permissions",
            {"permissionCodes": ["bogus.code"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_permissions_on_other_company_role_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.put(
            f"/roles/{self.role_c2.id}/permissions",
            {"permissionCodes": ["project.view"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
