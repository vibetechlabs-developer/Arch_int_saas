from django.db import models

from apps.common.models import BaseModel


class SiteVisit(BaseModel):
    """
    Tenant-scoped Site Visit (`01_Business/FRS.md §9`, Phase 3 CRM —
    explicitly authorized to build now per Backend Lead instruction,
    ahead of the `09_Project/Roadmap.md` "Phase 3+ needs client
    confirmation" gate — see BE-062's writeup in BACKEND_TASKS.md).

    Field set is a direct transcription of FRS §9's own documented list
    ("client, project/lead, visit date, assigned person, address,
    measurements, requirements, photos, videos, notes, budget, site
    conditions, follow-up actions") — unlike Lead, this module DOES have
    a documented field list, so nothing here is invented except where
    noted below.

    `01_Business/FRS.md §9`/`03_Database/ER_Diagram.md` §2 both show a
    site visit schedulable against either a `Lead` (pre-conversion
    prospecting) or a `Project` (post-conversion, or a standalone
    existing client relationship) — `lead` and `project` are therefore
    both nullable, with `LeadService`/`SiteVisitService` responsible for
    enforcing that at least one is always set (a DB-level constraint
    can't express "at least one of two nullable FKs", so this is a
    service-layer invariant, not a migration-level one). `client` is a
    third, separately-listed FRS field — resolved automatically from
    whichever of `lead.converted_client`/`project.client` is available
    at creation time (never independently settable), so it's never out
    of sync with the actual commercial relationship this visit serves.

    No `status` field: FRS/CRM_API.md document no status vocabulary for
    Site Visit, unlike Lead (whose FRS entry explicitly names its flow
    stages) or Project (whose FRS entry explicitly names its status
    lifecycle) — inventing one here would be exactly the kind of
    undocumented vocabulary this codebase's own established discipline
    (see Lead's own docstring) avoids. `report_submitted_at` (nullable,
    set only by `SiteVisitService.submit_report`) is the one true
    lifecycle signal FRS/CRM_API.md do document ("Produces a Site Visit
    Report... POST .../report") — a site visit is "scheduled" while it
    is null and "completed" once it is set, without needing a parallel
    enum to say the same thing.

    `photo_urls`/`video_urls` (JSONField lists of plain URL strings):
    FRS lists "photos, videos" with no structure documented. Real
    storage-backed upload plumbing (the `apps.common.storage`
    abstraction BE-078 built for Documents/Expense/Payment receipts) is
    deliberately NOT extended here in this pass — Document.project is a
    required (non-nullable) FK, so it cannot represent a lead-only site
    visit that has no project yet, and widening that constraint is a
    separate, riskier change to an already-shipped, tested model that
    this task does not take on as a side effect. Plain URL lists are
    the same pre-BE-078 pattern Product/Document used before real
    uploads existed — a disclosed, deliberate MVP scope decision, not
    an oversight. A follow-up task can extend this the same way BE-078
    did for the other modules.

    `measurements`/`site_conditions`/`follow_up_actions` are free-text
    (TextField) for the same reason Lead's `source` is free text: FRS
    names the concept but documents no structured schema for it.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="site_visits",
        db_index=True,
        help_text="The tenant company this site visit belongs to.",
    )
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_visits",
        help_text="The lead this site visit was scheduled against, if any (pre-conversion prospecting).",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_visits",
        help_text="The project this site visit was scheduled against, if any.",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_visits",
        help_text="Resolved automatically from lead.converted_client/project.client at creation — never independently settable.",
    )
    visit_date = models.DateTimeField(help_text="When this site visit is scheduled to occur.")
    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_site_visits",
        help_text="The person assigned to carry out this site visit, if any.",
    )
    address = models.CharField(max_length=500, blank=True, default="", help_text="The site address to visit.")
    measurements = models.TextField(blank=True, default="", help_text="Free-text measurements captured on site.")
    requirements = models.TextField(blank=True, default="", help_text="Free-text client requirements captured on site.")
    photo_urls = models.JSONField(default=list, blank=True, help_text="List of photo URLs captured for this visit.")
    video_urls = models.JSONField(default=list, blank=True, help_text="List of video URLs captured for this visit.")
    notes = models.TextField(blank=True, default="", help_text="Free-form internal notes about this visit.")
    budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Budget discussed/estimated during this visit, if any.",
    )
    site_conditions = models.TextField(blank=True, default="", help_text="Free-text notes on the physical site conditions.")
    follow_up_actions = models.TextField(blank=True, default="", help_text="Free-text follow-up actions agreed during this visit.")
    report_submitted_at = models.DateTimeField(
        null=True, blank=True, default=None,
        help_text="Set only by SiteVisitService.submit_report — the one true completion signal for this visit.",
    )

    class Meta:
        db_table = "site_visit"
        ordering = ["-visit_date"]
        indexes = [
            models.Index(fields=["company", "visit_date"], name="sitevisit_company_date_idx"),
            models.Index(fields=["company", "assigned_to"], name="sitevisit_company_assignee_idx"),
        ]
        verbose_name = "site visit"
        verbose_name_plural = "site visits"

    def __str__(self) -> str:
        return f"Site visit @ {self.visit_date:%Y-%m-%d} ({self.company.name})"

    @property
    def is_completed(self) -> bool:
        return self.report_submitted_at is not None
