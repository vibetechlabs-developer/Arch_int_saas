from typing import Any, List, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.authentication.models import PasswordResetToken

User = get_user_model()


class UserRepository:
    """
    Data-access layer for authentication-related User lookups/writes.
    """

    @staticmethod
    def get_active_by_email(email: str) -> Optional[Any]:
        # User.objects uses SoftDeleteManager (automatically filters deleted_at is null)
        return User.objects.filter(email__iexact=email.strip()).first()

    @staticmethod
    def touch_last_login(user: Any) -> None:
        update_last_login(None, user)

    @staticmethod
    def set_password(user: Any, new_password: str) -> None:
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])


class PasswordResetTokenRepository:
    """
    Data-access layer for PasswordResetToken.
    """

    @staticmethod
    def create_for_user(user: Any) -> tuple[PasswordResetToken, str]:
        return PasswordResetToken.generate_token_for_user(user)

    @staticmethod
    def get_by_raw_token(raw_token: str) -> Optional[PasswordResetToken]:
        token_hash = PasswordResetToken.hash_token(raw_token.strip())
        return (
            PasswordResetToken.objects.filter(token_hash=token_hash)
            .select_related("user")
            .first()
        )

    @staticmethod
    def mark_consumed(token_record: PasswordResetToken) -> None:
        token_record.consumed_at = timezone.now()
        token_record.save(update_fields=["consumed_at", "updated_at"])


class TokenBlacklistRepository:
    """
    Data-access layer for SimpleJWT's outstanding/blacklisted refresh tokens.
    """

    @staticmethod
    def blacklist_all_outstanding_for_user(user: Any) -> None:
        outstanding_tokens: List[OutstandingToken] = OutstandingToken.objects.filter(user=user)
        for outstanding in outstanding_tokens:
            BlacklistedToken.objects.get_or_create(token=outstanding)
