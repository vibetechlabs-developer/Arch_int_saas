from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.products.models import ProductUnit


class QuotationStatus(models.TextChoices):
    """
    Database_Schema.md's documented `quotation.status` enum, verbatim:
    `draft, internal_review, sent, revision_requested, approved, rejected`.

    Backend Lead decisions (AskUserQuestion, Sprint 5 planning):
    - `internal_review` has no dedicated transition endpoint — Finance_API.md's
      endpoint table (create/revise/send/approve/reject) never reaches it, so
      it stays in the enum for future/manual use but the API only enforces
      `draft -> sent -> approved/rejected`.
    - `revision_requested` is likewise never set by the API — `/reject`
      always sets the terminal `rejected`; a client asking for changes
      instead is handled by staff calling `/revise` directly, which creates
      a new `draft` version.
    """

    DRAFT = "draft", _("Draft")
    INTERNAL_REVIEW = "internal_review", _("Internal Review")
    SENT = "sent", _("Sent")
    REVISION_REQUESTED = "revision_requested", _("Revision Requested")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class Quotation(BaseModel):
    """
    Tenant-scoped Quotation (BE-039) — bridges a Project's BOQ to a
    commercial agreement (CLAUDE.md: "Project → BOQ → Create Quotation →
    Internal Review → Send to Client → Client Review → (Revision → new
    version) | (Approval)"). Field set matches Database_Schema.md's
    `quotation(id, company_id, project_id FK, boq_id FK nullable,
    quote_number, version, client_id FK, subtotal, discount, tax, total,
    terms, payment_schedule JSONB, valid_until, status, notes)` exactly.

    Versioning (Backend Lead decision, AskUserQuestion, Sprint 5 planning):
    a revision reuses the same `quote_number` and increments `version`
    (Database_Schema.md's own two columns — no undocumented parent FK
    added). `(company, quote_number, version)` is unique — the constraint
    that actually backs "no forked history" at the DB level; see
    QuotationService.revise_quotation's additional "must be the latest
    version" application-level guard.

    `subtotal`/`discount`/`tax`/`total` are stored as absolute currency
    amounts (NUMERIC(14,2)), not percentages — when created from a BOQ they
    are copied directly from BOQSummaryService.compute_summary's identical
    {subtotal, discount, tax, total} dict shape; when created manually,
    discount/tax are flat amounts entered directly in the request (unlike
    BOQItem's per-item percentage fields, which don't apply here since
    QuotationItem carries no discount/tax column of its own — matches
    Database_Schema.md's `quotation_item` column list literally).
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="quotations",
        db_index=True,
        help_text="The tenant company this quotation belongs to.",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="quotations",
        db_index=True,
        help_text="The project this quotation is for.",
    )
    boq = models.ForeignKey(
        "boq.BOQ",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotations",
        help_text="The BOQ this quotation was generated from, if any. Null for a manually-built quotation.",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="quotations",
        db_index=True,
        help_text="The client this quotation is for. Always derived from the project's own client, never caller-supplied.",
    )
    quote_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Per-company sequential quote number (e.g. QT-000001), shared across every version of the same quotation.",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Version number within this quote_number's revision chain. Starts at 1.",
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    terms = models.TextField(blank=True, default="")
    payment_schedule = models.JSONField(
        default=list,
        blank=True,
        help_text="Free-form payment schedule structure (e.g. milestone/percentage/amount entries).",
    )
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=QuotationStatus.choices,
        default=QuotationStatus.DRAFT,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "quotation"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "quote_number", "version"],
                name="quotation_comp_qnum_version_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["project"], name="quotation_project_idx"),
            models.Index(fields=["company", "quote_number"], name="quotation_comp_qnum_idx"),
        ]
        verbose_name = "quotation"
        verbose_name_plural = "quotations"

    def __str__(self) -> str:
        return f"{self.quote_number} v{self.version} ({self.project.name})"


class QuotationItem(BaseModel):
    """
    A single line item within a Quotation (BE-039). Field set matches
    Database_Schema.md's `quotation_item(id, quotation_id FK, product_id FK
    nullable, description, quantity, unit, rate, amount)` exactly — like
    boq_item, deliberately no `company` column (tenant scoping resolves
    through `quotation.company_id`) and no discount/tax column of its own
    (those live at the Quotation level here, unlike BOQItem).

    No independent CRUD endpoint exists for QuotationItem (Finance_API.md
    documents none) — items are only ever created as part of
    QuotationService.create_quotation/revise_quotation, so no
    repository.save()/soft_delete() beyond create is needed.
    """

    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
        help_text="The quotation this item belongs to.",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotation_items",
        help_text="Optional catalog product reference. Null for a free-text item.",
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(
        max_length=20,
        choices=ProductUnit.choices,
        blank=True,
        default="",
    )
    rate = models.DecimalField(max_digits=14, decimal_places=2)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Server-computed: quantity * rate. Never client-writable.",
    )

    class Meta:
        db_table = "quotation_item"
        ordering = ["created_at"]
        verbose_name = "quotation item"
        verbose_name_plural = "quotation items"

    def __str__(self) -> str:
        return f"{self.description} ({self.quotation_id})"
