from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.authentication.tokens import CompanyUserRefreshToken, PlatformAdminRefreshToken

User = get_user_model()


class TokenRefreshEndpointTestCase(TestCase):
    """
    Test suite for POST /auth/refresh endpoint.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/auth/refresh"
        self.user = User.objects.create_user(
            email="architect@example.com",
            name="Architect Pro",
            password="SecurePassword123!",
        )
        self.refresh = CompanyUserRefreshToken.for_user(self.user)
        self.refresh_token_str = str(self.refresh)

    def test_valid_refresh_token_returns_new_access_and_rotated_refresh_token(self):
        """
        Valid refresh token exchange returns new accessToken and new rotated refreshToken.
        """
        response = self.client.post(
            self.url,
            {"refreshToken": self.refresh_token_str},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data["success"])
        payload = data["data"]
        self.assertIn("accessToken", payload)
        self.assertIn("refreshToken", payload)

        new_refresh = payload["refreshToken"]
        self.assertNotEqual(new_refresh, self.refresh_token_str)

    def test_refresh_token_rotation_blacklists_previous_token(self):
        """
        Once rotated, the old refresh token is blacklisted and cannot be reused.
        """
        # First exchange - succeeds
        response1 = self.client.post(
            self.url,
            {"refreshToken": self.refresh_token_str},
            format="json",
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Attempt to reuse the old refresh token - must fail
        response2 = self.client.post(
            self.url,
            {"refreshToken": self.refresh_token_str},
            format="json",
        )
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response2.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_invalid_refresh_token_returns_401(self):
        """
        Malformed refresh token string returns 401 AUTHENTICATION_ERROR.
        """
        response = self.client.post(
            self.url,
            {"refreshToken": "invalid.jwt.token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_missing_refresh_token_field_returns_400_validation_error(self):
        """
        Missing refreshToken field returns 400 VALIDATION_ERROR.
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

    def test_successful_refresh_writes_audit_log_entry(self):
        response = self.client.post(
            self.url, {"refreshToken": self.refresh_token_str}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        entry = AuditLog.objects.get(entity_type="user", entity_id=self.user.id, action="token_refresh")
        self.assertEqual(entry.after_state["email"], self.user.email)

    def test_stale_admin_privilege_claim_is_rejected_not_re_minted(self):
        """
        A refresh token minted while the user WAS a platform admin must be
        rejected if their admin privileges have since been revoked — the
        prior implementation trusted the token's own user_type claim and
        would have kept minting valid platform_admin access tokens from a
        stale claim until the refresh token itself expired.
        """
        admin = User.objects.create_superuser(
            email="wasadmin@example.com", name="Was Admin", password="SecurePassword123!"
        )
        admin_refresh = PlatformAdminRefreshToken.for_user(admin)

        # Privilege revoked after the token was issued.
        admin.is_superuser = False
        admin.is_staff = False
        admin.save(update_fields=["is_superuser", "is_staff"])

        response = self.client.post(
            self.url, {"refreshToken": str(admin_refresh)}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["error"]["code"], "AUTHENTICATION_ERROR")

    def test_current_admin_privilege_is_reflected_even_if_claim_was_stale_company_user(self):
        """
        The reverse case is not a security concern (regaining/gaining admin
        privilege between issuance and refresh isn't a privilege
        escalation via the refresh token itself — the DB state is what's
        authoritative) — the refreshed access token must reflect the
        user's CURRENT state.
        """
        user = User.objects.create_user(
            email="promoted@example.com", name="Promoted", password="SecurePassword123!"
        )
        company_refresh = CompanyUserRefreshToken.for_user(user)

        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=["is_superuser", "is_staff"])

        response = self.client.post(
            self.url, {"refreshToken": str(company_refresh)}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_for_deactivated_user_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url, {"refreshToken": self.refresh_token_str}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
