from rest_framework import serializers

from apps.leads.models import Lead, LeadStatus
from apps.leads.selectors import VALID_ORDER_FIELDS


class LeadSerializer(serializers.ModelSerializer):
    """
    Serializer for Lead model with camelCase JSON fields, matching
    apps.clients.serializers.ClientSerializer's structure. `assignedToName`/
    `convertedClientName`/`convertedProjectName` are read-only display
    conveniences (mirrors ProjectSerializer's `clientName` pattern).
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    companyName = serializers.CharField(source="company_name", required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=LeadStatus.choices, read_only=True)
    assignedToId = serializers.UUIDField(source="assigned_to_id", read_only=True, allow_null=True)
    assignedToName = serializers.CharField(
        source="assigned_to.name", read_only=True, allow_null=True, default=None
    )
    lossReason = serializers.CharField(source="loss_reason", read_only=True)
    followUpReminderAt = serializers.DateTimeField(
        source="follow_up_reminder_at", required=False, allow_null=True
    )
    convertedClientId = serializers.UUIDField(
        source="converted_client_id", read_only=True, allow_null=True
    )
    convertedClientName = serializers.CharField(
        source="converted_client.name", read_only=True, allow_null=True, default=None
    )
    convertedProjectId = serializers.UUIDField(
        source="converted_project_id", read_only=True, allow_null=True
    )
    convertedProjectName = serializers.CharField(
        source="converted_project.name", read_only=True, allow_null=True, default=None
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "companyName",
            "email",
            "mobile",
            "source",
            "status",
            "assignedToId",
            "assignedToName",
            "lossReason",
            "followUpReminderAt",
            "notes",
            "convertedClientId",
            "convertedClientName",
            "convertedProjectId",
            "convertedProjectName",
            "companyId",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "companyId",
            "status",
            "assignedToId",
            "assignedToName",
            "lossReason",
            "convertedClientId",
            "convertedClientName",
            "convertedProjectId",
            "convertedProjectName",
            "createdAt",
            "updatedAt",
        ]


class LeadCreateSerializer(serializers.Serializer):
    """Input serializer for creating a new Lead. Always starts at LeadStatus.NEW — status is never settable at create."""

    name = serializers.CharField(max_length=255, required=True, help_text="Prospect's primary contact/individual name.")
    companyName = serializers.CharField(
        source="company_name", max_length=255, required=False, allow_blank=True, default="",
        help_text="The prospect's own business/trading name, if applicable.",
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    mobile = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    source = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default="",
        help_text="Free-text lead source (e.g. referral, website, walk-in).",
    )
    assignedToId = serializers.UUIDField(
        source="assigned_to_id", required=False, allow_null=True, default=None,
        help_text="The Sales/CRM user to assign this lead to, if any. Must be an active member of this company.",
    )
    followUpReminderAt = serializers.DateTimeField(
        source="follow_up_reminder_at", required=False, allow_null=True, default=None,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    companyId = serializers.UUIDField(
        source="company_id", required=False, allow_null=True, default=None,
        help_text="Company UUID for platform admins. Ignored/overridden for company users.",
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Lead name cannot be blank or empty.")
        return cleaned


class LeadUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing Lead's identity/assignment/
    notes fields. No `status` field — status has its own transition
    endpoints (mirrors ProjectUpdateSerializer's identical exclusion).
    `assignedToId` allows explicit `null` to clear the assignee.
    """

    name = serializers.CharField(max_length=255, required=False)
    companyName = serializers.CharField(source="company_name", max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=20, required=False, allow_blank=True)
    source = serializers.CharField(max_length=100, required=False, allow_blank=True)
    assignedToId = serializers.UUIDField(source="assigned_to_id", required=False, allow_null=True)
    followUpReminderAt = serializers.DateTimeField(
        source="follow_up_reminder_at", required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Lead name cannot be blank or empty.")
        return cleaned


class LeadListQuerySerializer(serializers.Serializer):
    """Validates ?status=/?assignedTo=/?search=/?ordering= query params for GET /leads (04_API/CRM_API.md: 'filter: status, assigned to')."""

    status = serializers.ChoiceField(choices=LeadStatus.choices, required=False, default=None, allow_null=True)
    assignedTo = serializers.UUIDField(
        source="assigned_to_id", required=False, default=None, allow_null=True
    )
    search = serializers.CharField(required=False, allow_blank=True, default="")
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_ORDER_FIELDS), required=False, default="-created_at"
    )


class LeadStatusTransitionSerializer(serializers.Serializer):
    """
    Input serializer for `PATCH /leads/{leadId}/status` (BE-061). Only
    validates that `status` is one of the 6 documented LeadStatus values
    — whether that specific transition is reachable from the lead's
    *current* status is LeadService.transition_status's job (a 409 state
    conflict, not a 400 validation error). Mirrors
    ProjectStatusTransitionSerializer exactly.
    """

    status = serializers.ChoiceField(choices=LeadStatus.choices, required=True)


class LeadMarkLostSerializer(serializers.Serializer):
    """Input serializer for `POST /leads/{leadId}/mark-lost` (04_API/CRM_API.md: 'requires loss reason, optional follow-up date')."""

    lossReason = serializers.CharField(source="loss_reason", required=True, allow_blank=False)
    followUpReminderAt = serializers.DateTimeField(
        source="follow_up_reminder_at", required=False, allow_null=True, default=None
    )

    def validate_lossReason(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("A loss reason is required to mark a lead as lost.")
        return cleaned


class LeadConvertSerializer(serializers.Serializer):
    """Input serializer for `POST /leads/{leadId}/convert` (04_API/CRM_API.md: 'Convert lead -> client (+ optionally create project)')."""

    createProject = serializers.BooleanField(source="create_project", required=False, default=False)
    projectName = serializers.CharField(
        source="project_name", required=False, allow_blank=True, default=None, allow_null=True,
        help_text="Only used when createProject is true. Defaults to the lead's own name.",
    )
