from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.models import PasswordResetToken
from apps.authentication.tokens import CompanyUserRefreshToken

User = get_user_model()


class ResetPasswordTestCase(TestCase):
    """
    Test suite for POST /auth/reset-password endpoint.
    Verifies token validation, password complexity, atomic password update,
    and session/refresh token invalidation.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/auth/reset-password"
        self.email = "contractor@example.com"
        self.initial_password = "InitialPassword123!"
        self.new_password = "NewStrongPassword456!"

        self.user = User.objects.create_user(
            email=self.email,
            name="Contractor Pro",
            password=self.initial_password,
        )

        # Generate a valid reset token for the user
        self.token_record, self.raw_token = PasswordResetToken.generate_token_for_user(self.user)

    def test_valid_token_resets_password_successfully(self):
        """
        Valid token updates password, consumes token, and allows login with new password.
        """
        response = self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["message"], "Password has been reset successfully.")
        self.assertIn("requestId", data)
        self.assertIn("X-Request-ID", response.headers)

        # Verify token is marked consumed
        self.token_record.refresh_from_db()
        self.assertTrue(self.token_record.is_consumed)
        self.assertFalse(self.token_record.is_valid)

        # Verify old password no longer works
        login_old = self.client.post(
            "/auth/login",
            {"email": self.email, "password": self.initial_password},
            format="json",
        )
        self.assertEqual(login_old.status_code, status.HTTP_401_UNAUTHORIZED)

        # Verify new password works
        login_new = self.client.post(
            "/auth/login",
            {"email": self.email, "password": self.new_password},
            format="json",
        )
        self.assertEqual(login_new.status_code, status.HTTP_200_OK)
        self.assertTrue(login_new.json()["success"])

    def test_reset_password_rejects_undocumented_password_field_without_new_password(self):
        """
        Submitting undocumented 'password' instead of 'newPassword' fails validation (400 VALIDATION_ERROR).
        """
        response = self.client.post(
            self.url,
            {"token": self.raw_token, "password": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertTrue(any(d["field"] == "newPassword" for d in data["error"]["details"]))

    def test_already_consumed_token_cannot_be_reused(self):
        """
        Token cannot be used a second time after successful reset.
        """
        # First reset - succeeds
        self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": self.new_password},
            format="json",
        )

        # Second attempt with same token - must fail
        response = self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": "AnotherPassword789!"},
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

    def test_expired_token_is_rejected(self):
        """
        Expired reset token is rejected with 401 AUTHENTICATION_ERROR.
        """
        self.token_record.expires_at = timezone.now() - timedelta(minutes=5)
        self.token_record.save(update_fields=["expires_at"])

        response = self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_invalid_or_forged_token_is_rejected(self):
        """
        Non-existent or forged token string is rejected with 401 AUTHENTICATION_ERROR.
        """
        response = self.client.post(
            self.url,
            {"token": "completely-fake-and-forged-token", "newPassword": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

    def test_weak_password_rejected_by_password_validators(self):
        """
        Weak password failing Django validation produces 400 VALIDATION_ERROR.
        """
        response = self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": "123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertTrue(len(data["error"]["details"]) > 0)

        # Token must remain valid and unconsumed if validation failed
        self.token_record.refresh_from_db()
        self.assertTrue(self.token_record.is_valid)

    def test_missing_required_fields_returns_400_validation_error(self):
        """
        Missing token or password returns 400 VALIDATION_ERROR.
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

    def test_password_reset_revokes_all_existing_refresh_tokens(self):
        """
        Resetting password invalidates/blacklists any prior active refresh tokens for the user.
        """
        # Generate an active refresh token before password reset
        prior_refresh = CompanyUserRefreshToken.for_user(self.user)
        prior_refresh_str = str(prior_refresh)

        # Perform password reset
        response = self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": self.new_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Attempting to refresh using the prior refresh token must fail
        refresh_attempt = self.client.post(
            "/auth/refresh",
            {"refreshToken": prior_refresh_str},
            format="json",
        )
        self.assertEqual(refresh_attempt.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            refresh_attempt.json()["error"]["code"],
            "AUTHENTICATION_ERROR",
        )

    def test_token_superseded_by_newer_forgot_password_request_is_rejected(self):
        """
        BE-017 audit gap: a reset token that has been superseded by a later
        POST /auth/forgot-password call (which invalidates prior unconsumed
        tokens — see test_forgot_password.py's DB-level assertion of this)
        must be rejected by the live /auth/reset-password endpoint itself,
        not just observably marked consumed in the database.
        """
        self.client.post("/auth/forgot-password", {"email": self.email}, format="json")

        response = self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_ERROR")

        # The original token record is the one that was superseded/consumed.
        self.token_record.refresh_from_db()
        self.assertTrue(self.token_record.is_consumed)

        # Original password must still work — the rejected reset must not
        # have taken effect.
        login = self.client.post(
            "/auth/login",
            {"email": self.email, "password": self.initial_password},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_password_or_token_are_never_returned_in_response(self):
        """
        API response never leaks passwords, password hashes, or token values.
        """
        response = self.client.post(
            self.url,
            {"token": self.raw_token, "newPassword": self.new_password},
            format="json",
        )
        data = response.json()

        for sensitive in ["password", "token", "raw_token", "token_hash", "hash"]:
            self.assertNotIn(sensitive, data["data"])
