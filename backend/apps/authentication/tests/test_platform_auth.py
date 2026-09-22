from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import UntypedToken

from apps.audit.models import AuditLog
from apps.authentication.tests.base import ThrottleIsolatedTestCase
from apps.authentication.tokens import CompanyUserAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus

User = get_user_model()


class PlatformAuthEndpointTestCase(ThrottleIsolatedTestCase):
    """
    Test suite for POST /platform-auth/login endpoint.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/platform-auth/login"
        self.password = "AdminSuperSecret2026!"
        self.admin_user = User.objects.create_superuser(
            email="platform.admin@example.com",
            name="Platform SuperAdmin",
            password=self.password,
        )
        self.regular_user = User.objects.create_user(
            email="regular.user@example.com",
            name="Regular User",
            password=self.password,
        )

    def test_platform_super_admin_login_success(self):
        """
        Platform super admin login returns 200 with tokens carrying token_type=platform_admin.
        """
        response = self.client.post(
            self.url,
            {"email": "platform.admin@example.com", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])

        payload = data["data"]
        self.assertIn("accessToken", payload)
        self.assertIn("refreshToken", payload)
        self.assertIn("user", payload)
        self.assertTrue(payload["user"]["isStaff"])

        # Verify decoded token carries token_type: platform_admin
        decoded = UntypedToken(payload["accessToken"])
        self.assertEqual(decoded["token_type"], "platform_admin")
        self.assertEqual(decoded["sub"], str(self.admin_user.id))

    def test_regular_user_cannot_login_to_platform_auth(self):
        """
        Regular company user (not superuser/staff) receives 401 AUTHENTICATION_ERROR on platform login.
        """
        response = self.client.post(
            self.url,
            {"email": "regular.user@example.com", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_staff_only_user_cannot_login_to_platform_auth_without_superuser(self):
        """
        Staff user without is_superuser=True is rejected.
        """
        staff_user = User.objects.create_user(
            email="staff.only@example.com",
            name="Staff User",
            password=self.password,
            is_staff=True,
        )

        response = self.client.post(
            self.url,
            {"email": "staff.only@example.com", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_platform_admin_token_can_access_auth_me(self):
        """
        Platform admin access token is accepted by DRF JWT authentication on protected endpoints.
        """
        login_res = self.client.post(
            self.url,
            {"email": "platform.admin@example.com", "password": self.password},
            format="json",
        )
        access_token = login_res.json()["data"]["accessToken"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_res = self.client.get("/auth/me")

        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        me_data = me_res.json()["data"]
        self.assertEqual(me_data["email"], "platform.admin@example.com")
        self.assertTrue(me_data["isStaff"])

    def test_platform_admin_login_recognized_end_to_end_on_gated_endpoint(self):
        """
        BE-017 audit gap: every existing "platform admin" test elsewhere in
        the suite mints its token via PlatformAdminAccessToken.for_user()
        directly, bypassing the RefreshToken.access_token property's claim
        copy-loop that the real login flow (AuthenticationService.
        login_platform_admin -> PlatformAdminRefreshToken.for_user().
        access_token) actually goes through. This proves the token issued
        by the real POST /platform-auth/login endpoint is recognized as
        platform_admin end-to-end by an endpoint that actually gates on it
        (GET /companies, via IsPlatformAdminOrCompanyAccess), not just an
        endpoint like /auth/me that accepts any authenticated user.
        """
        login_res = self.client.post(
            self.url,
            {"email": "platform.admin@example.com", "password": self.password},
            format="json",
        )
        access_token = login_res.json()["data"]["accessToken"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        companies_res = self.client.get("/companies")

        self.assertEqual(companies_res.status_code, status.HTTP_200_OK)
        self.assertTrue(companies_res.json()["success"])

    def test_successful_platform_admin_login_writes_audit_log_entry(self):
        response = self.client.post(
            self.url,
            {"email": "platform.admin@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        entry = AuditLog.objects.get(
            entity_type="user", entity_id=self.admin_user.id, action="login_success"
        )
        self.assertEqual(entry.after_state["email"], self.admin_user.email)

    def test_non_admin_valid_credentials_against_platform_login_writes_failure_entry(self):
        """
        A regular (non-admin) user with otherwise-correct credentials is
        still rejected by /platform-auth/login — and that rejection must
        itself be audited as a login_failure, since it's a real attempt to
        use the platform-admin surface.
        """
        regular_user = User.objects.create_user(
            email="not.admin@example.com", name="Not Admin", password="RegularPassword123!"
        )

        response = self.client.post(
            self.url,
            {"email": "not.admin@example.com", "password": "RegularPassword123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        entry = AuditLog.objects.get(
            entity_type="user", entity_id=regular_user.id, action="login_failure"
        )
        self.assertEqual(entry.after_state["email"], regular_user.email)

        # A denied platform-admin attempt must not mutate last_login just
        # because the underlying credentials happened to be valid.
        regular_user.refresh_from_db()
        self.assertIsNone(regular_user.last_login)

    def test_platform_login_succeeds_with_a_leftover_ambiguous_company_token_attached(self):
        """
        Bug found live (2026-09-22): apiClient's request interceptor
        attaches whatever access token is in storage to every request,
        including a fresh login attempt. TenantJWTAuthentication.
        authenticate() previously ran its full companyId-resolution logic
        against /platform-auth/login too (it wasn't in exempt_paths), so a
        browser with a leftover token belonging to a user with 2+ (or 0)
        active company memberships got a bare 403 PermissionDenied before
        PlatformLoginView was ever reached -- even though the login
        credentials in the request body were entirely valid. This
        reproduces the exact ambiguous-membership case.
        """
        company1 = Company.objects.create(name="Alpha Co", status=CompanyStatus.ACTIVE)
        company2 = Company.objects.create(name="Beta Co", status=CompanyStatus.ACTIVE)
        multi_user = User.objects.create_user(
            email="multi.member@example.com", name="Multi Member", password="StrongPassword123!"
        )
        make_full_access_membership(company1, multi_user)
        make_full_access_membership(company2, multi_user)
        stale_token = str(CompanyUserAccessToken.for_user(multi_user))

        response = self.client.post(
            self.url,
            {"email": "platform.admin@example.com", "password": self.password},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {stale_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])
