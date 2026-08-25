from typing import Any

from django.contrib.auth.password_validation import validate_password
from rest_framework import exceptions as drf_exceptions

GENERIC_AUTH_ERROR = "Invalid or expired authentication credentials."
GENERIC_RESET_TOKEN_ERROR = "Invalid or expired password reset token."


def require_credentials(email: str, password: str) -> None:
    if not email or not password:
        raise drf_exceptions.AuthenticationFailed(GENERIC_AUTH_ERROR)


def require_refresh_token_str(refresh_token_str: str) -> None:
    if not refresh_token_str or not isinstance(refresh_token_str, str):
        raise drf_exceptions.AuthenticationFailed(GENERIC_AUTH_ERROR)


def require_reset_token_str(token: str) -> None:
    if not token or not isinstance(token, str):
        raise drf_exceptions.AuthenticationFailed(GENERIC_RESET_TOKEN_ERROR)


def require_new_password_str(new_password: str) -> None:
    if not new_password or not isinstance(new_password, str):
        raise drf_exceptions.ValidationError({"newPassword": "New password must be provided."})


def validate_new_password_strength(new_password: str, user: Any) -> None:
    """
    Validate password complexity against configured AUTH_PASSWORD_VALIDATORS.
    """
    validate_password(new_password, user=user)
