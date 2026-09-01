from django.db import models

from apps.common.models import BaseModel


class Payment(BaseModel):
    """
    Tenant-scoped Payment (BE-043) -- a record of money received against
    one Invoice. Field set matches Database_Schema.md's `payment(id,
    company_id, invoice_id FK, client_id FK, project_id FK, payment_date,
    amount, method, reference_number, receipt_url, notes)` exactly.
    `client`/`project` are denormalized off `invoice` (always derived,
    never caller-supplied) -- the same "every tenant table gets its own
    direct FK, not merely derivable through a parent" pattern
    ProductSubcategory.company established (BE-032).

    `method` has no documented value domain anywhere (unlike, say,
    Product's `unit`) -- left an unconstrained CharField rather than an
    invented enum, the same treatment BOQ.status and Expense.category got
    for the same reason.

    "Void a payment (audit-logged, not hard-deleted)" (Finance_API.md) is
    just this model's inherited SoftDeleteModel.delete() -- no separate
    status field is needed; `deleted_at` alone distinguishes a voided
    payment.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True,
        help_text="The tenant company this payment belongs to.",
    )
    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True,
        help_text="The invoice this payment is recorded against.",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True,
        help_text="The client this payment is from. Always derived from the invoice's own client.",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True,
        help_text="The project this payment relates to. Always derived from the invoice's own project.",
    )
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=50, blank=True, default="")
    reference_number = models.CharField(max_length=100, blank=True, default="")
    receipt_url = models.URLField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "payment"
        ordering = ["-payment_date", "-created_at"]
        indexes = [
            models.Index(fields=["invoice"], name="payment_invoice_idx"),
            models.Index(fields=["company", "project"], name="payment_comp_project_idx"),
        ]
        verbose_name = "payment"
        verbose_name_plural = "payments"

    def __str__(self) -> str:
        return f"{self.amount} for {self.invoice.invoice_number}"
