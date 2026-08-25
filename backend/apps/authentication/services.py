from typing import Any, Dict
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from rest_framework import exceptions as drf_exceptions
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.tokens import (
    CompanyUserRefreshToken,
    PlatformAdminRefreshToken,
)

User = get_user_model()


class AuthenticationService:
    """
    Service layer for authentication, token generation, rotation, and revocation.
    """

    @staticmethod
    def _verify_credentials(email: str, password: str) -> Any:
        """
        Verify user credentials. Checks email case-insensitively, password,
        and account status.
        Raises drf_exceptions.AuthenticationFailed on any mismatch.
        """
        if not email or not password:
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            )

        # User.objects uses SoftDeleteManager (automatically filters deleted_at is null)
        user = User.objects.filter(email__iexact=email.strip()).first()

        if user is None:
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            )

        if not user.check_password(password):
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            )

        if not user.is_active:
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            )

        # Update last login timestamp
        update_last_login(None, user)
        return user

    @classmethod
    def login_company_user(cls, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a company user and return access and refresh tokens.
        """
        user = cls._verify_credentials(email, password)
        refresh = CompanyUserRefreshToken.for_user(user)

        return {
            "accessToken": str(refresh.access_token),
            "refreshToken": str(refresh),
            "user": user,
        }

    @classmethod
    def login_platform_admin(cls, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a platform super admin and return access and refresh tokens.
        """
        user = cls._verify_credentials(email, password)

        if not (user.is_superuser and user.is_staff):
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            )

        refresh = PlatformAdminRefreshToken.for_user(user)

        return {
            "accessToken": str(refresh.access_token),
            "refreshToken": str(refresh),
            "user": user,
        }

    @staticmethod
    def refresh_token(refresh_token_str: str) -> Dict[str, str]:
        """
        Exchange a valid refresh token for a new access token and rotated refresh token.
        """
        if not refresh_token_str or not isinstance(refresh_token_str, str):
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            )

        try:
            refresh = RefreshToken(refresh_token_str)

            # Preserve user type claim if present
            user_type = refresh.payload.get("user_type", "company_user")
            email = refresh.payload.get("email", "")

            # Set claims on the newly generated access token
            access_token = refresh.access_token
            if user_type == "platform_admin":
                access_token.token_type = "platform_admin"
            else:
                access_token.token_type = "company_user"

            access_token["user_type"] = user_type
            if email:
                access_token["email"] = email

            result = {"accessToken": str(access_token)}

            if api_settings.ROTATE_REFRESH_TOKENS:
                if api_settings.BLACKLIST_AFTER_ROTATION:
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass

                refresh.set_jti()
                refresh.set_exp()
                refresh.set_iat()
                result["refreshToken"] = str(refresh)

            return result

        except (TokenError, InvalidToken) as exc:
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            ) from exc

    @staticmethod
    def logout(refresh_token_str: str) -> None:
        """
        Revoke/blacklist the given refresh token.
        """
        if not refresh_token_str or not isinstance(refresh_token_str, str):
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            )

        try:
            refresh = RefreshToken(refresh_token_str)
            refresh.blacklist()
        except (TokenError, InvalidToken) as exc:
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired authentication credentials."
            ) from exc

    @classmethod
    def request_password_reset(cls, email: str) -> str:
        """
        Initiate password reset workflow.
        Generates a secure single-use token and sends reset email if the user exists and is active.
        Guarantees identical return message regardless of account state to prevent enumeration.
        """
        generic_message = (
            "If the email is registered and active, password reset instructions have been sent."
        )

        if not email or not isinstance(email, str):
            return generic_message

        normalized_email = email.strip().lower()
        user = User.objects.filter(email__iexact=normalized_email).first()

        if user is not None and user.is_active:
            from apps.authentication.models import PasswordResetToken
            record, raw_token = PasswordResetToken.generate_token_for_user(user)
            PasswordResetEmailService.send_password_reset_email(user, raw_token)

        return generic_message

    @classmethod
    def reset_password(cls, token: str, new_password: str) -> str:
        """
        Validate reset token, validate new password against Django validators,
        update password, consume token, and invalidate existing active sessions.
        """
        if not token or not isinstance(token, str):
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired password reset token."
            )

        if not new_password or not isinstance(new_password, str):
            raise drf_exceptions.ValidationError(
                {"newPassword": "New password must be provided."}
            )

        from apps.authentication.models import PasswordResetToken
        token_hash = PasswordResetToken.hash_token(token.strip())

        token_record = (
            PasswordResetToken.objects.filter(token_hash=token_hash)
            .select_related("user")
            .first()
        )

        if token_record is None or not token_record.is_valid:
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired password reset token."
            )

        user = token_record.user
        if user is None or not user.is_active:
            raise drf_exceptions.AuthenticationFailed(
                "Invalid or expired password reset token."
            )

        # Validate password complexity against configured AUTH_PASSWORD_VALIDATORS
        from django.contrib.auth.password_validation import validate_password
        validate_password(new_password, user=user)

        # Atomic update of password, token consumption, and session invalidation
        from django.db import transaction
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password", "updated_at"])

            token_record.consumed_at = timezone.now()
            token_record.save(update_fields=["consumed_at", "updated_at"])

            # Invalidate/blacklist all existing refresh tokens for this user
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for outstanding in outstanding_tokens:
                BlacklistedToken.objects.get_or_create(token=outstanding)

        return "Password has been reset successfully."


class PasswordResetEmailService:
    """
    Service for formatting and dispatching password reset emails.
    """

    @staticmethod
    def send_password_reset_email(user, raw_token: str) -> None:
        """
        Send password reset email to user containing the secure reset URL.
        """
        from django.conf import settings
        from django.core.mail import send_mail

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        reset_link = f"{frontend_url}/reset-password?token={raw_token}"
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@intprojects.com")

        subject = "Reset Your INT Projects SaaS Password"
        message = (
            f"Hello {user.name},\n\n"
            f"We received a request to reset your password for INT Projects SaaS.\n\n"
            f"Please click the link below to set a new password:\n"
            f"{reset_link}\n\n"
            f"This link is single-use and will expire in 1 hour.\n"
            f"If you did not request a password reset, you can safely ignore this email.\n\n"
            f"Regards,\nINT Projects Security Team"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            # Email delivery failures must not crash the auth flow or reveal state to the client
            pass

