import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, User

User = get_user_model()


@override_settings(ROOT_URLCONF="apps.users.tests.tenant_info_support")
class TenantAuthIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Platform admin
        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com",
            name="Super Admin",
            password="StrongPassword123!",
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))
        # Companies
        self.company_a = Company.objects.create(name="Company A", status=CompanyStatus.ACTIVE)
        self.company_b = Company.objects.create(name="Company B", status=CompanyStatus.ACTIVE)
        # Regular user with single active membership (Company A)
        self.single_user = User.objects.create_user(
            email="single@user.com",
            name="Single User",
            password="StrongPassword123!",
        )
        self.single_token = str(CompanyUserAccessToken.for_user(self.single_user))
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.single_user,
            status=CompanyMembershipStatus.ACTIVE,
        )
        # Regular user with multiple memberships (Company A and B)
        self.multi_user = User.objects.create_user(
            email="multi@user.com",
            name="Multi User",
            password="StrongPassword123!",
        )
        self.multi_token = str(CompanyUserAccessToken.for_user(self.multi_user))
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.multi_user,
            status=CompanyMembershipStatus.ACTIVE,
        )
        CompanyMembership.objects.create(
            company=self.company_b,
            user=self.multi_user,
            status=CompanyMembershipStatus.ACTIVE,
        )
        # User with inactive membership to Company B
        self.inactive_user = User.objects.create_user(
            email="inactive@user.com",
            name="Inactive User",
            password="StrongPassword123!",
        )
        self.inactive_token = str(CompanyUserAccessToken.for_user(self.inactive_user))
        CompanyMembership.objects.create(
            company=self.company_b,
            user=self.inactive_user,
            status=CompanyMembershipStatus.REVOKED,
        )
        # User with soft-deleted membership to Company B
        self.deleted_user = User.objects.create_user(
            email="deleted@user.com",
            name="Deleted User",
            password="StrongPassword123!",
        )
        self.deleted_token = str(CompanyUserAccessToken.for_user(self.deleted_user))
        membership = CompanyMembership.objects.create(
            company=self.company_b,
            user=self.deleted_user,
            status=CompanyMembershipStatus.ACTIVE,
        )
        # Soft delete the membership (BaseModel provides soft delete via .delete())
        membership.delete()

    # BE-017 audit gap: JWT.md §3 — a forged/injected company_id claim in an
    # otherwise-valid, correctly-signed token must never influence tenant
    # resolution. The server must always re-derive company_id from active
    # CompanyMembership records, not from anything embedded in the token.
    def test_forged_company_id_claim_in_token_is_ignored(self):
        forged_token = CompanyUserAccessToken.for_user(self.single_user)
        forged_token["company_id"] = str(self.company_b.id)
        forged_token["companyId"] = str(self.company_b.id)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {forged_token}")
        resp = self.client.get("/test/tenant-info/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        # Resolved from the real active membership (Company A), never from
        # the forged claim (Company B).
        self.assertEqual(data["data"]["company_id"], str(self.company_a.id))
        self.assertNotEqual(data["data"]["company_id"], str(self.company_b.id))

    # A. Single active membership, no companyId param
    def test_single_active_membership(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.single_token}")
        resp = self.client.get("/test/tenant-info/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["company_id"], str(self.company_a.id))
        self.assertFalse(data["data"]["is_platform_admin"])

    # B. Multiple memberships, valid company A claim
    def test_multiple_memberships_valid_company_a(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        resp = self.client.get(f"/test/tenant-info/?companyId={self.company_a.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["company_id"], str(self.company_a.id))
        self.assertFalse(data["data"]["is_platform_admin"])

    # C. Multiple memberships, valid company B claim
    def test_multiple_memberships_valid_company_b(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        resp = self.client.get(f"/test/tenant-info/?companyId={self.company_b.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["company_id"], str(self.company_b.id))
        self.assertFalse(data["data"]["is_platform_admin"])

    # D. Multiple memberships, missing company claim
    def test_multiple_memberships_missing_company(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        resp = self.client.get("/test/tenant-info/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "PERMISSION_ERROR")

    # E. Unauthorized company claim
    def test_unauthorized_company_claim(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.single_token}")
        resp = self.client.get(f"/test/tenant-info/?companyId={self.company_b.id}")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "PERMISSION_ERROR")

    # F. Inactive membership claim
    def test_inactive_membership_claim(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.inactive_token}")
        resp = self.client.get(f"/test/tenant-info/?companyId={self.company_b.id}")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "PERMISSION_ERROR")

    # G. Soft-deleted membership claim
    def test_soft_deleted_membership_claim(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.deleted_token}")
        resp = self.client.get(f"/test/tenant-info/?companyId={self.company_b.id}")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "PERMISSION_ERROR")

    # H. Platform admin
    def test_platform_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        resp = self.client.get("/test/tenant-info/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIsNone(data["data"]["company_id"])
        self.assertTrue(data["data"]["is_platform_admin"])

    # I. Unauthenticated request
    def test_unauthenticated(self):
        self.client.credentials()  # clear credentials
        resp = self.client.get("/test/tenant-info/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    # J. Invalid JWT
    def test_invalid_jwt(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken")
        resp = self.client.get("/test/tenant-info/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        data = resp.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")
