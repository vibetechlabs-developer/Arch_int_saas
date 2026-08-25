from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet providing soft delete, restore, and filtering capabilities.
    """

    def delete(self, hard: bool = False):
        """
        Soft delete by default by setting deleted_at timestamp.
        Pass hard=True to permanently delete from the database.
        """
        if hard:
            return super().delete()
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """
        Permanently delete matching records from the database.
        """
        return super().delete()

    def restore(self):
        """
        Restore soft-deleted records by clearing the deleted_at timestamp.
        """
        return self.update(deleted_at=None)

    def alive(self):
        """
        Filter to only active (non-deleted) records.
        """
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """
        Filter to only soft-deleted records.
        """
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """
    Default manager that filters out soft-deleted records.
    """

    _queryset_class = SoftDeleteQuerySet

    def get_queryset(self) -> SoftDeleteQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=True)

    def hard_delete(self):
        return self.get_queryset().hard_delete()

    def restore(self):
        return self.get_queryset().restore()

    def alive(self) -> SoftDeleteQuerySet:
        return self.get_queryset().alive()

    def deleted(self) -> SoftDeleteQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=False)


class SoftDeleteAllManager(models.Manager):
    """
    Manager that includes both active and soft-deleted records.
    """

    _queryset_class = SoftDeleteQuerySet

    def get_queryset(self) -> SoftDeleteQuerySet:
        return super().get_queryset()

    def alive(self) -> SoftDeleteQuerySet:
        return self.get_queryset().filter(deleted_at__isnull=True)

    def deleted(self) -> SoftDeleteQuerySet:
        return self.get_queryset().filter(deleted_at__isnull=False)


class SoftDeleteDeletedManager(models.Manager):
    """
    Manager that returns only soft-deleted records.
    """

    _queryset_class = SoftDeleteQuerySet

    def get_queryset(self) -> SoftDeleteQuerySet:
        return super().get_queryset().filter(deleted_at__isnull=False)

    def restore(self):
        return self.get_queryset().restore()

    def hard_delete(self):
        return self.get_queryset().hard_delete()
