from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


def get_default_company_settings() -> dict:
    """
    Returns default tenant configuration and preferences.
    """
    return {
        "numbering": {},
        "paymentTerms": {},
        "notificationPrefs": {},
    }


class CompanyStatus(models.TextChoices):
    """
    Status choices for Company tenants.
    """
    TRIAL = "trial", _("Trial")
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")


class Company(BaseModel):
    """
    Company (Tenant) Model for INT Projects SaaS.
    Acts as the multi-tenant isolation root for all company-scoped domain data.
    """

    name = models.CharField(
        max_length=255,
        help_text=_("Company trading or legal name."),
    )
    status = models.CharField(
        max_length=50,
        choices=CompanyStatus.choices,
        default=CompanyStatus.TRIAL,
        db_index=True,
        help_text=_("Subscription lifecycle status."),
    )
    currency = models.CharField(
        max_length=10,
        default="INR",
        help_text=_("Default currency code (e.g. INR, USD)."),
    )
    gst_number = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        help_text=_("Goods and Services Tax Identification Number (GSTIN)."),
    )
    settings = models.JSONField(
        default=get_default_company_settings,
        blank=True,
        help_text=_("Tenant-specific configuration and preferences."),
    )

    class Meta:
        db_table = "company"
        ordering = ["-created_at"]
        verbose_name = "company"
        verbose_name_plural = "companies"

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"
