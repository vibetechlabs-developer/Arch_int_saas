import uuid
from typing import Optional

from django.db.models import Q, QuerySet

from apps.clients.models import Client
from apps.clients.repositories import ClientRepository

VALID_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "name",
    "-name",
    "updated_at",
    "-updated_at",
}


def list_clients(
    company_id: Optional[str | uuid.UUID] = None,
    search: Optional[str] = None,
    ordering: str = "-created_at",
) -> QuerySet[Client]:
    """
    Read-only, filtered/ordered Client listing for ClientService.list_clients.
    Mirrors apps.users.selectors.list_roles. Search covers only the
    documented text fields (name, company_name, email, mobile) — no
    gstin/notes/addresses search (undocumented, and addresses is JSON).
    """
    queryset = ClientRepository.all()

    if company_id:
        queryset = queryset.filter(company_id=company_id)

    if search:
        search_query = search.strip()
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(company_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(mobile__icontains=search_query)
        )

    order_field = ordering if ordering in VALID_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field)
