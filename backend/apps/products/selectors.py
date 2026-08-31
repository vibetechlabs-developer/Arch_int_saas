import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.products.models import ProductCategory, ProductSubcategory
from apps.products.repositories import ProductCategoryRepository, ProductSubcategoryRepository

VALID_CATEGORY_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "name",
    "-name",
    "updated_at",
    "-updated_at",
}

VALID_SUBCATEGORY_ORDER_FIELDS = VALID_CATEGORY_ORDER_FIELDS


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


def list_subcategories_for_category(
    category_id: str | uuid.UUID,
    ordering: str = "-created_at",
) -> QuerySet[ProductSubcategory]:
    """
    Read-only ProductSubcategory listing scoped to one already-authorized
    Category (BE-032) — mirrors the ProjectMemberService pattern: tenant
    authorization for the parent happens at the view layer before this is
    ever called, so no company_id param is needed here.
    """
    queryset = ProductSubcategoryRepository.all().filter(category_id=category_id)
    order_field = ordering if ordering in VALID_SUBCATEGORY_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field, "id")


def has_active_subcategories_for_category(category_id: str | uuid.UUID) -> bool:
    """
    True if the given category (by ID) has at least one non-deleted
    Subcategory. Backs ProductCategoryService.soft_delete_category's
    delete guard (resolves BE-031's documented deferral) — implemented as
    a direct query here rather than a separate selector class the way
    apps.projects.selectors.ProjectSelector was, since Category and
    Subcategory live in the SAME app (apps.products); the cross-app
    domain-ownership concern that motivated ProjectSelector's indirection
    (Client and Project are separate apps) doesn't apply here.
    """
    return ProductSubcategory.objects.filter(category_id=category_id).exists()
