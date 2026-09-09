from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tests.base import ThrottleIsolatedTestCase
from apps.authentication.tokens import CompanyUserRefreshToken

User = get_user_model()


class MeEndpointTestCase(ThrottleIsolatedTestCase):
    """
    Test suite for GET /auth/me endpoint.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/auth/me"
        self.user = User.objects.create_user(
            email="accountant@example.com",
            name="Accountant Pro",
            password="SecurePassword123!",
        )
        self.refresh = CompanyUserRefreshToken.for_user(self.user)
        self.access_token_str = str(self.refresh.access_token)

    def test_authenticated_me_returns_current_user_profile(self):
        """
        Valid access token returns 200 OK with full user profile in camelCase.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token_str}")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data["success"])
        self.assertIn("requestId", data)
        self.assertEqual(data["requestId"], response.headers.get("X-Request-ID"))

        payload = data["data"]
        self.assertEqual(payload["id"], str(self.user.id))
        self.assertEqual(payload["email"], "accountant@example.com")
        self.assertEqual(payload["name"], "Accountant Pro")
        self.assertEqual(payload["status"], "active")
        self.assertTrue(payload["isActive"])
        self.assertFalse(payload["isStaff"])
        self.assertIn("createdAt", payload)
        self.assertIn("updatedAt", payload)

    def test_unauthenticated_me_returns_401(self):
        """
        Request without Authorization header returns 401 AUTHENTICATION_ERROR.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_refresh_token_rejected_as_bearer_access_token(self):
        """
        BE-017 audit gap / JWT.md §4: a refresh token (token_type="refresh")
        must never be usable as a Bearer access token on a protected
        endpoint — SIMPLE_JWT["AUTH_TOKEN_CLASSES"] only accepts
        company_user/platform_admin/access token types, so a refresh token
        must fail verify_token_type() for all of them.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh}")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_expired_access_token_returns_401(self):
        """
        Expired access token returns 401 AUTHENTICATION_ERROR.
        """
        token = self.refresh.access_token
        # Backdate token expiration
        token.set_exp(lifetime=-timedelta(minutes=1))
        expired_token_str = str(token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token_str}")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")
