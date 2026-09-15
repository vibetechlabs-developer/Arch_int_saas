import uuid
from typing import Optional

from django.db.models import Q, QuerySet

from apps.leads.models import Lead
from apps.leads.repositories import LeadRepository

VALID_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "name",
    "-name",
    "updated_at",
    "-updated_at",
    "status",
    "-status",
}


def list_leads(
    company_id: Optional[str | uuid.UUID] = None,
    status: Optional[str] = None,
    assigned_to_id: Optional[str | uuid.UUID] = None,
    search: Optional[str] = None,
    ordering: str = "-created_at",
) -> QuerySet[Lead]:
    """
    Read-only, filtered/ordered Lead listing for LeadService.list_leads.
    Mirrors apps.clients.selectors.list_clients. `status`/`assignedTo`
    filters are directly implied by 04_API/CRM_API.md's own documented
    `GET /leads` sketch ("filter: status, assigned to").
    """
    queryset = LeadRepository.all()

    if company_id:
        queryset = queryset.filter(company_id=company_id)

    if status:
        queryset = queryset.filter(status=status)

    if assigned_to_id:
        queryset = queryset.filter(assigned_to_id=assigned_to_id)

    if search:
        search_query = search.strip()
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(company_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(mobile__icontains=search_query)
        )

    order_field = ordering if ordering in VALID_ORDER_FIELDS else "-created_at"
    # "id" tie-breaker — mirrors apps.clients.selectors/apps.projects
    # selectors' identical fix (BE-030/BE-028): without it, rows tied on
    # order_field (most commonly created_at) have no defined relative
    # order across calls.
    return queryset.order_by(order_field, "id")
