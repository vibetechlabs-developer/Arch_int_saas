from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserRefreshToken

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
