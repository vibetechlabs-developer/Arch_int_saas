from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework import exceptions as drf_exceptions
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.users.permissions import RolePermission, is_platform_admin
from apps.users.serializers import (
    RoleCreateSerializer,
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
class RoleViewSet(viewsets.GenericViewSet):
    """
    ViewSet for Role CRUD operations.
    Enforces standard ApiResponse envelopes, pagination, and tenant isolation boundaries.
    """

    permission_classes = [IsAuthenticated, RolePermission]
    pagination_class = StandardPagination
    serializer_class = RoleSerializer

    def list(self, request: Request) -> Response:
        """
        List roles with tenant scoping, status filter, search, and ordering.
        """
        company_id_param = request.query_params.get("companyId") or request.query_params.get("company_id")
        is_active_param = request.query_params.get("isActive")
        if is_active_param is None:
            is_active_param = request.query_params.get("is_active")

        is_active = None
        if is_active_param is not None:
            if is_active_param.lower() in ("true", "1"):
                is_active = True
            elif is_active_param.lower() in ("false", "0"):
                is_active = False

        search_query = request.query_params.get("search")
        ordering = request.query_params.get("ordering", "-created_at")

        if is_platform_admin(request):
            queryset = RoleService.list_roles(
                company_id=company_id_param,
                is_active=is_active,
                search=search_query,
                ordering=ordering,
            )
        else:
            user_company_ids = list(
                request.user.memberships.filter(
                    status="active",
                    deleted_at__isnull=True,
                ).values_list("company_id", flat=True)
            )

            if company_id_param:
                if company_id_param not in [str(cid) for cid in user_company_ids]:
                    raise drf_exceptions.PermissionDenied("You do not have access to this company's roles.")
                queryset = RoleService.list_roles(
                    company_id=company_id_param,
                    is_active=is_active,
                    search=search_query,
                    ordering=ordering,
                )
            else:
                queryset = RoleService.list_roles(
                    company_ids=user_company_ids,
                    is_active=is_active,
                    search=search_query,
                    ordering=ordering,
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
        """
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if is_platform_admin(request):
            target_company_id = (
                serializer.validated_data.get("company_id")
                or request.data.get("companyId")
                or request.data.get("company_id")
            )
            if not target_company_id:
                raise drf_exceptions.ValidationError({"companyId": ["companyId is required for platform admin role creation."]})
        else:
            supplied_company_id = (
                serializer.validated_data.get("company_id")
                or request.data.get("companyId")
                or request.data.get("company_id")
            )
            if supplied_company_id:
                if not request.user.memberships.filter(
                    company_id=supplied_company_id,
                    status="active",
                    deleted_at__isnull=True,
                ).exists():
                    raise drf_exceptions.PermissionDenied("You do not have permission to create roles for this company.")
                target_company_id = supplied_company_id
            else:
                membership = request.user.memberships.filter(
                    status="active",
                    deleted_at__isnull=True,
                ).first()
                if not membership:
                    raise drf_exceptions.PermissionDenied("You do not belong to an active company.")
                target_company_id = membership.company_id

        role = RoleService.create_role(
            company_id=target_company_id,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            is_active=serializer.validated_data.get("is_active", True),
            actor_user=request.user,
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

        RoleService.soft_delete_role(pk, actor_user=request.user)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Role deleted successfully."},
            request_id=request_id,
        )
