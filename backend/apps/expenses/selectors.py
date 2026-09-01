import datetime
import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.expenses.models import Expense

VALID_EXPENSE_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "date",
    "-date",
    "amount",
    "-amount",
    "updated_at",
    "-updated_at",
}


def list_expenses_for_project(
    project_id: str | uuid.UUID,
    category: Optional[str] = None,
    vendor: Optional[str] = None,
    employee_id: Optional[str | uuid.UUID] = None,
    approval_status: Optional[str] = None,
    date_from: Optional[datetime.date] = None,
    date_to: Optional[datetime.date] = None,
    ordering: str = "-date",
) -> QuerySet[Expense]:
    """
    Read-only, filtered/ordered Expense listing scoped to one already-
    authorized Project (BE-044). Filters match Finance_API.md's
    documented set exactly ("filter: category, vendor, employee, date"),
    plus `approval_status` (documented as the entity's own status field,
    the same "add the obvious status filter" treatment
    apps.products.selectors.list_products gave Product.status).
    """
    queryset = Expense.objects.select_related("company", "project", "employee", "added_by").filter(
        project_id=project_id
    )

    if category:
        queryset = queryset.filter(category=category)
    if vendor:
        queryset = queryset.filter(vendor=vendor)
    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)
    if approval_status:
        queryset = queryset.filter(approval_status=approval_status)
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date__lte=date_to)

    order_field = ordering if ordering in VALID_EXPENSE_ORDER_FIELDS else "-date"
    return queryset.order_by(order_field, "id")
