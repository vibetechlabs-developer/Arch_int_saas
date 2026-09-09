import uuid

from django.db.models import QuerySet

from apps.invoices.models import Invoice
from apps.invoices.repositories import with_paid_amount

VALID_INVOICE_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "due_date",
    "-due_date",
    "updated_at",
    "-updated_at",
}


def list_invoices_for_project(
    project_id: str | uuid.UUID,
    ordering: str = "-created_at",
) -> QuerySet[Invoice]:
    """
    Read-only Invoice listing scoped to one already-authorized Project
    (BE-042). Mirrors
    apps.quotations.selectors.list_quotations_for_project.
    """
    queryset = with_paid_amount(
        Invoice.objects.select_related("company", "project", "quotation", "client").filter(
            project_id=project_id
        )
    )
    order_field = ordering if ordering in VALID_INVOICE_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field, "id")
