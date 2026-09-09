from rest_framework import serializers

from apps.users.models import CompanyMembership, CompanyMembershipStatus, Permission, Role, User
from apps.users.selectors import MEMBERSHIP_ORDER_FIELDS, VALID_ORDER_FIELDS


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
    roleId = serializers.UUIDField(source="role_id", read_only=True, allow_null=True)
    roleName = serializers.CharField(source="role.name", read_only=True, allow_null=True, default=None)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = CompanyMembership
        fields = [
            "id",
            "companyId",
            "companyName",
            "companyStatus",
            "userId",
            "userEmail",
            "userName",
            "roleId",
            "roleName",
            "status",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = fields


class MyMembershipSerializer(serializers.ModelSerializer):
    """
    Minimal per-membership shape for GET /auth/memberships (BE-053) —
    workspace switching only needs enough to label and select a company;
    deliberately excludes anything not needed for that (e.g. other members,
    company financial/settings data).
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    companyName = serializers.CharField(source="company.name", read_only=True)
    roleName = serializers.CharField(source="role.name", read_only=True, allow_null=True, default=None)

    class Meta:
        model = CompanyMembership
        fields = ["companyId", "companyName", "status", "roleName"]
        read_only_fields = fields


class CompanyMembershipInviteSerializer(serializers.Serializer):
    """
    Input serializer for inviting an existing user into a company (BE-052).

    roleId is required (BE-054 §1) — the product has no defined default
    role for a new membership, so the inviter must explicitly pick one
    rather than the platform silently leaving the membership role-less
    (which, under enforcement, would mean zero permission codes).
    """

    email = serializers.EmailField(required=True)
    roleId = serializers.UUIDField(source="role_id", required=True)


class AddUserSerializer(serializers.Serializer):
    """
    Input serializer for CompanyMembershipService.add_user — unlike
    CompanyMembershipInviteSerializer, this genuinely creates a new User
    when the email has no existing account, so it also collects `name`
    (User's only name field — no firstName/lastName split exists on the
    model).
    """

    email = serializers.EmailField(required=True)
    name = serializers.CharField(required=True, max_length=255)
    roleId = serializers.UUIDField(source="role_id", required=True)


class AddUserResponseSerializer(serializers.Serializer):
    """
    Wraps CompanyMembershipSerializer with the two flags the frontend
    needs to render an accurate outcome message — whether a brand-new
    User record was created vs. an existing one was linked, and whether
    an account-setup email was sent.
    """

    membership = CompanyMembershipSerializer()
    userCreated = serializers.BooleanField(source="user_created")
    activationRequired = serializers.BooleanField(source="activation_required")


class CompanyMembershipAssignRoleSerializer(serializers.Serializer):
    """
    Input serializer for assigning/changing/clearing a membership's role.
    roleId=null clears the role assignment.
    """

    roleId = serializers.UUIDField(source="role_id", required=True, allow_null=True)


class CompanyMembershipListQuerySerializer(serializers.Serializer):
    """
    Validates ?status=/?search=/?ordering= query params for
    GET /company-memberships.
    """

    status = serializers.ChoiceField(
        choices=CompanyMembershipStatus.choices, required=False, allow_null=True, default=None
    )
    search = serializers.CharField(required=False, allow_blank=True, default="")
    ordering = serializers.ChoiceField(
        choices=sorted(MEMBERSHIP_ORDER_FIELDS), required=False, default="-created_at"
    )


class PermissionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the global Permission catalog.
    """

    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "code", "module", "action", "description", "createdAt"]
        read_only_fields = fields


class RolePermissionAssignSerializer(serializers.Serializer):
    """
    Input serializer for replacing a role's permission-code grants
    (BE-049/BE-051).
    """

    permissionCodes = serializers.ListField(
        source="codes",
        child=serializers.CharField(),
        required=True,
        allow_empty=True,
        help_text="Full replacement set of `<module>.<action>` codes for this role.",
    )


class RolePermissionsSerializer(serializers.Serializer):
    """
    Output serializer for GET /roles/{id}/permissions (BE-072) — the
    role's currently *persisted* grants, read from RolePermission via
    PermissionRepository.codes_for_role, never reconstructed from
    DEFAULT_ROLE_PERMISSIONS or any other seed/default data.
    """

    roleId = serializers.UUIDField(source="role_id", read_only=True)
    permissionCodes = serializers.ListField(child=serializers.CharField(), read_only=True)


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


class RoleListQuerySerializer(serializers.Serializer):
    """
    Validates ?companyId=/?isActive=/?search=/?ordering= query params for
    GET /roles — replaces the manual string parsing that previously lived
    in RoleViewSet.list(). An invalid value for any of these now returns
    400 VALIDATION_ERROR instead of being silently ignored/coerced.
    """

    companyId = serializers.UUIDField(source="company_id", required=False, allow_null=True, default=None)
    isActive = serializers.BooleanField(source="is_active", required=False, allow_null=True, default=None)
    search = serializers.CharField(required=False, allow_blank=True, default="")
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_ORDER_FIELDS), required=False, default="-created_at"
    )


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

