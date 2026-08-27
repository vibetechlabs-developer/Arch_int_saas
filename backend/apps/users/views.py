from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.users.models import Role
from apps.users.permissions import RolePermission, is_platform_admin
from apps.users.serializers import (
    RoleCreateSerializer,
    RoleListQuerySerializer,
    RoleSerializer,
    RoleUpdateSerializer,
)
from apps.users.services import RoleService


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
