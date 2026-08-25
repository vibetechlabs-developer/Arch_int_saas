from rest_framework import serializers

from apps.company.models import Company


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

