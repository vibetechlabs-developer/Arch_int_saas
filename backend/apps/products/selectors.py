import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.products.models import ProductCategory
from apps.products.repositories import ProductCategoryRepository

VALID_CATEGORY_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "name",
    "-name",
    "updated_at",
    "-updated_at",
}


def list_categories(
    company_id: Optional[str | uuid.UUID] = None,
    ordering: str = "-created_at",
) -> QuerySet[ProductCategory]:
    """
    Read-only, tenant-scoped ProductCategory listing for
    ProductCategoryService.list_categories (BE-031). No `search` param --
    Category has only one field (`name`), so a dedicated search would just
    duplicate an exact/icontains filter; not documented anywhere either.
    "id" is an unconditional secondary sort key (BE-030 finding applied
    from day one here, not retrofitted after a flake).
    """
    queryset = ProductCategoryRepository.all()

    if company_id:
        queryset = queryset.filter(company_id=company_id)

    order_field = ordering if ordering in VALID_CATEGORY_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field, "id")
