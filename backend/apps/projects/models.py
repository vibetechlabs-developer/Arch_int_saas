from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class ProjectStatus(models.TextChoices):
    """
    Project lifecycle status (01_Business/FRS.md §10, CLAUDE.md "Project
    Status Lifecycle"). BE-024 defines this enum and its default only —
    the allowed-transition graph, transition authorization, and transition
    audit logging are BE-027's responsibility, not implemented here.
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
    management beyond the single `assigned_to` field is built in BE-026
    (see ProjectMember below — a documented deviation from
    Migration_Plan.md's 27 migrations, which have no project_member table).
    Status transitions are BE-027's. Filters are BE-028's. Audit
    integration is BE-029's.
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
            "04_API/Project_API.md's /team endpoints, which is the "
            "separate ProjectMember table below (BE-026), a documented "
            "deviation from Migration_Plan.md. assigned_to must belong to "
            "the same Company as this Project — enforced by "
            "validators.validate_assignee_company_membership (BE-025)."
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


class ProjectMember(BaseModel):
    """
    A user's membership on a Project's team (BE-026). Additive to, and
    independent from, `Project.assigned_to` — `assigned_to` remains the
    single documented point-of-contact field; this table is the separate
    multi-user "Team" concept `04_API/Project_API.md`'s `/team` endpoints
    document, which has no table in `Migration_Plan.md`'s original 27
    migrations. Backend Lead approved this as a documented deviation (see
    `03_Database/Migration_Plan.md` "Deviations From This Plan").

    `company` is denormalized from `project.company` (never set
    independently) purely so tenant-scoped queries and defense-in-depth
    isolation checks don't require joining through Project — the same
    reasoning `CompanyMembership` already applies to every tenant-owned
    table in this codebase.

    No project-specific role field exists on membership — not documented
    anywhere, so not invented. Removal is soft-delete only (BaseModel), so
    historical "who was on this project" data is never lost.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="project_memberships",
        db_index=True,
        help_text="Tenant company this membership belongs to (denormalized from project.company).",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
        db_index=True,
        help_text="The project this membership is for.",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_memberships",
        help_text=(
            "The member user. SET_NULL (not CASCADE) so a hard-deleted "
            "user's historical membership record is preserved, mirroring "
            "Project.assigned_to's own SET_NULL choice."
        ),
    )
    assigned_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_project_memberships",
        help_text="The user who added this member to the project, if known.",
    )

    class Meta:
        db_table = "project_member"
        ordering = ["-created_at"]
        verbose_name = "project member"
        verbose_name_plural = "project members"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_project_member",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} on {self.project_id}"
