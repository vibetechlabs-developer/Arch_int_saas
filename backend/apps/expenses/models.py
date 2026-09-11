from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class ExpenseApprovalStatus(models.TextChoices):
    """
    Database_Schema.md's documented `expense.approval_status` enum,
    verbatim: `draft, submitted, approved, paid`.
    """

    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    APPROVED = "approved", _("Approved")
    PAID = "paid", _("Paid")


class Expense(BaseModel):
    """
    Tenant-scoped Expense (BE-044) -- a project cost, feeding
    `Revenue - Cost = Profit` project costing (CLAUDE.md). Field set
    matches Database_Schema.md's `expense(id, company_id, project_id FK,
    category, vendor, employee_id FK nullable, amount, tax, date,
    payment_method, receipt_url, notes, added_by (user_id),
    approval_status)` exactly.

    `category` has no documented value domain (unlike Product.unit) --
    left an unconstrained CharField, the same treatment BOQ.status/
    Payment.method got. `vendor` is plain text -- no Vendor model exists
    yet (Procurement is a Phase 4/future module, CLAUDE.md's MVP Phasing).
    `employee`/`added_by` both reference `users.User` with SET_NULL
    (mirrors Project.assigned_to's reasoning): `employee` is who the
    expense was incurred for/by (optional -- an expense might be a
    vendor-only cost with no specific employee), `added_by` is who
    recorded it (always the acting user at creation, per
    ExpenseService.create_expense).
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="expenses",
        db_index=True,
        help_text="The tenant company this expense belongs to.",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="expenses",
        db_index=True,
        help_text="The project this expense is for.",
    )
    category = models.CharField(max_length=100, blank=True, default="")
    vendor = models.CharField(max_length=255, blank=True, default="")
    employee = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incurred_expenses",
        help_text="The employee this expense relates to, if any.",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date = models.DateField()
    payment_method = models.CharField(max_length=50, blank=True, default="")
    receipt_url = models.URLField(max_length=500, blank=True, default="")
    receipt_storage_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Internal-only (never publicly exposed). The private "
            "object-storage key backing the receipt, set only when it "
            "was uploaded via POST /expenses/receipts/upload (BE-078). "
            "Blank for a legacy/manual receipt_url registration."
        ),
    )
    notes = models.TextField(blank=True, default="")
    added_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_expenses",
        help_text="The user who recorded this expense.",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ExpenseApprovalStatus.choices,
        default=ExpenseApprovalStatus.DRAFT,
        db_index=True,
    )

    class Meta:
        db_table = "expense"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["company", "project"], name="expense_comp_project_idx"),
            models.Index(fields=["company", "approval_status"], name="expense_comp_status_idx"),
        ]
        verbose_name = "expense"
        verbose_name_plural = "expenses"

    def __str__(self) -> str:
        return f"{self.category or 'Expense'}: {self.amount} ({self.project.name})"
