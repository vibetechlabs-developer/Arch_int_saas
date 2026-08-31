from rest_framework import serializers

from apps.projects.models import Project, ProjectMember, ProjectStatus
from apps.projects.selectors import VALID_ORDER_FIELDS


class ProjectListQuerySerializer(serializers.Serializer):
    """
    Validates GET /projects query params (BE-028). Covers exactly
    Project_API.md's documented filter set (status, client, assigned
    user, priority, date range) plus ordering, matching the
    ClientListQuerySerializer convention. No free-text `search` param —
    Project_API.md doesn't document one for this endpoint, unlike Client.
    """

    status = serializers.ChoiceField(choices=ProjectStatus.choices, required=False, default=None, allow_null=True)
    client = serializers.UUIDField(source="client_id", required=False, default=None, allow_null=True)
    assignedTo = serializers.UUIDField(
        source="assigned_to_id", required=False, default=None, allow_null=True
    )
    priority = serializers.CharField(required=False, allow_blank=True, default=None, allow_null=True)
    startDateFrom = serializers.DateField(
        source="start_date_from", required=False, default=None, allow_null=True
    )
    startDateTo = serializers.DateField(
        source="start_date_to", required=False, default=None, allow_null=True
    )
    deadlineFrom = serializers.DateField(
        source="deadline_from", required=False, default=None, allow_null=True
    )
    deadlineTo = serializers.DateField(
        source="deadline_to", required=False, default=None, allow_null=True
    )
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_ORDER_FIELDS), required=False, default="-created_at"
    )


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


class ProjectStatusTransitionSerializer(serializers.Serializer):
    """
    Input serializer for `PATCH /projects/{projectId}/status` (BE-027).
    Only validates that `status` is one of the 11 documented
    ProjectStatus values — whether that specific transition is reachable
    from the project's *current* status is ProjectService.transition_status's
    job (a 409 state conflict, not a 400 validation error).
    """

    status = serializers.ChoiceField(choices=ProjectStatus.choices, required=True)


class ProjectMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectMember (BE-026), camelCase, matching
    ProjectSerializer's `assignedToName`-style read-only display
    convenience pattern for `userName`/`assignedByName`.
    """

    projectId = serializers.UUIDField(source="project_id", read_only=True)
    userId = serializers.UUIDField(source="user_id", read_only=True, allow_null=True)
    userName = serializers.CharField(
        source="user.name", read_only=True, allow_null=True, default=None
    )
    userEmail = serializers.CharField(
        source="user.email", read_only=True, allow_null=True, default=None
    )
    assignedById = serializers.UUIDField(source="assigned_by_id", read_only=True, allow_null=True)
    assignedByName = serializers.CharField(
        source="assigned_by.name", read_only=True, allow_null=True, default=None
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            "id",
            "projectId",
            "userId",
            "userName",
            "userEmail",
            "assignedById",
            "assignedByName",
            "createdAt",
        ]
        read_only_fields = fields


class ProjectMemberCreateSerializer(serializers.Serializer):
    """
    Input serializer for adding a user to a project's team
    (`POST /projects/{projectId}/team`, BE-026).
    """

    userId = serializers.UUIDField(source="user_id", required=True)


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
