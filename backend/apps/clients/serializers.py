from rest_framework import serializers

from apps.clients.models import Client
from apps.clients.selectors import VALID_ORDER_FIELDS


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for Client model with camelCase JSON fields, matching
    apps.users.serializers.RoleSerializer / apps.company.serializers.CompanySerializer.

    Naming note: `companyName` here is the CLIENT's own business/trading
    name (Client.company_name, per Database_Schema.md's `client` table and
    FRS §7's "Name, Company, Email, Mobile, GSTIN" field list) — distinct
    from `companyId`, which is the tenant Company this client belongs to.
    Unlike RoleSerializer, the tenant's own display name is not also
    exposed under a `companyName`-shaped key, to avoid colliding with this
    field.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    companyName = serializers.CharField(
        source="company_name", required=False, allow_blank=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "companyName",
            "email",
            "mobile",
            "gstin",
            "addresses",
            "notes",
            "companyId",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "companyId",
            "createdAt",
            "updatedAt",
        ]


class ClientCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new Client.
    """

    name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Client's primary contact/individual name.",
    )
    companyName = serializers.CharField(
        source="company_name",
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        help_text="The client's own business/trading name, if applicable.",
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Client's primary contact email address.",
    )
    mobile = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
        help_text="Client's primary contact mobile number.",
    )
    gstin = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        default="",
        help_text="Client's GST Identification Number (GSTIN), if applicable.",
    )
    addresses = serializers.JSONField(
        required=False,
        default=list,
        help_text="List of address records for this client (shape not standardized).",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Free-form internal notes about this client.",
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
            raise serializers.ValidationError("Client name cannot be blank or empty.")
        return cleaned

    def validate_addresses(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("addresses must be a list.")
        return value


class ClientUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing Client. All fields optional
    (partial update semantics — see apps/clients/views.py::update()).
    """

    name = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Client's primary contact/individual name.",
    )
    companyName = serializers.CharField(
        source="company_name",
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="The client's own business/trading name, if applicable.",
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Client's primary contact email address.",
    )
    mobile = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Client's primary contact mobile number.",
    )
    gstin = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        help_text="Client's GST Identification Number (GSTIN), if applicable.",
    )
    addresses = serializers.JSONField(
        required=False,
        help_text="List of address records for this client (shape not standardized).",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Free-form internal notes about this client.",
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Client name cannot be blank or empty.")
        return cleaned

    def validate_addresses(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("addresses must be a list.")
        return value


class ClientListQuerySerializer(serializers.Serializer):
    """
    Validates ?search=/?ordering= query params for GET /clients. No status/
    isActive filter — Client has no such field (unlike Role/Company).
    """

    search = serializers.CharField(required=False, allow_blank=True, default="")
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_ORDER_FIELDS), required=False, default="-created_at"
    )
