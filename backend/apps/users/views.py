from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.common.permissions import get_active_membership_for_request, is_platform_admin
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.users.models import CompanyMembership, Role
from apps.users.permissions import CompanyMembershipPermission, RolePermission
from apps.users.serializers import (
    AddUserResponseSerializer,
    AddUserSerializer,
    CompanyMembershipAssignRoleSerializer,
    CompanyMembershipInviteSerializer,
    CompanyMembershipListQuerySerializer,
    CompanyMembershipSerializer,
    PermissionSerializer,
    RoleCreateSerializer,
    RoleListQuerySerializer,
    RolePermissionAssignSerializer,
    RoleSerializer,
    RoleUpdateSerializer,
)
from apps.users.services import CompanyMembershipService, PermissionService, RoleService


@extend_schema_view(
    list=extend_schema(
        summary="List Roles",
        description="List tenant roles with search, status filtering, and pagination.",
        parameters=[
            OpenApiParameter(
                name="companyId",
                description="Filter by Company UUID (Platform Admin only or verified member company).",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="isActive",
                description="Filter by active status (true/false).",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="search",
                description="Search roles by name or description.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                description="Ordering field (e.g. name, -name, created_at, -created_at).",
                required=False,
                type=str,
            ),
        ],
        responses={status.HTTP_200_OK: RoleSerializer(many=True)},
        tags=["Role"],
    ),
    create=extend_schema(
        summary="Create Role",
        description="Create a new role for a company tenant.",
        request=RoleCreateSerializer,
        responses={status.HTTP_201_CREATED: RoleSerializer},
        tags=["Role"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Role",
        description="Retrieve role details by UUID.",
        responses={status.HTTP_200_OK: RoleSerializer},
        tags=["Role"],
    ),
    partial_update=extend_schema(
        summary="Update Role",
        description="Partially update role details by UUID.",
        request=RoleUpdateSerializer,
        responses={status.HTTP_200_OK: RoleSerializer},
        tags=["Role"],
    ),
    update=extend_schema(
        summary="Full Update Role",
        description="Update role details by UUID.",
        request=RoleUpdateSerializer,
        responses={status.HTTP_200_OK: RoleSerializer},
        tags=["Role"],
    ),
    destroy=extend_schema(
        summary="Delete Role",
        description="Soft-delete a role by UUID.",
        responses={status.HTTP_200_OK: RoleSerializer},
        tags=["Role"],
    ),
)
class RoleViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for Role CRUD operations.
    Enforces standard ApiResponse envelopes, pagination, and tenant isolation boundaries.

    ObjectPermission404Mixin (apps/common/views.py) makes cross-tenant
    object access return 404 instead of DRF's default 403 — deferred at
    BE-018 (applied there only to CompanyViewSet) and closed out here.
    """

    permission_classes = [IsAuthenticated, RolePermission]
    pagination_class = StandardPagination
    serializer_class = RoleSerializer
    # Every action below is fully overridden and goes through RoleService
    # rather than self.get_queryset()/self.get_object() — this attribute is
    # inert at runtime and exists solely so drf-spectacular (BE-016) can
    # resolve the response model for schema generation.
    queryset = Role.objects.none()
    # BE-054: role.view covers read actions; role.manage covers every
    # mutation, including the permission-assignment action below — RBAC
    # configuring itself requires the same code as configuring roles
    # generally, per the enforcement matrix.
    permission_code_map = {
        "list": "role.view",
        "create": "role.manage",
        "retrieve": "role.view",
        "partial_update": "role.manage",
        "update": "role.manage",
        "destroy": "role.manage",
        "permissions_action": "role.manage",
    }

    def list(self, request: Request) -> Response:
        """
        List roles with tenant scoping, status filter, search, and ordering.

        Orchestration only — validates request shape (query params, via
        RoleListQuerySerializer) and hands the caller's admin status +
        resolved tenant context to RoleService.list_roles_for_viewer(),
        which owns the actual scoping decision.
        """
        query = RoleListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        admin_company_id_param = str(validated["company_id"]) if validated["company_id"] else None

        queryset = RoleService.list_roles_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=admin_company_id_param,
            is_active=validated["is_active"],
            search=validated["search"] or None,
            ordering=validated["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = RoleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RoleSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        """
        Create a new role within a tenant company.

        Orchestration only — validates input (serializer) and hands the
        caller's admin status + resolved tenant context + any client-
        supplied companyId to RoleService.resolve_create_target_company_id(),
        which owns the authorization decision, before delegating persistence
        to RoleService.create_role().
        """
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_company_id = RoleService.resolve_create_target_company_id(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            supplied_company_id=serializer.validated_data.get("company_id"),
        )

        role = RoleService.create_role(
            company_id=target_company_id,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            is_active=serializer.validated_data.get("is_active", True),
            actor_user=request.user,
            request=request,
        )

        response_data = RoleSerializer(role).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """
        Retrieve details of a single role by UUID.
        """
        role = RoleService.get_role_by_id(pk)
        self.check_object_permissions(request, role)

        response_data = RoleSerializer(role).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def partial_update(self, request: Request, pk: str = None) -> Response:
        """
        Partially update an existing role by UUID.
        """
        role = RoleService.get_role_by_id(pk)
        self.check_object_permissions(request, role)

        serializer = RoleUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_role = RoleService.update_role(
            role_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = RoleSerializer(updated_role).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic.
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        """
        Soft-delete a role by UUID.
        """
        role = RoleService.get_role_by_id(pk)
        self.check_object_permissions(request, role)

        RoleService.soft_delete_role(pk, actor_user=request.user, request=request)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Role deleted successfully."},
            request_id=request_id,
        )

    @extend_schema(
        summary="Assign Role Permissions",
        description="Replace a role's permission-code grants with the given full set (BE-049/BE-051).",
        request=RolePermissionAssignSerializer,
        responses={status.HTTP_200_OK: RoleSerializer},
        tags=["Role"],
    )
    @action(detail=True, methods=["put"], url_path="permissions")
    def permissions_action(self, request: Request, pk: str = None) -> Response:
        """
        `PUT /roles/{id}/permissions` — replace this role's permission-code
        grants. Not yet enforced by any view (BE-054 is separate); exists so
        Company Admins can start composing role permission sets ahead of
        that cutover.
        """
        role = RoleService.get_role_by_id(pk)
        self.check_object_permissions(request, role)

        serializer = RolePermissionAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = RoleService.assign_permissions(
            role_id=pk,
            codes=serializer.validated_data["codes"],
            actor_user=request.user,
            actor_membership=None if is_platform_admin(request) else get_active_membership_for_request(request),
            request=request,
        )
        response_data = RoleSerializer(role).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)


class PermissionListView(APIView):
    """
    `GET /permissions` — the global Permission catalog (BE-049). Read-only;
    the catalog is seeded via migration, not managed through this API.
    """

    # BE-054: deliberately left on bare IsAuthenticated, not
    # TenantScopedPermission — a read-only, non-tenant-scoped reference
    # catalog (per the enforcement matrix's explicit decision), not a
    # business resource that needs a permission code.
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List Permissions",
        description="List the global RBAC permission-code catalog.",
        responses={status.HTTP_200_OK: PermissionSerializer(many=True)},
        tags=["Role"],
    )
    def get(self, request: Request) -> Response:
        permissions_qs = PermissionService.list_all_permissions()
        data = PermissionSerializer(permissions_qs, many=True).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=data, request_id=request_id)


@extend_schema_view(
    list=extend_schema(
        summary="List Company Members",
        description="List this company's memberships with status filtering, search, and pagination.",
        parameters=[
            OpenApiParameter(name="status", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
            OpenApiParameter(name="ordering", required=False, type=str),
        ],
        responses={status.HTTP_200_OK: CompanyMembershipSerializer(many=True)},
        tags=["Company Membership"],
    ),
    create=extend_schema(
        summary="Invite Member",
        description="Invite an existing user (by email) into this company, optionally with a role.",
        request=CompanyMembershipInviteSerializer,
        responses={status.HTTP_201_CREATED: CompanyMembershipSerializer},
        tags=["Company Membership"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Membership",
        responses={status.HTTP_200_OK: CompanyMembershipSerializer},
        tags=["Company Membership"],
    ),
    destroy=extend_schema(
        summary="Remove Member",
        description="Soft-delete a company membership.",
        responses={status.HTTP_200_OK: None},
        tags=["Company Membership"],
    ),
)
class CompanyMembershipViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for Company Membership management (BE-052): invite, list,
    retrieve, remove, suspend, reactivate, assign role. Mirrors RoleViewSet's
    structure exactly (fully-overridden actions through
    CompanyMembershipService, ObjectPermission404Mixin for cross-tenant
    404s, standard ApiResponse envelopes).
    """

    permission_classes = [IsAuthenticated, CompanyMembershipPermission]
    pagination_class = StandardPagination
    serializer_class = CompanyMembershipSerializer
    queryset = CompanyMembership.objects.none()
    # BE-054: user.view covers read actions; user.manage covers every
    # membership-mutating action per the enforcement matrix.
    permission_code_map = {
        "list": "user.view",
        "create": "user.manage",
        "retrieve": "user.view",
        "destroy": "user.manage",
        "assign_role": "user.manage",
        "suspend": "user.manage",
        "reactivate": "user.manage",
        # Same code as invite/assign-role/suspend/reactivate — "user.manage"
        # already reads as "invite, remove, suspend, and assign roles to
        # company members" (permission_catalog.py), which covers adding a
        # genuinely new person exactly as well as inviting an existing one.
        # No new permission code was introduced for this.
        "add_user": "user.manage",
    }

    def list(self, request: Request) -> Response:
        query = CompanyMembershipListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = CompanyMembershipService.list_memberships(
            company_id=request.company_id,
            status=validated["status"],
            search=validated["search"] or None,
            ordering=validated["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = CompanyMembershipSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CompanyMembershipSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        serializer = CompanyMembershipInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = CompanyMembershipService.invite_member(
            company_id=request.company_id,
            email=serializer.validated_data["email"],
            role_id=serializer.validated_data.get("role_id"),
            actor_user=request.user,
            actor_membership=None if is_platform_admin(request) else get_active_membership_for_request(request),
            request=request,
        )

        response_data = CompanyMembershipSerializer(membership).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.created(data=response_data, request_id=request_id)

    @extend_schema(
        summary="Add User",
        description=(
            "Add a person to this company by email, creating a new User account if none exists "
            "for that email yet, or linking their existing account (never duplicated). Assigns "
            "the given role and creates an active CompanyMembership."
        ),
        request=AddUserSerializer,
        responses={status.HTTP_201_CREATED: AddUserResponseSerializer},
        tags=["Company Membership"],
    )
    @action(detail=False, methods=["post"], url_path="add-user")
    def add_user(self, request: Request) -> Response:
        """
        `POST /company-memberships/add-user` — the genuine new-user
        onboarding flow, distinct from `create` (invite_member), which
        only ever links an existing account and 404s otherwise.
        """
        serializer = AddUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership, user_created, activation_required = CompanyMembershipService.add_user(
            company_id=request.company_id,
            email=serializer.validated_data["email"],
            name=serializer.validated_data["name"],
            role_id=serializer.validated_data.get("role_id"),
            actor_user=request.user,
            actor_membership=None if is_platform_admin(request) else get_active_membership_for_request(request),
            request=request,
        )

        response_data = AddUserResponseSerializer(
            {
                "membership": membership,
                "user_created": user_created,
                "activation_required": activation_required,
            }
        ).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        membership = CompanyMembershipService.get_membership_by_id(pk)
        self.check_object_permissions(request, membership)

        response_data = CompanyMembershipSerializer(membership).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=response_data, request_id=request_id)

    def destroy(self, request: Request, pk: str = None) -> Response:
        membership = CompanyMembershipService.get_membership_by_id(pk)
        self.check_object_permissions(request, membership)

        CompanyMembershipService.remove_member(pk, actor_user=request.user, request=request)
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(
            data={"message": "Membership removed successfully."},
            request_id=request_id,
        )

    @extend_schema(
        summary="Assign Member Role",
        description="Assign, change, or clear (roleId=null) a membership's role.",
        request=CompanyMembershipAssignRoleSerializer,
        responses={status.HTTP_200_OK: CompanyMembershipSerializer},
        tags=["Company Membership"],
    )
    @action(detail=True, methods=["post"], url_path="assign-role")
    def assign_role(self, request: Request, pk: str = None) -> Response:
        membership = CompanyMembershipService.get_membership_by_id(pk)
        self.check_object_permissions(request, membership)

        serializer = CompanyMembershipAssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = CompanyMembershipService.assign_role(
            membership_id=pk,
            role_id=serializer.validated_data["role_id"],
            actor_user=request.user,
            actor_membership=None if is_platform_admin(request) else get_active_membership_for_request(request),
            request=request,
        )
        response_data = CompanyMembershipSerializer(membership).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=response_data, request_id=request_id)

    @extend_schema(
        summary="Suspend Member",
        description="Revoke a company membership's active status.",
        responses={status.HTTP_200_OK: CompanyMembershipSerializer},
        tags=["Company Membership"],
    )
    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend(self, request: Request, pk: str = None) -> Response:
        membership = CompanyMembershipService.get_membership_by_id(pk)
        self.check_object_permissions(request, membership)

        membership = CompanyMembershipService.suspend_member(
            pk, actor_user=request.user, request=request
        )
        response_data = CompanyMembershipSerializer(membership).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=response_data, request_id=request_id)

    @extend_schema(
        summary="Reactivate Member",
        description="Restore a revoked company membership to active status.",
        responses={status.HTTP_200_OK: CompanyMembershipSerializer},
        tags=["Company Membership"],
    )
    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate(self, request: Request, pk: str = None) -> Response:
        membership = CompanyMembershipService.get_membership_by_id(pk)
        self.check_object_permissions(request, membership)

        membership = CompanyMembershipService.reactivate_member(
            pk, actor_user=request.user, request=request
        )
        response_data = CompanyMembershipSerializer(membership).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=response_data, request_id=request_id)
