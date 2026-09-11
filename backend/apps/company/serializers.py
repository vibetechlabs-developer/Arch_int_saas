from rest_framework import serializers

from apps.company.models import Company, CompanyStatus
from apps.company.selectors import VALID_ORDER_FIELDS


class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer for Company model with camelCase JSON fields.
    """

    gstNumber = serializers.CharField(
        source="gst_number",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    logoUrl = serializers.URLField(
        source="logo_url",
        required=False,
        allow_blank=True,
    )
    createdAt = serializers.DateTimeField(
        source="created_at",
        read_only=True,
    )
    updatedAt = serializers.DateTimeField(
        source="updated_at",
        read_only=True,
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "status",
            "currency",
            "gstNumber",
            "logoUrl",
            "settings",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "createdAt",
            "updatedAt",
        ]


class CompanyCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new Company tenant.
    """

    name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Company trading or legal name.",
    )
    currency = serializers.CharField(
        max_length=10,
        required=False,
        default="INR",
        help_text="Default currency code (e.g. INR, USD).",
    )
    gstNumber = serializers.CharField(
        source="gst_number",
        max_length=15,
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
        help_text="Goods and Services Tax Identification Number.",
    )
    status = serializers.ChoiceField(
        choices=Company.status.field.choices,
        required=False,
        default="trial",
        help_text="Tenant lifecycle status.",
    )
    settings = serializers.JSONField(
        required=False,
        help_text="Tenant configuration and preferences dictionary.",
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Company name cannot be blank or empty.")
        return cleaned


class CompanyLogoUploadSerializer(serializers.Serializer):
    """
    Output shape for `POST /company/{id}/logo/upload` (BE-078). Mirrors
    `apps.products.serializers.ProductImageUploadSerializer` exactly -- a
    plain Serializer over `CompanyService.upload_logo`'s returned dict (no
    model behind this endpoint).
    """

    url = serializers.URLField()
    key = serializers.CharField(
        help_text="Internal storage key -- pass back as logoStorageKey when saving the Company so a later replace/remove can clean up this file."
    )
    fileName = serializers.CharField()
    contentType = serializers.CharField()
    size = serializers.IntegerField()


class CompanyListQuerySerializer(serializers.Serializer):
    """
    Validates ?status=/?search=/?ordering= query params for GET /companies —
    replaces the manual query-param reads that previously lived directly in
    CompanyViewSet.list(). An invalid value for any of these now returns
    400 VALIDATION_ERROR instead of being silently ignored/coerced.
    """

    status = serializers.ChoiceField(
        choices=CompanyStatus.choices, required=False, allow_null=True, default=None
    )
    search = serializers.CharField(required=False, allow_blank=True, default="")
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_ORDER_FIELDS), required=False, default="-created_at"
    )


class CompanyUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing Company tenant.
    """

    name = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Company trading or legal name.",
    )
    currency = serializers.CharField(
        max_length=10,
        required=False,
        help_text="Default currency code (e.g. INR, USD).",
    )
    gstNumber = serializers.CharField(
        source="gst_number",
        max_length=15,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Goods and Services Tax Identification Number.",
    )
    logoUrl = serializers.URLField(
        source="logo_url",
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Absolute URL returned by POST /company/{id}/logo/upload. Set to an empty string to remove the logo.",
    )
    logoStorageKey = serializers.CharField(
        source="logo_storage_key",
        required=False,
        allow_blank=True,
        max_length=500,
        write_only=True,
        help_text="Internal-only. Pass through the `key` returned by the logo upload endpoint alongside logoUrl.",
    )
    status = serializers.ChoiceField(
        choices=Company.status.field.choices,
        required=False,
        help_text="Tenant lifecycle status.",
    )
    settings = serializers.JSONField(
        required=False,
        help_text="Tenant configuration and preferences dictionary.",
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Company name cannot be blank or empty.")
        return cleaned

