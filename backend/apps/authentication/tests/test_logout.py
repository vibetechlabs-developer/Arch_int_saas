from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.authentication.tokens import CompanyUserRefreshToken

User = get_user_model()


class LogoutEndpointTestCase(TestCase):
    """
    Test suite for POST /auth/logout endpoint.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/auth/logout"
        self.user = User.objects.create_user(
            email="manager@example.com",
            name="Manager One",
            password="SecurePassword123!",
        )
        self.refresh = CompanyUserRefreshToken.for_user(self.user)
        self.access_token_str = str(self.refresh.access_token)
        self.refresh_token_str = str(self.refresh)

    def test_authenticated_logout_blacklists_refresh_token(self):
        """
        Authenticated request with valid refresh token returns 200 and blacklists the token.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token_str}")

        response = self.client.post(
            self.url,
            {"refreshToken": self.refresh_token_str},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["message"], "Logged out successfully.")

        # Attempting to refresh using the logged-out refresh token must fail
        refresh_response = self.client.post(
            "/auth/refresh",
            {"refreshToken": self.refresh_token_str},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            refresh_response.json()["error"]["code"],
            "AUTHENTICATION_ERROR",
        )

    def test_unauthenticated_logout_returns_401(self):
        """
        Logout without Bearer access token returns 401 AUTHENTICATION_ERROR.
        """
        response = self.client.post(
            self.url,
            {"refreshToken": self.refresh_token_str},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_logout_with_invalid_refresh_token_returns_401(self):
        """
        Logout with malformed refresh token returns 401 AUTHENTICATION_ERROR.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token_str}")

        response = self.client.post(
            self.url,
            {"refreshToken": "invalid.refresh.token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_missing_refresh_token_returns_400_validation_error(self):
        """
        Missing refreshToken field returns 400 VALIDATION_ERROR.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token_str}")

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_successful_logout_writes_audit_log_entry(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token_str}")

        response = self.client.post(
            self.url, {"refreshToken": self.refresh_token_str}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        entry = AuditLog.objects.get(entity_type="user", entity_id=self.user.id, action="logout")
        self.assertEqual(entry.after_state["email"], self.user.email)
