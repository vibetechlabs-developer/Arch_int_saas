from typing import Optional

from django.db.models import Q, QuerySet

from apps.company.models import Company
from apps.company.repositories import CompanyRepository

VALID_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "name",
    "-name",
    "status",
    "-status",
    "updated_at",
    "-updated_at",
}


def list_companies(
    status: Optional[str] = None,
    search: Optional[str] = None,
    ordering: str = "-created_at",
) -> QuerySet[Company]:
    """
    Read-only, filtered/ordered Company listing for CompanyService.list_companies.
    """
    queryset = CompanyRepository.all()

    if status:
        queryset = queryset.filter(status=status)

    if search:
        search_query = search.strip()
        queryset = queryset.filter(
            Q(name__icontains=search_query) | Q(gst_number__icontains=search_query)
        )

    order_field = ordering if ordering in VALID_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field)
