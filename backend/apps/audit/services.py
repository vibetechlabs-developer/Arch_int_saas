import datetime
import logging
import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet

from apps.audit import selectors, validators
from apps.audit.models import AuditAction, AuditLog
from apps.audit.repositories import AuditLogRepository

logger = logging.getLogger("apps.audit")


class AuditLogService:
    """
    Single entry point for recording a durable audit_log row for a sensitive
    mutation, plus the companion operational log line
    (Logging_Standards.md §5: a sensitive mutation emits BOTH). Callers pass
    one call instead of duplicating both concerns themselves — this replaces
    the ad-hoc audit_logger.info()-only calls that RoleService used before
    BE-019.
    """

    @staticmethod
    def _client_ip(request: Any) -> Optional[str]:
        if request is None:
            return None
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @classmethod
    def record(
        cls,
        action: AuditAction,
        entity_type: str,
        entity_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        request: Any = None,
    ) -> AuditLog:
        """
        Persist an AuditLog row and emit the matching info-level log line.

        before_state/after_state are filtered through the per-entity-type
        allowlist (apps/audit/validators.py) before being persisted, never
        stored as given verbatim.

        request_id/ip_address/user_agent are extracted from the optional
        DRF/Django `request` when available — never required, since some
        callers (e.g. a future management command or Celery task) won't
        have one.
        """
        filtered_before = validators.filter_state_fields(entity_type, before_state)
        filtered_after = validators.filter_state_fields(entity_type, after_state)

        actor_user_id = getattr(actor_user, "id", None)
        request_id = getattr(request, "request_id", None) if request is not None else None
        user_agent = request.META.get("HTTP_USER_AGENT") if request is not None else None
        ip_address = cls._client_ip(request)

        entry = AuditLogRepository.create(
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_state=filtered_before,
            after_state=filtered_after,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(
            "%s %s",
            action,
            entity_type,
            extra={
                "action": action,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "company_id": str(company_id) if company_id else None,
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
                "request_id": request_id,
                "old_value": filtered_before,
                "new_value": filtered_after,
            },
        )

        return entry


class ActivityLogService:
    """
    Read-only "Activity Feed"/"Activity Logs" surface (BE-047), built
    directly on the existing audit_log table (BE-019) -- no new model.
    Deliberately separate from AuditLogService: that class is a write-
    only concern (every prior sprint's services call `.record()` and
    never read this table back), this one is the read/query concern,
    mirroring how apps.boq split BOQService (write orchestration) from
    BOQSummaryService (read computation).
    """

    @classmethod
    def list_activity_for_company(
        cls,
        company_id: str | uuid.UUID,
        entity_type: Optional[str] = None,
        entity_id: Optional[str | uuid.UUID] = None,
        action: Optional[str] = None,
        actor_user_id: Optional[str | uuid.UUID] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[AuditLog]:
        return selectors.list_activity_for_company(
            company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_user_id=actor_user_id,
            date_from=date_from,
            date_to=date_to,
            ordering=ordering,
        )
