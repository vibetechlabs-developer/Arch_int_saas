from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Standard serializer for User model representation with camelCase fields.
    Excludes sensitive credentials and internal permission mappings.
    """

    isActive = serializers.BooleanField(source="is_active", read_only=True)
    isStaff = serializers.BooleanField(source="is_staff", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "status",
            "isActive",
            "isStaff",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "email",
            "status",
            "isActive",
            "isStaff",
            "createdAt",
            "updatedAt",
        ]


class CompanyMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for CompanyMembership model with camelCase JSON fields.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    companyName = serializers.CharField(source="company.name", read_only=True)
    companyStatus = serializers.CharField(source="company.status", read_only=True)
    userId = serializers.UUIDField(source="user_id", read_only=True)
    userEmail = serializers.EmailField(source="user.email", read_only=True)
    userName = serializers.CharField(source="user.name", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        from apps.users.models import CompanyMembership

        model = CompanyMembership
        fields = [
            "id",
            "companyId",
            "companyName",
            "companyStatus",
            "userId",
            "userEmail",
            "userName",
            "status",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "companyId",
            "companyName",
            "companyStatus",
            "userId",
            "userEmail",
            "userName",
            "createdAt",
            "updatedAt",
        ]


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for Role model with camelCase JSON fields.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    companyName = serializers.CharField(source="company.name", read_only=True)
    isActive = serializers.BooleanField(source="is_active", default=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        from apps.users.models import Role

        model = Role
        fields = [
            "id",
            "name",
            "description",
            "companyId",
            "companyName",
            "isActive",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "companyId",
            "companyName",
            "createdAt",
            "updatedAt",
        ]


class RoleCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new Role.
    """

    name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Human-readable role name, unique per company.",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional free-form description of the role's purpose.",
    )
    isActive = serializers.BooleanField(
        source="is_active",
        required=False,
        default=True,
        help_text="Indicates whether the role is currently usable.",
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
            raise serializers.ValidationError("Role name cannot be blank or empty.")
        return cleaned


class RoleUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing Role.
    """

    name = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Human-readable role name, unique per company.",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional free-form description of the role's purpose.",
    )
    isActive = serializers.BooleanField(
        source="is_active",
        required=False,
        help_text="Indicates whether the role is currently usable.",
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Role name cannot be blank or empty.")
        return cleaned

