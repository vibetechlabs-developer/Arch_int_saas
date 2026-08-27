from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.authentication.models import PasswordResetToken

User = get_user_model()


class ForgotPasswordTestCase(TestCase):
    """
    Test suite for POST /auth/forgot-password endpoint.
    Verifies user enumeration prevention, token generation, hashing, and email dispatch.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/auth/forgot-password"
        self.email = "designer@example.com"
        self.user = User.objects.create_user(
            email=self.email,
            name="Designer One",
            password="InitialPassword123!",
        )

    def test_existing_user_receives_generic_success_and_email_dispatched(self):
        """
        Valid email triggers token creation and dispatches email with generic success response.
        """
        response = self.client.post(
            self.url,
            {"email": self.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(
            data["data"]["message"],
            "If the email is registered and active, password reset instructions have been sent.",
        )
        self.assertIn("requestId", data)
        self.assertIn("X-Request-ID", response.headers)

        # Verify token record was created in database
        token_record = PasswordResetToken.objects.filter(user=self.user).first()
        self.assertIsNotNone(token_record)
        self.assertTrue(token_record.is_valid)
        self.assertFalse(token_record.is_consumed)
        self.assertFalse(token_record.is_expired)

        # Verify token hash is 64 hex characters (SHA-256)
        self.assertEqual(len(token_record.token_hash), 64)

        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.email])
        self.assertIn("Reset Your INT Projects SaaS Password", sent_email.subject)
        self.assertIn("reset-password?token=", sent_email.body)

    def test_nonexistent_email_returns_identical_generic_response_without_email(self):
        """
        Non-existent email produces identical 200 response without dispatching email.
        """
        response = self.client.post(
            self.url,
            {"email": "unknown.user@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(
            data["data"]["message"],
            "If the email is registered and active, password reset instructions have been sent.",
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_inactive_user_returns_identical_generic_response_without_email(self):
        """
        Inactive user (is_active=False) receives identical generic response without email dispatch.
        """
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url,
            {"email": self.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_soft_deleted_user_returns_identical_generic_response_without_email(self):
        """
        Soft-deleted user receives identical generic response without email dispatch.
        """
        self.user.delete()
        self.assertTrue(self.user.is_deleted)

        response = self.client.post(
            self.url,
            {"email": self.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_email_normalization_is_case_insensitive(self):
        """
        Email casing and surrounding whitespace are normalized.
        """
        response = self.client.post(
            self.url,
            {"email": "  DESIGNER@EXAMPLE.COM  "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.user).count(), 1)

    def test_raw_token_is_not_persisted_in_database(self):
        """
        Database stores only the SHA-256 hash of the token, never the raw token string.
        """
        self.client.post(self.url, {"email": self.email}, format="json")

        sent_email = mail.outbox[0]
        # Extract raw token from reset link
        raw_token = sent_email.body.split("token=")[1].split()[0]

        token_record = PasswordResetToken.objects.get(user=self.user)
        # Raw token must not equal the stored token_hash
        self.assertNotEqual(token_record.token_hash, raw_token)
        # But SHA-256 of raw token must match token_hash
        self.assertEqual(
            token_record.token_hash,
            PasswordResetToken.hash_token(raw_token),
        )

    def test_subsequent_forgot_password_invalidates_prior_unconsumed_tokens(self):
        """
        Generating a new reset token consumes/invalidates any prior unconsumed tokens for the user.
        """
        # First request
        self.client.post(self.url, {"email": self.email}, format="json")
        first_token = PasswordResetToken.objects.filter(user=self.user).order_by("created_at").first()

        # Second request
        self.client.post(self.url, {"email": self.email}, format="json")
        first_token.refresh_from_db()

        self.assertTrue(first_token.is_consumed)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.user, consumed_at__isnull=True).count(), 1)

    def test_missing_or_invalid_email_returns_400_validation_error(self):
        """
        Invalid email syntax returns standard 400 VALIDATION_ERROR envelope.
        """
        response = self.client.post(
            self.url,
            {"email": "not-an-email"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertTrue(any(d["field"] == "email" for d in data["error"]["details"]))

    def test_existing_user_request_writes_audit_log_entry(self):
        response = self.client.post(self.url, {"email": self.email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        entry = AuditLog.objects.get(
            entity_type="user", entity_id=self.user.id, action="password_reset_requested"
        )
        self.assertEqual(entry.after_state["email"], self.user.email)

    def test_nonexistent_email_writes_no_audit_log_entry(self):
        response = self.client.post(
            self.url, {"email": "unknown.user@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AuditLog.objects.filter(action="password_reset_requested").count(), 0)

    def test_smtp_failure_is_logged_but_response_is_unchanged(self):
        """
        An SMTP/email-backend failure must never crash the request or
        change the client-visible response (still the identical generic
        200 message) — but it must be logged server-side, not silently
        swallowed with zero trace.
        """
        with patch(
            "django.core.mail.send_mail", side_effect=RuntimeError("SMTP connection refused")
        ), self.assertLogs("apps.authentication", level="ERROR") as logs:
            response = self.client.post(self.url, {"email": self.email}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["data"]["message"],
            "If the email is registered and active, password reset instructions have been sent.",
        )
        self.assertTrue(
            any("Failed to send password reset email" in message for message in logs.output)
        )
