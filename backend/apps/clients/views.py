from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.clients.models import Client
from apps.clients.permissions import ClientPermission
from apps.clients.serializers import (
    ClientCreateSerializer,
    ClientListQuerySerializer,
    ClientSerializer,
    ClientUpdateSerializer,
)
from apps.clients.services import ClientService
from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.users.permissions import is_platform_admin


@extend_schema_view(
    list=extend_schema(
        summary="List Clients",
        description="List tenant clients with search and pagination.",
        parameters=[
            OpenApiParameter(
                name="search",
                description="Search clients by name, company name, email, or mobile.",
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
        responses={status.HTTP_200_OK: ClientSerializer(many=True)},
        tags=["Client"],
    ),
    create=extend_schema(
        summary="Create Client",
        description="Create a new client for a company tenant.",
        request=ClientCreateSerializer,
        responses={status.HTTP_201_CREATED: ClientSerializer},
        tags=["Client"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Client",
        description="Retrieve client details by UUID.",
        responses={status.HTTP_200_OK: ClientSerializer},
        tags=["Client"],
    ),
    partial_update=extend_schema(
        summary="Update Client",
        description="Partially update client details by UUID.",
        request=ClientUpdateSerializer,
        responses={status.HTTP_200_OK: ClientSerializer},
        tags=["Client"],
    ),
    update=extend_schema(
        summary="Full Update Client",
        description="Update forwards to partial_update logic.",
        request=ClientUpdateSerializer,
        responses={status.HTTP_200_OK: ClientSerializer},
        tags=["Client"],
    ),
    destroy=extend_schema(
        summary="Delete Client",
        description="Soft-delete a client by UUID.",
        responses={status.HTTP_200_OK: ClientSerializer},
        tags=["Client"],
    ),
)
class ClientViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for Client CRUD operations. Mirrors apps.users.views.RoleViewSet
    exactly — orchestration only, all business logic lives in ClientService.

    ObjectPermission404Mixin makes cross-tenant object access return 404
    instead of DRF's default 403 (Error_Handling.md §5 anti-enumeration
    rule).
    """

    permission_classes = [IsAuthenticated, ClientPermission]
    pagination_class = StandardPagination
    serializer_class = ClientSerializer
    # Inert at runtime (every action goes through ClientService, not
    # self.get_queryset()/self.get_object()) — exists solely so
    # drf-spectacular can resolve the response model for schema generation.
    queryset = Client.objects.none()
    permission_code_map = {
        "list": "client.view",
        "create": "client.create",
        "retrieve": "client.view",
        "partial_update": "client.edit",
        "update": "client.edit",
        "destroy": "client.delete",
    }

    def list(self, request: Request) -> Response:
        """
        List clients with tenant scoping, search, and ordering.
        """
        query = ClientListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        # No companyId list filter is exposed for Client (unlike Role) —
        # not part of the approved BE-023 scope ("no invented filters"). A
        # platform admin therefore always sees every company's clients on
        # this endpoint, which is the explicit Platform Admin exception in
        # Tenant.md §4, not a gap.
        queryset = ClientService.list_clients_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=None,
            search=validated["search"] or None,
            ordering=validated["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = ClientSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ClientSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        """
        Create a new client within a tenant company.
        """
        serializer = ClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        target_company_id = ClientService.resolve_create_target_company_id(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            supplied_company_id=validated.get("company_id"),
        )

        client = ClientService.create_client(
            company_id=target_company_id,
            name=validated["name"],
            company_name=validated.get("company_name", ""),
            email=validated.get("email", ""),
            mobile=validated.get("mobile", ""),
            gstin=validated.get("gstin", ""),
            addresses=validated.get("addresses"),
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = ClientSerializer(client).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """
        Retrieve details of a single client by UUID.
        """
        client = ClientService.get_client_by_id(pk)
        self.check_object_permissions(request, client)

        response_data = ClientSerializer(client).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def partial_update(self, request: Request, pk: str = None) -> Response:
        """
        Partially update an existing client by UUID.
        """
        client = ClientService.get_client_by_id(pk)
        self.check_object_permissions(request, client)

        serializer = ClientUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_client = ClientService.update_client(
            client_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = ClientSerializer(updated_client).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic — matching the
        existing project convention (RoleViewSet.update()), not a
        Client-specific PUT semantic.
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        """
        Soft-delete a client by UUID.
        """
        client = ClientService.get_client_by_id(pk)
        self.check_object_permissions(request, client)

        ClientService.soft_delete_client(pk, actor_user=request.user, request=request)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Client deleted successfully."},
            request_id=request_id,
        )
