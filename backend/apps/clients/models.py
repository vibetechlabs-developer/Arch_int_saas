from django.db import models

from apps.common.models import BaseModel


class Client(BaseModel):
    """
    Tenant-scoped Client (the central commercial entity — 01_Business/FRS.md
    §7, 03_Database/Database_Schema.md). Reusable across multiple Projects
    within the same company. Field set and column list match
    Database_Schema.md's `client` table exactly — no undocumented fields
    (e.g. no `is_active`/status column, no uniqueness constraint) have been
    added.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="clients",
        db_index=True,
        help_text="The tenant company this client belongs to.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Client's primary contact/individual name.",
    )
    company_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="The client's own business/trading name, if applicable.",
    )
    email = models.EmailField(
        blank=True,
        help_text="Client's primary contact email address.",
    )
    mobile = models.CharField(
        max_length=20,
        blank=True,
        help_text="Client's primary contact mobile number.",
    )
    gstin = models.CharField(
        max_length=15,
        blank=True,
        help_text="Client's GST Identification Number (GSTIN), if applicable.",
    )
    addresses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of address records for this client (shape not yet standardized).",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Free-form internal notes about this client.",
    )

    class Meta:
        db_table = "client"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "name"], name="client_company_name_idx"),
        ]
        verbose_name = "client"
        verbose_name_plural = "clients"

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name})"
