from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class ProjectStatus(models.TextChoices):
    """
    Project lifecycle status (01_Business/FRS.md §10, CLAUDE.md "Project
    Status Lifecycle"). BE-024 defines this enum and its default only —
    the allowed-transition graph, transition authorization, and transition
    audit logging are BE-026's responsibility, not implemented here.
    """

    DRAFT = "draft", _("Draft")
    PLANNING = "planning", _("Planning")
    DESIGN = "design", _("Design")
    QUOTATION = "quotation", _("Quotation")
    APPROVED = "approved", _("Approved")
    EXECUTION = "execution", _("Execution")
    QUALITY_CHECK = "quality_check", _("Quality Check")
    HANDOVER = "handover", _("Handover")
    COMPLETED = "completed", _("Completed")
    ON_HOLD = "on_hold", _("On Hold")
    CANCELLED = "cancelled", _("Cancelled")


# Terminal statuses per Backend Lead decision (2026-08-27): a Client may be
# soft-deleted only once every one of its Projects is in one of these
# states. Every other status is "active"/blocking. Defined once here so no
# other module duplicates these string literals (apps.clients.services
# imports this, not the other way around — see apps/projects/selectors.py).
TERMINAL_PROJECT_STATUSES = (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED)


class Project(BaseModel):
    """
    Tenant-scoped Project — the central *operational* entity (FRS §10,
    02_Architecture/Solution_Architecture.md §3). Always belongs to exactly
    one Company and exactly one Client (09_Project/Module_Dependency_Map.md
    §2 step 6: "a project cannot exist without a client to belong to").

    Foundation only (BE-024): no CRUD/service/view layer yet. Team/member
    management beyond the single `assigned_to` field is BE-025's decision
    (Migration_Plan.md's 27 migrations have no project_member table — only
    this column — so BE-024 does not invent one). Status transitions are
    BE-026's. Filters are BE-027's. Audit integration is BE-028's.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="projects",
        db_index=True,
        help_text="The tenant company this project belongs to.",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.PROTECT,
        related_name="projects",
        db_index=True,
        help_text=(
            "The client this project is for. PROTECT per "
            "03_Database/Naming_Standards.md §4 — a client with existing "
            "projects must not be hard-deleted. Soft-deleting a client "
            "never triggers this (SoftDeleteModel.delete() never calls "
            "super().delete()), so historical projects keep resolving "
            "their client with no extra code."
        ),
    )
    name = models.CharField(
        max_length=255,
        help_text="Project name.",
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned project start date.",
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Planned project deadline.",
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
        db_index=True,
        help_text="Project lifecycle status.",
    )
    priority = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text=(
            "Free-text priority signal. No documented value domain exists "
            "(01_Business/FRS.md §10 names the field but never defines "
            "values) — deliberately left unconstrained per Backend Lead "
            "decision (2026-08-27) rather than inventing an enum."
        ),
    )
    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_projects",
        help_text=(
            "Single responsible user (Database_Schema.md's `assigned_to` "
            "column) — not the multi-user \"team\" concept implied by "
            "04_API/Project_API.md's /team endpoints, which has no "
            "corresponding table in Migration_Plan.md and is deferred to "
            "BE-025. Future invariant (not yet enforced — no assignment "
            "service exists yet): assigned_to must belong to the same "
            "Company as this Project."
        ),
    )
    follow_up_reminder_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional follow-up reminder timestamp.",
    )

    class Meta:
        db_table = "project"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="project_company_status_idx"),
        ]
        verbose_name = "project"
        verbose_name_plural = "projects"

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name})"
