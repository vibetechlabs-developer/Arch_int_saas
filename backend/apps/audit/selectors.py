import datetime
import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.audit.models import AuditLog

VALID_AUDIT_LOG_ORDER_FIELDS = {
    "created_at",
    "-created_at",
}


def list_activity_for_company(
    company_id: str | uuid.UUID,
    entity_type: Optional[str] = None,
    entity_id: Optional[str | uuid.UUID] = None,
    action: Optional[str] = None,
    actor_user_id: Optional[str | uuid.UUID] = None,
    date_from: Optional[datetime.date] = None,
    date_to: Optional[datetime.date] = None,
    ordering: str = "-created_at",
) -> QuerySet[AuditLog]:
    """
    Read-only, filtered/ordered AuditLog listing scoped to one tenant
    (BE-047) -- the "Activity Feed"/"Activity Logs" surface CLAUDE.md's
    Dashboard section and Sprint 7's stub both name, built directly on
    top of the existing audit_log table (BE-019) rather than a new model.
    """
    queryset = AuditLog.objects.select_related("company", "actor_user").filter(company_id=company_id)

    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)
    if entity_id:
        queryset = queryset.filter(entity_id=entity_id)
    if action:
        queryset = queryset.filter(action=action)
    if actor_user_id:
        queryset = queryset.filter(actor_user_id=actor_user_id)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    order_field = ordering if ordering in VALID_AUDIT_LOG_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field, "id")
