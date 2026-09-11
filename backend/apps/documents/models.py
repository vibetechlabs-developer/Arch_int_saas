from django.db import models

from apps.common.models import BaseModel


class Document(BaseModel):
    """
    Tenant-scoped Document (BE-046) -- a file attached to a Project or to
    one of a Project's sub-entities (Quotation, Invoice, Expense, ...).
    Field set matches Database_Schema.md's `document(id, company_id,
    project_id FK, entity_type, entity_id, file_url, version,
    uploaded_by FK, uploaded_at)` exactly, with one deliberate
    simplification: no separate `uploaded_at` column. A document's upload
    moment and its row-creation moment are always the same instant (unlike
    Payment.payment_date/Expense.date, which a user can backdate to a real
    past event) -- BaseModel's own `created_at` already carries that exact
    meaning, so `DocumentSerializer` exposes it as `uploadedAt` rather than
    physically duplicating the timestamp column.

    `entity_type`/`entity_id` is the same generic polymorphic-attachment
    pattern `AuditLog` already uses (Migration_Plan.md's own note: "allows
    attaching to other entities later") -- not a real FK, since it can
    point at rows in many different tables. Defaults to `("project",
    project.id)` when a document is registered without a more specific
    target (DocumentService.create_document).

    BE-078 adds a real multipart upload path via `POST /documents/upload`
    (PRIVATE storage scope) alongside the original URL-registration flow:
    `file_storage_key`, when non-blank, means this row owns a file in this
    app's own private object storage, accessible only through the
    authenticated, tenant/RBAC-checked `GET /documents/{id}/download` proxy
    (never a permanently public or persisted-signed URL). `file_url` stays
    blank in that case -- it remains populated only for a legacy/manually-
    registered external URL, the original (BE-046) behavior, kept for
    backward compatibility with any such existing rows.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
        help_text="The tenant company this document belongs to.",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
        help_text="The project this document belongs to.",
    )
    entity_type = models.CharField(
        max_length=50,
        help_text="The kind of entity this document is attached to, e.g. 'project', 'quotation', 'invoice', 'expense'.",
    )
    entity_id = models.UUIDField(
        help_text="The specific entity's primary key. Not a real FK -- spans many entity tables.",
    )
    file_url = models.URLField(max_length=500, blank=True, default="")
    file_storage_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Internal-only (never publicly exposed). The private "
            "object-storage key backing this document, set only when it "
            "was uploaded via POST /documents/upload (BE-078). Blank for "
            "a legacy/manual file_url registration."
        ),
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Auto-assigned: next version among documents sharing this (entity_type, entity_id).",
    )
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
        help_text="The user who uploaded this document.",
    )

    class Meta:
        db_table = "document"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project"], name="document_project_idx"),
            models.Index(fields=["entity_type", "entity_id"], name="document_entity_idx"),
        ]
        verbose_name = "document"
        verbose_name_plural = "documents"

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.entity_id} v{self.version}"
