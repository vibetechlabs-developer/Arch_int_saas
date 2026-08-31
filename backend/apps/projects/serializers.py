from rest_framework import serializers

from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for Project model with camelCase JSON fields, matching
    apps.clients.serializers.ClientSerializer / apps.users.serializers.RoleSerializer.
    `clientName`/`assignedToName` are read-only display conveniences
    (mirrors RoleSerializer's `companyName`), not separate business data.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    clientId = serializers.UUIDField(source="client_id", read_only=True)
    clientName = serializers.CharField(source="client.name", read_only=True)
    startDate = serializers.DateField(source="start_date", required=False, allow_null=True)
    assignedToId = serializers.UUIDField(source="assigned_to_id", read_only=True)
    assignedToName = serializers.CharField(
        source="assigned_to.name", read_only=True, allow_null=True, default=None
    )
    followUpReminderAt = serializers.DateTimeField(
        source="follow_up_reminder_at", required=False, allow_null=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "companyId",
            "clientId",
            "clientName",
            "startDate",
            "deadline",
            "status",
            "priority",
            "assignedToId",
            "assignedToName",
            "followUpReminderAt",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "companyId",
            "clientId",
            "clientName",
            "status",
            "assignedToId",
            "assignedToName",
            "createdAt",
            "updatedAt",
        ]


class ProjectCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new Project. `status` is deliberately
    absent — Project_API.md documents a separate dedicated
    `PATCH .../status` endpoint for transitions (BE-027); every new
    project starts at the model default (draft).
    """

    name = serializers.CharField(max_length=255, required=True)
    clientId = serializers.UUIDField(source="client_id", required=True)
    startDate = serializers.DateField(source="start_date", required=False, allow_null=True, default=None)
    deadline = serializers.DateField(required=False, allow_null=True, default=None)
    priority = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    assignedTo = serializers.UUIDField(
        source="assigned_to_id", required=False, allow_null=True, default=None
    )
    followUpReminderAt = serializers.DateTimeField(
        source="follow_up_reminder_at", required=False, allow_null=True, default=None
    )
    companyId = serializers.UUIDField(
        source="company_id",
        required=False,
        allow_null=True,
        default=None,
        help_text="Company UUID for platform admins. Ignored/overridden for company users.",
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Project name cannot be blank or empty.")
        return cleaned


class ProjectUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing Project. `client` and
    `status` are deliberately not editable here — Project_API.md's PATCH
    endpoint lists only name/dates/priority/assigned user as editable;
    status changes go through the separate dedicated `/status` endpoint
    (BE-027), and client reassignment is not documented as supported.
    """

    name = serializers.CharField(max_length=255, required=False)
    startDate = serializers.DateField(source="start_date", required=False, allow_null=True)
    deadline = serializers.DateField(required=False, allow_null=True)
    priority = serializers.CharField(max_length=50, required=False, allow_blank=True)
    assignedTo = serializers.UUIDField(source="assigned_to_id", required=False, allow_null=True)
    followUpReminderAt = serializers.DateTimeField(
        source="follow_up_reminder_at", required=False, allow_null=True
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Project name cannot be blank or empty.")
        return cleaned
