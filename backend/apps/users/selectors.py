import uuid
from typing import Optional

from django.db.models import Q, QuerySet

from apps.users.models import CompanyMembership, Role
from apps.users.repositories import CompanyMembershipRepository, RoleRepository

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

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    if search:
        search_query = search.strip()
        queryset = queryset.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    order_field = ordering if ordering in VALID_ORDER_FIELDS else "-created_at"
    # "id" tie-breaker (BE-030, mirrors the identical fix apps.projects
    # made in BE-028): without it, two rows whose order_field value ties
    # (most commonly created_at, which can collide under coarse OS clock
    # resolution) have no defined relative order and can come back
    # differently across calls.
    return queryset.order_by(order_field, "id")


MEMBERSHIP_ORDER_FIELDS = {"created_at", "-created_at", "status", "-status"}


def list_memberships_for_company(
    company_id: str | uuid.UUID,
    status: Optional[str] = None,
    search: Optional[str] = None,
    ordering: str = "-created_at",
) -> QuerySet[CompanyMembership]:
    """
    Read-only, filtered/ordered CompanyMembership listing scoped to one
    company (BE-052). Always company-scoped — there is no "list across
    companies" mode for this endpoint, matching Role's list_roles pattern.
    """
    queryset = CompanyMembershipRepository.all().filter(company_id=company_id)

    if status:
        queryset = queryset.filter(status=status)

    if search:
        search_query = search.strip()
        queryset = queryset.filter(
            Q(user__email__icontains=search_query) | Q(user__name__icontains=search_query)
        )

    order_field = ordering if ordering in MEMBERSHIP_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field, "id")


def list_memberships_for_user(user_id: str | uuid.UUID) -> QuerySet[CompanyMembership]:
    """
    A user's own active memberships across every company they belong to —
    the one legitimate cross-tenant read in this codebase, since it is
    scoped by user identity (not by a caller-supplied company id) and
    returns only company id/name/status + role name (BE-053).
    """
    return (
        CompanyMembershipRepository.all()
        .filter(user_id=user_id, status="active")
        .order_by("-created_at", "id")
    )
