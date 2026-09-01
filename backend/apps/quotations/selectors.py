import uuid

from django.db.models import QuerySet

from apps.quotations.models import Quotation

VALID_QUOTATION_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "version",
    "-version",
    "updated_at",
    "-updated_at",
}


def list_quotations_for_project(
    project_id: str | uuid.UUID,
    ordering: str = "-created_at",
) -> QuerySet[Quotation]:
    """
    Read-only Quotation listing scoped to one already-authorized Project
    (BE-039) — "all versions", per Finance_API.md ("List quotations (all
    versions)"), so no status/version filter is applied here. Mirrors the
    ProjectMemberService pattern: tenant authorization for the parent
    happens at the view layer before this is ever called.
    """
    queryset = Quotation.objects.select_related("company", "project", "boq", "client").filter(
        project_id=project_id
    )
    order_field = ordering if ordering in VALID_QUOTATION_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field, "id")
