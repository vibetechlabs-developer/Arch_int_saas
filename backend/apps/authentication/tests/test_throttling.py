from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tests.base import ThrottleIsolatedTestCase

User = get_user_model()


class AuthEndpointThrottlingTestCase(ThrottleIsolatedTestCase):
    """
    DRF ScopedRateThrottle protects the five pre-auth endpoints most
    exposed to brute-force/enumeration abuse. DEFAULT_THROTTLE_RATES
    (config/settings.py) sets auth_login=10/min, platform_auth_login=
    10/min, auth_forgot_password=5/min, auth_reset_password=10/min,
    auth_refresh=30/min. These tests exceed each rate and confirm the
    (N+1)th request is rejected with the project's standard 429 envelope
    (already wired through custom_exception_handler's existing Throttled
    mapping — no response-shape change needed for this to work).

    ThrottleIsolatedTestCase resets the cache-backed throttle state
    before/after every test, so these counts are exact and don't leak
    between test methods or test files, regardless of test runner.
    """

    def setUp(self):
        self.client = APIClient()

    def test_login_endpoint_throttles_after_configured_rate(self):
        for _ in range(10):
            response = self.client.post(
                "/auth/login",
                {"email": "nobody@example.com", "password": "wrong"},
                format="json",
            )
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(
            "/auth/login",
            {"email": "nobody@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "RATE_LIMIT_EXCEEDED")

    def test_platform_login_endpoint_has_its_own_independent_throttle_bucket(self):
        """
        platform_auth_login uses a distinct scope from auth_login — hitting
        one endpoint's limit must not affect the other's budget.
        """
        for _ in range(10):
            self.client.post(
                "/auth/login", {"email": "nobody@example.com", "password": "wrong"}, format="json"
            )

        # The company-user login bucket is now exhausted, but the platform
        # admin login bucket is untouched and must still succeed (as far as
        # throttling is concerned — 401 for bad credentials is fine, 429 is not).
        response = self.client.post(
            "/platform-auth/login",
            {"email": "nobody@example.com", "password": "wrong"},
            format="json",
        )
        self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_forgot_password_endpoint_throttles_after_configured_rate(self):
        for _ in range(5):
            response = self.client.post(
                "/auth/forgot-password", {"email": "someone@example.com"}, format="json"
            )
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(
            "/auth/forgot-password", {"email": "someone@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_reset_password_endpoint_throttles_after_configured_rate(self):
        for _ in range(10):
            response = self.client.post(
                "/auth/reset-password",
                {"token": "not-a-real-token", "newPassword": "whatever123"},
                format="json",
            )
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(
            "/auth/reset-password",
            {"token": "not-a-real-token", "newPassword": "whatever123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_refresh_endpoint_throttles_after_configured_rate(self):
        for _ in range(30):
            response = self.client.post(
                "/auth/refresh", {"refreshToken": "not-a-real-token"}, format="json"
            )
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(
            "/auth/refresh", {"refreshToken": "not-a-real-token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_unthrottled_endpoints_are_unaffected(self):
        """
        ScopedRateThrottle only throttles a view that declares
        throttle_scope — /auth/me (no scope) must remain unaffected by
        DEFAULT_THROTTLE_CLASSES being set globally.
        """
        user = User.objects.create_user(
            email="frequent@example.com", name="Frequent Caller", password="SecurePassword123!"
        )
        login = self.client.post(
            "/auth/login",
            {"email": "frequent@example.com", "password": "SecurePassword123!"},
            format="json",
        )
        access_token = login.json()["data"]["accessToken"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        for _ in range(15):
            response = self.client.get("/auth/me")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
