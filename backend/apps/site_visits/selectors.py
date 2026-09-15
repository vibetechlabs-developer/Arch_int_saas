import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.site_visits.models import SiteVisit
from apps.site_visits.repositories import SiteVisitRepository

VALID_ORDER_FIELDS = {
    "visit_date",
    "-visit_date",
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
}


def list_site_visits(
    company_id: Optional[str | uuid.UUID] = None,
    lead_id: Optional[str | uuid.UUID] = None,
    project_id: Optional[str | uuid.UUID] = None,
    assigned_to_id: Optional[str | uuid.UUID] = None,
    ordering: str = "-visit_date",
) -> QuerySet[SiteVisit]:
    """
    Read-only, filtered/ordered SiteVisit listing for SiteVisitService.list_site_visits.
    Mirrors apps.leads.selectors.list_leads. `lead`/`project`/`assignedTo`
    filters are directly implied by CRM_API.md's own documented
    `GET /site-visits` sketch and FRS §9's field list.
    """
    queryset = SiteVisitRepository.all()

    if company_id:
        queryset = queryset.filter(company_id=company_id)

    if lead_id:
        queryset = queryset.filter(lead_id=lead_id)

    if project_id:
        queryset = queryset.filter(project_id=project_id)

    if assigned_to_id:
        queryset = queryset.filter(assigned_to_id=assigned_to_id)

    order_field = ordering if ordering in VALID_ORDER_FIELDS else "-visit_date"
    # "id" tie-breaker — mirrors apps.leads/apps.clients/apps.projects
    # selectors' identical fix: without it, rows tied on order_field have
    # no defined relative order across calls.
    return queryset.order_by(order_field, "id")
