from rest_framework import serializers

from apps.site_visits.models import SiteVisit
from apps.site_visits.selectors import VALID_ORDER_FIELDS


class SiteVisitSerializer(serializers.ModelSerializer):
    """
    Serializer for SiteVisit model with camelCase JSON fields, matching
    apps.leads.serializers.LeadSerializer's structure. `leadName`/
    `projectName`/`clientName`/`assignedToName` are read-only display
    conveniences.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    leadId = serializers.UUIDField(source="lead_id", read_only=True, allow_null=True)
    leadName = serializers.CharField(source="lead.name", read_only=True, allow_null=True, default=None)
    projectId = serializers.UUIDField(source="project_id", read_only=True, allow_null=True)
    projectName = serializers.CharField(source="project.name", read_only=True, allow_null=True, default=None)
    clientId = serializers.UUIDField(source="client_id", read_only=True, allow_null=True)
    clientName = serializers.CharField(source="client.name", read_only=True, allow_null=True, default=None)
    visitDate = serializers.DateTimeField(source="visit_date")
    assignedToId = serializers.UUIDField(source="assigned_to_id", read_only=True, allow_null=True)
    assignedToName = serializers.CharField(
        source="assigned_to.name", read_only=True, allow_null=True, default=None
    )
    photoUrls = serializers.JSONField(source="photo_urls")
    videoUrls = serializers.JSONField(source="video_urls")
    siteConditions = serializers.CharField(source="site_conditions", required=False, allow_blank=True)
    followUpActions = serializers.CharField(source="follow_up_actions", required=False, allow_blank=True)
    reportSubmittedAt = serializers.DateTimeField(source="report_submitted_at", read_only=True, allow_null=True)
    isCompleted = serializers.BooleanField(source="is_completed", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = SiteVisit
        fields = [
            "id",
            "leadId",
            "leadName",
            "projectId",
            "projectName",
            "clientId",
            "clientName",
            "visitDate",
            "assignedToId",
            "assignedToName",
            "address",
            "measurements",
            "requirements",
            "photoUrls",
            "videoUrls",
            "notes",
            "budget",
            "siteConditions",
            "followUpActions",
            "reportSubmittedAt",
            "isCompleted",
            "companyId",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "companyId",
            "leadId",
            "leadName",
            "projectId",
            "projectName",
            "clientId",
            "clientName",
            "assignedToId",
            "assignedToName",
            "reportSubmittedAt",
            "isCompleted",
            "createdAt",
            "updatedAt",
        ]


class SiteVisitCreateSerializer(serializers.Serializer):
    """Input serializer for creating a new SiteVisit. Requires at least one of leadId/projectId (FRS §9 / ER_Diagram.md §2)."""

    leadId = serializers.UUIDField(source="lead_id", required=False, allow_null=True, default=None)
    projectId = serializers.UUIDField(source="project_id", required=False, allow_null=True, default=None)
    visitDate = serializers.DateTimeField(source="visit_date", required=True)
    assignedToId = serializers.UUIDField(source="assigned_to_id", required=False, allow_null=True, default=None)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    measurements = serializers.CharField(required=False, allow_blank=True, default="")
    requirements = serializers.CharField(required=False, allow_blank=True, default="")
    photoUrls = serializers.JSONField(source="photo_urls", required=False, default=list)
    videoUrls = serializers.JSONField(source="video_urls", required=False, default=list)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    budget = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, default=None)
    siteConditions = serializers.CharField(source="site_conditions", required=False, allow_blank=True, default="")
    followUpActions = serializers.CharField(source="follow_up_actions", required=False, allow_blank=True, default="")
    companyId = serializers.UUIDField(
        source="company_id", required=False, allow_null=True, default=None,
        help_text="Company UUID for platform admins. Ignored/overridden for company users.",
    )

    def validate_photoUrls(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("photoUrls must be a list.")
        return value

    def validate_videoUrls(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("videoUrls must be a list.")
        return value

    def validate(self, attrs):
        if not attrs.get("lead_id") and not attrs.get("project_id"):
            raise serializers.ValidationError(
                {"leadId": ["A site visit must be linked to a lead or a project (or both)."]}
            )
        return attrs


class SiteVisitUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing SiteVisit's captured-on-site
    fields. No `leadId`/`projectId`/`companyId` — those are only set at
    creation (mirrors ProjectUpdateSerializer's exclusion of `clientId`).
    """

    visitDate = serializers.DateTimeField(source="visit_date", required=False)
    assignedToId = serializers.UUIDField(source="assigned_to_id", required=False, allow_null=True)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    measurements = serializers.CharField(required=False, allow_blank=True)
    requirements = serializers.CharField(required=False, allow_blank=True)
    photoUrls = serializers.JSONField(source="photo_urls", required=False)
    videoUrls = serializers.JSONField(source="video_urls", required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    budget = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    siteConditions = serializers.CharField(source="site_conditions", required=False, allow_blank=True)
    followUpActions = serializers.CharField(source="follow_up_actions", required=False, allow_blank=True)

    def validate_photoUrls(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("photoUrls must be a list.")
        return value

    def validate_videoUrls(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("videoUrls must be a list.")
        return value


class SiteVisitListQuerySerializer(serializers.Serializer):
    """Validates ?lead=/?project=/?assignedTo=/?ordering= query params for GET /site-visits."""

    lead = serializers.UUIDField(source="lead_id", required=False, default=None, allow_null=True)
    project = serializers.UUIDField(source="project_id", required=False, default=None, allow_null=True)
    assignedTo = serializers.UUIDField(source="assigned_to_id", required=False, default=None, allow_null=True)
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_ORDER_FIELDS), required=False, default="-visit_date"
    )


class SiteVisitReportSerializer(serializers.Serializer):
    """Input serializer for `POST /site-visits/{siteVisitId}/report` (04_API/CRM_API.md: 'Submit site visit report (may trigger project creation)')."""

    createProject = serializers.BooleanField(source="create_project", required=False, default=False)
    projectName = serializers.CharField(
        source="project_name", required=False, allow_blank=True, default=None, allow_null=True,
        help_text="Only used when createProject is true. Defaults to '{Client name} Project'.",
    )
