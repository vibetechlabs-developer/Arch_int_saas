import uuid
from typing import Iterable, Optional

from django.db.models import Q, QuerySet

from apps.users.models import Role
from apps.users.repositories import RoleRepository

VALID_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "name",
    "-name",
    "updated_at",
    "-updated_at",
    "is_active",
    "-is_active",
}


def list_roles(
    company_id: Optional[str | uuid.UUID] = None,
    company_ids: Optional[Iterable[str | uuid.UUID]] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    ordering: str = "-created_at",
) -> QuerySet[Role]:
    """
    Read-only, filtered/ordered Role listing for RoleService.list_roles.
    """
    queryset = RoleRepository.all()

    if company_id:
        queryset = queryset.filter(company_id=company_id)
    elif company_ids is not None:
        queryset = queryset.filter(company_id__in=company_ids)

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    if search:
        search_query = search.strip()
        queryset = queryset.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    order_field = ordering if ordering in VALID_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field)
