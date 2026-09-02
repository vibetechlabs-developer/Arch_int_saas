from rest_framework import serializers

from apps.audit.models import AuditAction, AuditLog
from apps.audit.selectors import VALID_AUDIT_LOG_ORDER_FIELDS


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Output serializer for AuditLog, with camelCase JSON fields matching
    every other serializer in this codebase. Read-only in every sense --
    AuditLog itself is append-only (see its own model docstring).
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True, allow_null=True)
    actorUserId = serializers.UUIDField(source="actor_user_id", read_only=True, allow_null=True)
    actorUserName = serializers.CharField(
        source="actor_user.name", read_only=True, allow_null=True, default=None
    )
    entityType = serializers.CharField(source="entity_type", read_only=True)
    entityId = serializers.UUIDField(source="entity_id", read_only=True)
    beforeState = serializers.JSONField(source="before_state", read_only=True)
    afterState = serializers.JSONField(source="after_state", read_only=True)
    requestId = serializers.CharField(source="request_id", read_only=True, allow_null=True)
    ipAddress = serializers.IPAddressField(source="ip_address", read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "companyId",
            "actorUserId",
            "actorUserName",
            "entityType",
            "entityId",
            "action",
            "beforeState",
            "afterState",
            "requestId",
            "ipAddress",
            "createdAt",
        ]
        read_only_fields = fields


class ActivityLogListQuerySerializer(serializers.Serializer):
    """
    Validates GET /activity-logs query params (BE-047): entityType/
    entityId/action/actorUserId/dateFrom/dateTo filters, plus ordering.
    """

    entityType = serializers.CharField(
        source="entity_type", required=False, allow_blank=True, default=None, allow_null=True
    )
    entityId = serializers.UUIDField(source="entity_id", required=False, default=None, allow_null=True)
    action = serializers.ChoiceField(
        choices=AuditAction.choices, required=False, default=None, allow_null=True
    )
    actorUserId = serializers.UUIDField(
        source="actor_user_id", required=False, default=None, allow_null=True
    )
    dateFrom = serializers.DateField(source="date_from", required=False, default=None, allow_null=True)
    dateTo = serializers.DateField(source="date_to", required=False, default=None, allow_null=True)
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_AUDIT_LOG_ORDER_FIELDS), required=False, default="-created_at"
    )
