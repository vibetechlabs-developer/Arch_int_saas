import uuid
from django.db import models
from django.utils import timezone

from apps.common.managers import (
    SoftDeleteAllManager,
    SoftDeleteDeletedManager,
    SoftDeleteManager,
)


class UUIDModel(models.Model):
    """
    Abstract base model providing a UUID primary key.
    Enforces 'Always use UUID' architecture rule.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract base model providing created_at and updated_at timestamps in UTC.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract base model providing soft delete functionality via deleted_at timestamp.
    Preserves audit trails and history while hiding deleted records from default queries.
    """

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        editable=False,
        db_index=True,
    )

    # Managers
    objects = SoftDeleteManager()
    all_objects = SoftDeleteAllManager()
    deleted_objects = SoftDeleteDeletedManager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        """
        Check if the record has been soft-deleted.
        """
        return self.deleted_at is not None

    def delete(self, using=None, keep_parents: bool = False, hard: bool = False):
        """
        Soft delete the record by setting deleted_at.
        Pass hard=True to perform a permanent database deletion.
        """
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)

        self.deleted_at = timezone.now()
        update_fields = ["deleted_at"]
        if hasattr(self, "updated_at"):
            update_fields.append("updated_at")
        self.save(using=using, update_fields=update_fields)

    def restore(self, using=None):
        """
        Restore a soft-deleted record by clearing deleted_at.
        """
        self.deleted_at = None
        update_fields = ["deleted_at"]
        if hasattr(self, "updated_at"):
            update_fields.append("updated_at")
        self.save(using=using, update_fields=update_fields)

    def hard_delete(self, using=None, keep_parents: bool = False):
        """
        Permanently delete the record from the database.
        """
        return super().delete(using=using, keep_parents=keep_parents)


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    Comprehensive base model combining UUID primary key, audit timestamps,
    and soft deletion capabilities. All future domain models extend BaseModel.
    """

    class Meta:
        abstract = True
        ordering = ["-created_at"]
