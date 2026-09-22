from unittest.mock import patch

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


class LoginEndpointTestCase(ThrottleIsolatedTestCase):
    """
    Test suite for POST /auth/login endpoint.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/auth/login"
        self.raw_password = "SecurePassword123!"
        self.user = User.objects.create_user(
            email="developer@example.com",
            name="Developer One",
            password=self.raw_password,
        )

    def test_valid_login_returns_token_pair_and_user_profile(self):
        """
        Valid login returns 200 OK with accessToken, refreshToken, and camelCase user profile.
        """
        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": self.raw_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data["success"])
        self.assertIn("requestId", data)
        self.assertIn("X-Request-ID", response.headers)
        self.assertEqual(data["requestId"], response.headers["X-Request-ID"])

        payload = data["data"]
        self.assertIn("accessToken", payload)
        self.assertIn("refreshToken", payload)
        self.assertIn("user", payload)

        user_data = payload["user"]
        self.assertEqual(user_data["id"], str(self.user.id))
        self.assertEqual(user_data["email"], "developer@example.com")
        self.assertEqual(user_data["name"], "Developer One")
        self.assertEqual(user_data["status"], "active")
        self.assertTrue(user_data["isActive"])
        self.assertFalse(user_data["isStaff"])

    def test_login_email_is_case_insensitive(self):
        """
        Login succeeds regardless of email casing.
        """
        response = self.client.post(
            self.url,
            {"email": "DEVELOPER@EXAMPLE.COM", "password": self.raw_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])

    def test_login_updates_last_login_timestamp(self):
        """
        Successful login updates user.last_login field.
        """
        self.assertIsNone(self.user.last_login)
        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": self.raw_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_access_token_claims_payload_security_boundary(self):
        """
        Verify access token carries sub, email, token_type=company_user,
        and strictly does NOT carry company_id or role/permissions.
        """
        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": self.raw_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        access_token_str = response.json()["data"]["accessToken"]
        decoded_token = UntypedToken(access_token_str)

        # Expected claims
        self.assertEqual(decoded_token["sub"], str(self.user.id))
        self.assertEqual(decoded_token["email"], "developer@example.com")
        self.assertEqual(decoded_token["token_type"], "company_user")
        self.assertIn("iat", decoded_token)
        self.assertIn("exp", decoded_token)
        self.assertIn("jti", decoded_token)

        # Prohibited claims (05_Security/JWT.md §3)
        self.assertNotIn("company_id", decoded_token)
        self.assertNotIn("companyId", decoded_token)
        self.assertNotIn("role", decoded_token)
        self.assertNotIn("roles", decoded_token)
        self.assertNotIn("permissions", decoded_token)

    def test_invalid_password_returns_401_authentication_error(self):
        """
        Invalid password returns 401 with standard AUTHENTICATION_ERROR envelope.
        """
        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": "WrongPassword!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")
        self.assertEqual(
            data["error"]["message"],
            "Invalid or expired authentication credentials.",
        )
        self.assertIn("requestId", data)

    def test_nonexistent_email_returns_identical_401_error(self):
        """
        Non-existent email returns identical 401 error to prevent user enumeration.
        """
        response = self.client.post(
            self.url,
            {"email": "nonexistent@example.com", "password": self.raw_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")
        self.assertEqual(
            data["error"]["message"],
            "Invalid or expired authentication credentials.",
        )

    def test_inactive_user_cannot_login(self):
        """
        Inactive user (is_active=False) receives 401 AUTHENTICATION_ERROR.
        """
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": self.raw_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_soft_deleted_user_cannot_login(self):
        """
        Soft-deleted user receives 401 AUTHENTICATION_ERROR.
        """
        self.user.delete()  # soft delete via SoftDeleteModel
        self.assertTrue(self.user.is_deleted)

        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": self.raw_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_missing_credentials_returns_400_validation_error(self):
        """
        Missing email or password returns 400 VALIDATION_ERROR with field issues.
        """
        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        details = data["error"]["details"]
        self.assertTrue(any(d["field"] == "email" for d in details))
        self.assertTrue(any(d["field"] == "password" for d in details))

    def test_successful_login_writes_audit_log_entry(self):
        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": self.raw_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        entry = AuditLog.objects.get(
            entity_type="user", entity_id=self.user.id, action="login_success"
        )
        self.assertEqual(entry.after_state["email"], self.user.email)

    def test_failed_login_for_existing_user_writes_audit_log_entry(self):
        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        entry = AuditLog.objects.get(
            entity_type="user", entity_id=self.user.id, action="login_failure"
        )
        self.assertEqual(entry.after_state["email"], self.user.email)

    def test_failed_login_for_nonexistent_email_writes_no_audit_log_entry(self):
        """
        There is no user record to attach an audit entry to for a
        completely unknown email — this must not create an entry with a
        fabricated/placeholder entity_id.
        """
        response = self.client.post(
            self.url,
            {"email": "nonexistent@example.com", "password": self.raw_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(AuditLog.objects.filter(action="login_failure").count(), 0)

    def test_unknown_email_still_runs_password_hasher_for_timing_parity(self):
        """
        Timing-attack mitigation: a login attempt against an email that
        doesn't exist must still pay the password-hashing cost, mirroring
        Django's own ModelBackend.authenticate() — otherwise response
        timing distinguishes "no such account" from "wrong password" for
        an existing account, leaking which emails are registered.
        """
        with patch(
            "apps.authentication.services.User.set_password", autospec=True
        ) as mocked_set_password:
            response = self.client.post(
                self.url,
                {"email": "definitely-not-registered@example.com", "password": "whatever123"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mocked_set_password.assert_called_once()

    def test_login_succeeds_with_a_leftover_ambiguous_company_token_attached(self):
        """
        Same bug as PlatformAuthEndpointTestCase's own version of this test
        (2026-09-22), for the far more common path: /auth/login itself
        wasn't in TenantJWTAuthentication's exempt_paths either, so a
        browser re-logging-in with a stale token from a user who now has
        2+ (or 0) active company memberships got a bare 403 before this
        view was ever reached, regardless of how valid the fresh login
        credentials in the body were.
        """
        company1 = Company.objects.create(name="Alpha Co", status=CompanyStatus.ACTIVE)
        company2 = Company.objects.create(name="Beta Co", status=CompanyStatus.ACTIVE)
        multi_user = User.objects.create_user(
            email="multi.member2@example.com", name="Multi Member Two", password="StrongPassword123!"
        )
        make_full_access_membership(company1, multi_user)
        make_full_access_membership(company2, multi_user)
        stale_token = str(CompanyUserAccessToken.for_user(multi_user))

        response = self.client.post(
            self.url,
            {"email": "developer@example.com", "password": self.raw_password},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {stale_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])
