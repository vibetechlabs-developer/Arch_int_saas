from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import UUIDModel


class AuditAction(models.TextChoices):
    """
    Action taxonomy for AuditLog entries — matches 03_Database/Database_Schema.md's
    documented audit_log.action value set exactly (create/update/delete/approve).
    A status change is recorded as an UPDATE with the status field visible in
    before_state/after_state, not a separate action value.
    """
    CREATE = "create", _("Create")
    UPDATE = "update", _("Update")
    DELETE = "delete", _("Delete")
    APPROVE = "approve", _("Approve")


class AuditLog(UUIDModel):
    """
    Durable, append-only, never-expired record of who changed what
    (00_Development_Standards/Logging_Standards.md §5, 01_Business/FRS.md §27).

    Deliberately extends UUIDModel only, not BaseModel: an audit row is
    immutable (no updated_at — nothing about an entry is ever updated after
    creation) and never soft-deleted (deleted_at would defeat the
    "never-expired" requirement). See apps/audit/repositories.py — the
    repository exposes create/read only, enforcing this at the application
    layer as well.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "The tenant this entry concerns. Null for platform-level actions "
            "with no company context — the one deliberate exception to the "
            "usual NOT NULL tenant-scope rule (Database_Schema.md). Also set "
            "null (not cascade-deleted) if the company is ever hard-deleted — "
            "the audit row itself must outlive the tenant record, per the "
            "'never-expired' requirement this model exists to satisfy."
        ),
    )
    actor_user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
        db_index=True,
        help_text=_("The user who performed the action. Null for system/automated actions."),
    )
    entity_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Module-level entity name, e.g. 'role', 'company'."),
    )
    entity_id = models.UUIDField(
        db_index=True,
        help_text=_("Primary key of the affected record. Not a FK — spans many entity tables."),
    )
    action = models.CharField(
        max_length=20,
        choices=AuditAction.choices,
        db_index=True,
    )
    before_state = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Allowlisted field snapshot before the change. Null for create."),
    )
    after_state = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Allowlisted field snapshot after the change. Null for delete."),
    )
    request_id = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text=_("Correlates to the same requestId in operational logs and API responses."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    user_agent = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
    )

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        verbose_name = "audit log entry"
        verbose_name_plural = "audit log entries"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["company", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id} @ {self.created_at}"
