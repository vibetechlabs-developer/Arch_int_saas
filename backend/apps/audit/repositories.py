import uuid
from typing import Any, Optional

from django.db.models import QuerySet

from apps.audit.models import AuditLog


class AuditLogRepository:
    """
    Data-access layer for AuditLog. Append-only by design: create() and
    read helpers only — no update()/delete(). An audit trail that could be
    altered or removed through the application layer would defeat its own
    purpose (Logging_Standards.md §5: "durable, queryable, never-expired").
    """

    @staticmethod
    def create(**fields: Any) -> AuditLog:
        return AuditLog.objects.create(**fields)

    @staticmethod
    def for_entity(entity_type: str, entity_id: str | uuid.UUID) -> QuerySet[AuditLog]:
        return AuditLog.objects.filter(entity_type=entity_type, entity_id=entity_id)

    @staticmethod
    def for_company(company_id: str | uuid.UUID) -> QuerySet[AuditLog]:
        return AuditLog.objects.filter(company_id=company_id)

    @staticmethod
    def for_actor(actor_user_id: str | uuid.UUID) -> QuerySet[AuditLog]:
        return AuditLog.objects.filter(actor_user_id=actor_user_id)
