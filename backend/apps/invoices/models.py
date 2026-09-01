from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.products.models import ProductUnit


class InvoiceStatus(models.TextChoices):
    """
    Database_Schema.md's documented `invoice.status` enum, verbatim:
    `draft, sent, partially_paid, paid, overdue, cancelled`.

    Backend Lead decision (AskUserQuestion, Sprint 6 planning): only
    draft/sent/partially_paid/paid/cancelled are ever persisted here.
    `overdue` is never stored -- Finance_API.md's own text says invoice
    status is "derived server-side from paid-vs-total amount and due
    date", and this sprint has no scheduled/cron job to sweep invoices
    daily. Instead, `InvoiceSerializer` computes `overdue` at read time
    (sent/partially_paid + a past due_date), so it's always accurate
    without any background infrastructure. See
    InvoiceService.compute_effective_status.
    """

    DRAFT = "draft", _("Draft")
    SENT = "sent", _("Sent")
    PARTIALLY_PAID = "partially_paid", _("Partially Paid")
    PAID = "paid", _("Paid")
    OVERDUE = "overdue", _("Overdue")
    CANCELLED = "cancelled", _("Cancelled")


class Invoice(BaseModel):
    """
    Tenant-scoped Invoice (BE-042) -- the financial-lifecycle bridge from
    an approved Quotation (or an ad hoc line-item list) to Payment.
    Field set matches Database_Schema.md's `invoice(id, company_id,
    project_id FK, contract_id FK nullable, quotation_id FK nullable,
    invoice_number, client_id FK, subtotal, discount, tax, total,
    due_date, payment_terms, status, notes)` -- with one deliberate
    omission: **no `contract_id` column**. `Contract` is not part of this
    build's scope -- CLAUDE.md's Module Dependency Map (binding build
    order) and BACKEND_TASKS.md's Sprint list both go straight from
    Quotation to Invoice with no Contract step, and
    "Never implement future modules unless instructed" (Engineering
    Execution Rules) forbids adding a table this build order doesn't call
    for just to satisfy an FK that would sit permanently null. `quotation`
    is therefore the only commercial-document link; Finance_API.md's
    "from contract/approved quotation, or ad hoc" becomes "from an
    approved quotation, or ad hoc" here.

    `invoice_number` is per-company sequential ("INV-000001"), the same
    scheme and non-atomic count()+1 generation
    QuotationRepository.next_quote_number established (BE-039) -- an
    already-approved Backend Lead decision, not re-litigated here.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="invoices",
        db_index=True,
        help_text="The tenant company this invoice belongs to.",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="invoices",
        db_index=True,
        help_text="The project this invoice is for.",
    )
    quotation = models.ForeignKey(
        "quotations.Quotation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        help_text="The approved quotation this invoice was generated from, if any. Null for an ad hoc invoice.",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="invoices",
        db_index=True,
        help_text="The client this invoice is for. Always derived from the project's own client, never caller-supplied.",
    )
    invoice_number = models.CharField(max_length=50, db_index=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    payment_terms = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=30,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True,
        help_text="Persisted base status. Never 'overdue' -- see InvoiceStatus docstring.",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "invoice"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project"], name="invoice_project_idx"),
            models.Index(fields=["company", "invoice_number"], name="invoice_comp_number_idx"),
        ]
        verbose_name = "invoice"
        verbose_name_plural = "invoices"

    def __str__(self) -> str:
        return f"{self.invoice_number} ({self.project.name})"


class InvoiceItem(BaseModel):
    """
    A single line item within an Invoice (BE-042). Field set matches
    Database_Schema.md's `invoice_item(id, invoice_id FK, description,
    quantity, unit, rate, amount)` exactly -- unlike QuotationItem/
    BOQItem, there is deliberately **no `product_id` FK** here (the
    literal schema lists none); an invoice line is always a frozen
    description/quantity/rate snapshot, never a live catalog reference.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
        help_text="The invoice this item belongs to.",
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
        db_table = "invoice_item"
        ordering = ["created_at"]
        verbose_name = "invoice item"
        verbose_name_plural = "invoice items"

    def __str__(self) -> str:
        return f"{self.description} ({self.invoice_id})"
