from rest_framework import serializers

from apps.clients.models import Client


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
