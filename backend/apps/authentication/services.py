import logging
from typing import Any, Dict
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import exceptions as drf_exceptions
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.authentication import validators
from apps.authentication.repositories import (
    PasswordResetTokenRepository,
    TokenBlacklistRepository,
    UserRepository,
)
from apps.authentication.tokens import (
    CompanyUserRefreshToken,
    PlatformAdminRefreshToken,
)

User = get_user_model()
logger = logging.getLogger("apps.authentication")


class AuthenticationService:
    """
    Service layer for authentication, token generation, rotation, and revocation.
    Delegates persistence to apps.authentication.repositories and input
    validation to apps.authentication.validators (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model).
    """

    @staticmethod
    def _audit_email(user: Any) -> Dict[str, Any]:
        return {"email": user.email}

    @classmethod
    def _verify_credentials(cls, email: str, password: str, request: Any = None) -> Any:
        """
        Verify user credentials. Checks email case-insensitively, password,
        and account status.
        Raises drf_exceptions.AuthenticationFailed on any mismatch.

        Timing-attack mitigation: when the email doesn't match any user, the
        password hasher still runs once against a throwaway User() instance
        — mirroring Django's own ModelBackend.authenticate(), which does the
        same for the same reason (#20760) — so response timing doesn't
        reveal whether the email is registered.

        Does NOT touch last_login here — that's a caller-side side effect
        applied only once every check for the specific login path has
        passed (a regular user's failed platform-admin attempt must not
        mutate last_login just because their basic credentials were valid).
        """
        validators.require_credentials(email, password)

        user = UserRepository.get_active_by_email(email)

        if user is None:
            User().set_password(password)
            raise drf_exceptions.AuthenticationFailed(validators.GENERIC_AUTH_ERROR)

        if not user.check_password(password) or not user.is_active:
            AuditLogService.record(
                action=AuditAction.LOGIN_FAILURE,
                entity_type="user",
                entity_id=user.id,
                actor_user=user,
                after_state=cls._audit_email(user),
                request=request,
            )
            raise drf_exceptions.AuthenticationFailed(validators.GENERIC_AUTH_ERROR)

        return user

    @classmethod
    def login_company_user(cls, email: str, password: str, request: Any = None) -> Dict[str, Any]:
        """
        Authenticate a company user and return access and refresh tokens.
        """
        user = cls._verify_credentials(email, password, request=request)
        UserRepository.touch_last_login(user)
        refresh = CompanyUserRefreshToken.for_user(user)

        AuditLogService.record(
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="user",
            entity_id=user.id,
            actor_user=user,
            after_state=cls._audit_email(user),
            request=request,
        )

        return {
            "accessToken": str(refresh.access_token),
            "refreshToken": str(refresh),
            "user": user,
        }

    @classmethod
    def login_platform_admin(cls, email: str, password: str, request: Any = None) -> Dict[str, Any]:
        """
        Authenticate a platform super admin and return access and refresh tokens.
        """
        user = cls._verify_credentials(email, password, request=request)

        if not (user.is_superuser and user.is_staff):
            AuditLogService.record(
                action=AuditAction.LOGIN_FAILURE,
                entity_type="user",
                entity_id=user.id,
                actor_user=user,
                after_state=cls._audit_email(user),
                request=request,
            )
            raise drf_exceptions.AuthenticationFailed(validators.GENERIC_AUTH_ERROR)

        UserRepository.touch_last_login(user)
        refresh = PlatformAdminRefreshToken.for_user(user)

        AuditLogService.record(
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="user",
            entity_id=user.id,
            actor_user=user,
            after_state=cls._audit_email(user),
            request=request,
        )

        return {
            "accessToken": str(refresh.access_token),
            "refreshToken": str(refresh),
            "user": user,
        }

    @staticmethod
    def refresh_token(refresh_token_str: str, request: Any = None) -> Dict[str, str]:
        """
        Exchange a valid refresh token for a new access token and rotated refresh token.

        Privilege re-verification (hardened): the prior implementation
        trusted the incoming token's own `user_type` claim to decide
        whether the new access token carries platform-admin privileges. A
        refresh token issued before an admin's privileges were revoked
        could keep minting valid platform-admin access tokens until the
        refresh token itself expired (up to REFRESH_TOKEN_LIFETIME later).
        This now re-queries the user's *current* is_active/is_superuser/
        is_staff state on every refresh and rejects outright if the claimed
        admin privilege no longer holds, rather than re-minting it from the
        stale claim.
        """
        validators.require_refresh_token_str(refresh_token_str)

        try:
            refresh = RefreshToken(refresh_token_str)

            user_id = refresh.payload.get("sub")
            user = UserRepository.get_by_id(user_id)

            if user is None or not user.is_active:
                raise drf_exceptions.AuthenticationFailed(validators.GENERIC_AUTH_ERROR)

            claimed_user_type = refresh.payload.get("user_type", "company_user")
            is_admin_now = bool(user.is_superuser and user.is_staff)

            if claimed_user_type == "platform_admin" and not is_admin_now:
                raise drf_exceptions.AuthenticationFailed(validators.GENERIC_AUTH_ERROR)

            current_user_type = "platform_admin" if is_admin_now else "company_user"

            access_token = refresh.access_token
            access_token.token_type = current_user_type
            access_token["user_type"] = current_user_type
            access_token["email"] = user.email

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

            AuditLogService.record(
                action=AuditAction.TOKEN_REFRESH,
                entity_type="user",
                entity_id=user.id,
                actor_user=user,
                after_state={"email": user.email},
                request=request,
            )

            return result

        except (TokenError, InvalidToken) as exc:
            raise drf_exceptions.AuthenticationFailed(validators.GENERIC_AUTH_ERROR) from exc

    @staticmethod
    def logout(refresh_token_str: str, request: Any = None) -> None:
        """
        Revoke/blacklist the given refresh token.
        """
        validators.require_refresh_token_str(refresh_token_str)

        try:
            refresh = RefreshToken(refresh_token_str)
            user_id = refresh.payload.get("sub")
            refresh.blacklist()
        except (TokenError, InvalidToken) as exc:
            raise drf_exceptions.AuthenticationFailed(validators.GENERIC_AUTH_ERROR) from exc

        user = UserRepository.get_by_id(user_id)
        if user is not None:
            AuditLogService.record(
                action=AuditAction.LOGOUT,
                entity_type="user",
                entity_id=user.id,
                actor_user=user,
                after_state={"email": user.email},
                request=request,
            )

    @classmethod
    def request_password_reset(cls, email: str, request: Any = None) -> str:
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

        user = UserRepository.get_active_by_email(email.strip().lower())

        if user is not None and user.is_active:
            _record, raw_token = PasswordResetTokenRepository.create_for_user(user)
            PasswordResetEmailService.send_password_reset_email(user, raw_token)
            AuditLogService.record(
                action=AuditAction.PASSWORD_RESET_REQUESTED,
                entity_type="user",
                entity_id=user.id,
                actor_user=user,
                after_state=cls._audit_email(user),
                request=request,
            )

        return generic_message

    @classmethod
    def reset_password(cls, token: str, new_password: str, request: Any = None) -> str:
        """
        Validate reset token, validate new password against Django validators,
        update password, consume token, and invalidate existing active sessions.
        """
        validators.require_reset_token_str(token)
        validators.require_new_password_str(new_password)

        token_record = PasswordResetTokenRepository.get_by_raw_token(token)

        if token_record is None or not token_record.is_valid:
            raise drf_exceptions.AuthenticationFailed(validators.GENERIC_RESET_TOKEN_ERROR)

        user = token_record.user
        if user is None or not user.is_active:
            raise drf_exceptions.AuthenticationFailed(validators.GENERIC_RESET_TOKEN_ERROR)

        validators.validate_new_password_strength(new_password, user)

        # Atomic update of password, token consumption, and session invalidation
        with transaction.atomic():
            UserRepository.set_password(user, new_password)
            PasswordResetTokenRepository.mark_consumed(token_record)
            TokenBlacklistRepository.blacklist_all_outstanding_for_user(user)

            AuditLogService.record(
                action=AuditAction.PASSWORD_RESET_COMPLETED,
                entity_type="user",
                entity_id=user.id,
                actor_user=user,
                after_state=cls._audit_email(user),
                request=request,
            )

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
            # Delivery failures must not crash the auth flow or reveal
            # account state to the client (the caller's response is
            # unaffected either way) — but they must not be silently
            # invisible server-side either.
            logger.exception(
                "Failed to send password reset email",
                extra={"user_id": str(user.id)},
            )
