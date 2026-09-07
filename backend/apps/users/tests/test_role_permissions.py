import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role

User = get_user_model()


class RoleSecurityAndPermissionsTestCase(TestCase):
    """
    Strict security and tenant-isolation test suite for Role endpoints (BE-014).
    Covers malformed JWTs, forged tokens, cross-tenant IDOR, and membership verification.
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Users
        self.user_c1 = User.objects.create_user(
            email="user1@company1.com",
            name="User One",
            password="StrongPassword123!",
        )
        self.token_c1 = str(CompanyUserAccessToken.for_user(self.user_c1))

        self.user_c2 = User.objects.create_user(
            email="user2@company2.com",
            name="User Two",
            password="StrongPassword123!",
        )
        self.token_c2 = str(CompanyUserAccessToken.for_user(self.user_c2))

        self.user_no_membership = User.objects.create_user(
            email="loner@nowhere.com",
            name="No Membership User",
            password="StrongPassword123!",
        )
        self.token_no_membership = str(CompanyUserAccessToken.for_user(self.user_no_membership))

        self.user_revoked = User.objects.create_user(
            email="revoked@company1.com",
            name="Revoked User",
            password="StrongPassword123!",
        )
        self.token_revoked = str(CompanyUserAccessToken.for_user(self.user_revoked))

        self.superadmin = User.objects.create_superuser(
            email="admin@platform.com",
            name="Super Admin",
            password="StrongPassword123!",
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        # 2. Companies
        self.company1 = Company.objects.create(
            name="Company One",
            status=CompanyStatus.ACTIVE,
        )
        self.company2 = Company.objects.create(
            name="Company Two",
            status=CompanyStatus.ACTIVE,
        )

        # 3. Memberships
        # user_c1 needs full permission codes in its own company so the
        # cross-tenant IDOR tests below actually exercise the object-level
        # (tenant-mismatch) 404 check, rather than failing earlier at the
        # action-level permission-code check with an unrelated 403.
        make_full_access_membership(self.company1, self.user_c1)
        CompanyMembership.objects.create(
            company=self.company2,
            user=self.user_c2,
            status=CompanyMembershipStatus.ACTIVE,
        )
        CompanyMembership.objects.create(
            company=self.company1,
            user=self.user_revoked,
            status=CompanyMembershipStatus.REVOKED,
        )

        # 4. Roles
        self.role_c1 = Role.objects.create(
            company=self.company1,
            name="C1 Role",
            description="Role in Company 1",
            is_active=True,
        )
        self.role_c2 = Role.objects.create(
            company=self.company2,
            name="C2 Role",
            description="Role in Company 2",
            is_active=True,
        )

    def test_malformed_jwt_header_returns_401_no_500(self):
        """
        Verify that malformed / garbage Authorization headers return 401 and never cause 500 error.
        """
        malformed_headers = [
            "Bearer invalid.jwt.structure",
            "Bearer",
            "Bearer ",
            "InvalidScheme token",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIifQ",  # missing signature
        ]
        for header in malformed_headers:
            self.client.credentials(HTTP_AUTHORIZATION=header)
            response = self.client.get("/roles")
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Failed for header: {header}",
            )
            self.assertEqual(response.json()["error"]["code"], "AUTHENTICATION_ERROR")

    def test_cross_tenant_idor_get_role_fails(self):
        """
        User in Company 1 retrieving a Company 2 role must get 404, not 403
        — a 403 would confirm the role exists (Error_Handling.md §5
        anti-enumeration rule). Fixed via ObjectPermission404Mixin on
        RoleViewSet (deferred at BE-018, applied there only to
        CompanyViewSet; closed out for Role here).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_c1}")
        response = self.client.get(f"/roles/{self.role_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "NOT_FOUND")

    def test_cross_tenant_idor_patch_role_fails(self):
        """
        PATCH equivalent of the GET case above — must also be 404, not 403.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_c1}")
        payload = {"name": "Hacked Name"}
        response = self.client.patch(f"/roles/{self.role_c2.id}", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")
        self.role_c2.refresh_from_db()
        self.assertEqual(self.role_c2.name, "C2 Role")

    def test_cross_tenant_idor_delete_role_fails(self):
        """
        DELETE equivalent of the GET case above — must also be 404, not 403.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_c1}")
        response = self.client.delete(f"/roles/{self.role_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")
        self.role_c2.refresh_from_db()
        self.assertFalse(self.role_c2.is_deleted)

    def test_cross_tenant_get_role_and_nonexistent_role_are_indistinguishable(self):
        """
        No enumeration possible: a real role in another tenant and a
        random/nonexistent UUID must produce the identical 404 response
        shape, so a caller cannot use the status code to detect whether a
        given role ID exists in some other company.
        """
        import uuid as _uuid

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_c1}")

        real_cross_tenant_response = self.client.get(f"/roles/{self.role_c2.id}")
        nonexistent_response = self.client.get(f"/roles/{_uuid.uuid4()}")

        self.assertEqual(real_cross_tenant_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            real_cross_tenant_response.json()["error"]["code"],
            nonexistent_response.json()["error"]["code"],
        )

    def test_cross_tenant_company_injection_in_create_fails(self):
        """
        Verify User in Company 1 cannot create a role in Company 2 by supplying companyId.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_c1}")
        payload = {
            "name": "Injected Role",
            "companyId": str(self.company2.id),
        }
        response = self.client.post("/roles", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Role.objects.filter(name="Injected Role").exists())

    def test_user_without_active_membership_denied_access(self):
        """
        Verify user with no company memberships receives 403 Forbidden.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_no_membership}")
        response = self.client.get("/roles")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        resp_create = self.client.post("/roles", {"name": "Test Role"})
        self.assertEqual(resp_create.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_revoked_membership_denied_access(self):
        """
        Verify user with revoked membership receives 403 Forbidden.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_revoked}")
        response = self.client.get("/roles")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_platform_admin_can_manage_any_tenant_role(self):
        """
        Verify Platform Admin can view, update, and delete roles in any company.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")

        # Retrieve C1 role
        resp_get = self.client.get(f"/roles/{self.role_c1.id}")
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)

        # Update C2 role
        resp_patch = self.client.patch(f"/roles/{self.role_c2.id}", {"description": "Admin edited"}, format="json")
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_patch.json()["data"]["description"], "Admin edited")

        # Delete C1 role
        resp_del = self.client.delete(f"/roles/{self.role_c1.id}")
        self.assertEqual(resp_del.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_del.json()["success"])
