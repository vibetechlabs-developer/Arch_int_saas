from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class LeadStatus(models.TextChoices):
    """
    Lead lifecycle status (BE-061). `01_Business/FRS.md §8` documents only
    the flow itself ("Lead → Qualification → Follow-up → Site Visit →
    Won → Client → Project") and the loss requirement ("Lost leads
    require a loss reason and optional future follow-up date") — no
    field list or exact status vocabulary. These values are a direct,
    literal transcription of that documented flow (Backend Lead
    decision), not an invented workflow: NEW (a lead exists, not yet
    worked), QUALIFIED, FOLLOW_UP, SITE_VISIT_SCHEDULED (a lead-lifecycle
    marker only — the real Site Visit module, `03_Database/
    Migration_Plan.md`'s own explicit Phase 3+ table, is NOT built here),
    WON, LOST.
    """

    NEW = "new", _("New")
    QUALIFIED = "qualified", _("Qualified")
    FOLLOW_UP = "follow_up", _("Follow-up")
    SITE_VISIT_SCHEDULED = "site_visit_scheduled", _("Site Visit Scheduled")
    WON = "won", _("Won")
    LOST = "lost", _("Lost")


#: Terminal statuses — no outgoing transitions via the plain
#: `PATCH /leads/{id}/status` endpoint. WON is reachable ONLY through
#: `POST /leads/{id}/convert` (LeadService.convert_lead), never through a
#: plain status PATCH — converting has real side effects (creating a real
#: Client, optionally a Project) that a bare status flip must never be
#: able to skip, so a lead can never end up "won" with no converted
#: Client behind it.
TERMINAL_LEAD_STATUSES = (LeadStatus.WON, LeadStatus.LOST)

#: The documented forward chain, stopping short of WON for the reason
#: above. LOST is a side-transition reachable from any non-terminal
#: status (mirrors apps.projects.models's ON_HOLD/CANCELLED side-state
#: pattern), not part of this chain.
MAIN_CHAIN_STATUSES = (
    LeadStatus.NEW,
    LeadStatus.QUALIFIED,
    LeadStatus.FOLLOW_UP,
    LeadStatus.SITE_VISIT_SCHEDULED,
)

NEXT_MAIN_CHAIN_STATUS = {
    MAIN_CHAIN_STATUSES[i]: MAIN_CHAIN_STATUSES[i + 1]
    for i in range(len(MAIN_CHAIN_STATUSES) - 1)
}


def get_allowed_next_statuses(current_status: str) -> set:
    """
    The BE-061 status transition graph for the plain
    `PATCH /leads/{id}/status` endpoint (mirrors
    apps.projects.models.get_allowed_next_statuses's structure, simplified
    since Lead has no ON_HOLD-style pause/resume state):

    1. A terminal status (WON, LOST) has no outgoing transitions.
    2. Any other status may move to LOST directly (a lead can be
       abandoned from any live stage).
    3. Every MAIN_CHAIN_STATUSES status may also move one step forward
       to its documented successor — forward-only, one step at a time,
       no skipping, no backward moves.
    4. WON is deliberately never in this set — see TERMINAL_LEAD_STATUSES'
       docstring.
    """
    if current_status in TERMINAL_LEAD_STATUSES:
        return set()

    allowed = {LeadStatus.LOST}
    next_status = NEXT_MAIN_CHAIN_STATUS.get(current_status)
    if next_status:
        allowed.add(next_status)

    return allowed


class Lead(BaseModel):
    """
    Tenant-scoped Lead (`01_Business/FRS.md §8`, Phase 3 CRM — explicitly
    authorized to build now per Backend Lead instruction, ahead of the
    `09_Project/Roadmap.md` "Phase 3+ needs client confirmation" gate).

    Field set (Backend Lead decision — FRS.md documents only the status
    flow and the loss-reason/follow-up-date requirement, no field list,
    unlike Client's explicit "Name, Company, Email, Mobile, GSTIN"):
    `name`/`company_name`/`email`/`mobile` deliberately mirror Client's
    own identity fields exactly, since a Lead becomes a Client verbatim
    on conversion (`LeadService.convert_lead`) — carrying the same field
    names avoids a lossy or invented mapping at that point. `source` is
    free text (no invented closed vocabulary) since the concept is
    universal to any lead-capture flow but no format is documented.
    `assignedTo` is directly implied by `04_API/CRM_API.md`'s own
    `GET /leads` sketch ("filter: status, assigned to"), not invented.
    No `gstin`/`addresses` — those are documented Client-only fields
    (FRS §7), not part of a lead's own pre-qualification data.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="leads",
        db_index=True,
        help_text="The tenant company this lead belongs to.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Prospect's primary contact/individual name.",
    )
    company_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="The prospect's own business/trading name, if applicable.",
    )
    email = models.EmailField(
        blank=True,
        default="",
        help_text="Prospect's primary contact email address.",
    )
    mobile = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Prospect's primary contact mobile number.",
    )
    source = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Free-text lead source (e.g. referral, website, walk-in). No fixed vocabulary is documented.",
    )
    status = models.CharField(
        max_length=30,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW,
        db_index=True,
        help_text="Lead lifecycle status.",
    )
    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
        help_text="The Sales/CRM user currently working this lead, if any.",
    )
    loss_reason = models.TextField(
        blank=True,
        default="",
        help_text="Required when status is LOST (enforced in LeadService.mark_lost, not a DB constraint).",
    )
    follow_up_reminder_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text="Optional future follow-up date/time, settable independent of status (FRS §8: 'optional future follow-up date').",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Free-form internal notes about this lead.",
    )
    converted_client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="converted_from_leads",
        help_text="The real Client created when this lead was converted (LeadService.convert_lead). Set once, never cleared.",
    )
    converted_project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="converted_from_leads",
        help_text="The Project optionally created at the same time as conversion, if requested.",
    )

    class Meta:
        db_table = "lead"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="lead_company_status_idx"),
            models.Index(fields=["company", "assigned_to"], name="lead_company_assignee_idx"),
        ]
        verbose_name = "lead"
        verbose_name_plural = "leads"

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name})"
