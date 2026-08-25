from datetime import timedelta
import hashlib
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel


class PasswordResetToken(UUIDModel, TimeStampedModel):
    """
    Stores secure single-use password reset tokens with SHA-256 hashing.
    Raw tokens are never persisted in the database.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        db_index=True,
        help_text="User requesting password reset.",
    )
    token_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hex digest of the raw cryptographic token.",
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="Timestamp after which the reset token is invalid.",
    )
    consumed_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text="Timestamp when the token was successfully used to reset password.",
    )

    class Meta:
        db_table = "password_reset_token"
        ordering = ["-created_at"]
        verbose_name = "password reset token"
        verbose_name_plural = "password reset tokens"

    def __str__(self) -> str:
        return f"PasswordResetToken for user={self.user_id} (active={self.is_valid})"

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """
        Compute SHA-256 hex digest of a raw token string.
        """
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def generate_token_for_user(
        cls,
        user,
        lifetime: timedelta | None = None,
    ) -> tuple["PasswordResetToken", str]:
        """
        Generate a cryptographically secure, unpredictable 256-bit token.
        Persists only the SHA-256 digest in the database.
        Returns the created record and the raw token string (to be sent via email).
        """
        if lifetime is None:
            lifetime = getattr(
                settings,
                "PASSWORD_RESET_TOKEN_LIFETIME",
                timedelta(hours=1),
            )

        # 32 bytes = 256 bits of cryptographic entropy
        raw_token = secrets.token_urlsafe(32)
        token_hash = cls.hash_token(raw_token)
        expires_at = timezone.now() + lifetime

        # Invalidate/expire prior unconsumed tokens for this user
        cls.objects.filter(
            user=user,
            consumed_at__isnull=True,
        ).update(consumed_at=timezone.now())

        record = cls.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return record, raw_token

    @property
    def is_valid(self) -> bool:
        """
        Check if the token is currently valid and unconsumed.
        """
        return self.consumed_at is None and self.expires_at > timezone.now()

    @property
    def is_expired(self) -> bool:
        """
        Check if the token has expired.
        """
        return self.expires_at <= timezone.now()

    @property
    def is_consumed(self) -> bool:
        """
        Check if the token has already been consumed.
        """
        return self.consumed_at is not None
