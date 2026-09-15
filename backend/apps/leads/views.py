from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.leads.models import Lead
from apps.leads.permissions import LeadPermission
from apps.leads.serializers import (
    LeadConvertSerializer,
    LeadCreateSerializer,
    LeadListQuerySerializer,
    LeadMarkLostSerializer,
    LeadSerializer,
    LeadStatusTransitionSerializer,
    LeadUpdateSerializer,
)
from apps.leads.services import LeadService
from apps.users.permissions import is_platform_admin


@extend_schema_view(
    list=extend_schema(
        summary="List Leads",
        description="List tenant leads. Filterable by status/assignedTo, searchable by name/companyName/email/mobile, orderable via ?ordering=.",
        parameters=[
            OpenApiParameter(name="status", required=False, type=str),
            OpenApiParameter(name="assignedTo", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
            OpenApiParameter(name="ordering", required=False, type=str),
        ],
        responses={status.HTTP_200_OK: LeadSerializer(many=True)},
        tags=["Leads"],
    ),
    create=extend_schema(
        summary="Create Lead",
        description="Create a new lead for a company tenant. Always starts at status=new.",
        request=LeadCreateSerializer,
        responses={status.HTTP_201_CREATED: LeadSerializer},
        tags=["Leads"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Lead",
        responses={status.HTTP_200_OK: LeadSerializer},
        tags=["Leads"],
    ),
    partial_update=extend_schema(
        summary="Update Lead",
        description="Update a lead's identity/assignment/notes fields. Status is not settable here.",
        request=LeadUpdateSerializer,
        responses={status.HTTP_200_OK: LeadSerializer},
        tags=["Leads"],
    ),
    update=extend_schema(
        summary="Full Update Lead",
        description="Update forwards to partial_update logic.",
        request=LeadUpdateSerializer,
        responses={status.HTTP_200_OK: LeadSerializer},
        tags=["Leads"],
    ),
    destroy=extend_schema(
        summary="Delete Lead",
        description="Soft-delete a lead by UUID.",
        responses={status.HTTP_200_OK: LeadSerializer},
        tags=["Leads"],
    ),
)
class LeadViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for Lead CRUD + status-transition/mark-lost/convert
    operations (BE-061). Mirrors apps.clients.views.ClientViewSet for
    plain CRUD and apps.projects.views.ProjectViewSet's status_transition
    `@action` pattern for the state-machine endpoints. Orchestration
    only — all business logic lives in LeadService.
    """

    permission_classes = [IsAuthenticated, LeadPermission]
    pagination_class = StandardPagination
    serializer_class = LeadSerializer
    # Inert at runtime (every action goes through LeadService, not
    # self.get_queryset()/self.get_object()) — exists solely so
    # drf-spectacular can resolve the response model for schema generation.
    queryset = Lead.objects.none()
    permission_code_map = {
        "list": "lead.view",
        "create": "lead.create",
        "retrieve": "lead.view",
        "partial_update": "lead.edit",
        "update": "lead.edit",
        "destroy": "lead.delete",
        "status_transition": "lead.edit",
        "mark_lost": "lead.edit",
        "convert": "lead.convert",
    }

    def list(self, request: Request) -> Response:
        query = LeadListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = LeadService.list_leads_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=None,
            status=validated["status"],
            assigned_to_id=validated["assigned_to_id"],
            search=validated["search"] or None,
            ordering=validated["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = LeadSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LeadSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        serializer = LeadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        target_company_id = LeadService.resolve_create_target_company_id(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            supplied_company_id=validated.get("company_id"),
        )

        lead = LeadService.create_lead(
            company_id=target_company_id,
            name=validated["name"],
            company_name=validated.get("company_name", ""),
            email=validated.get("email", ""),
            mobile=validated.get("mobile", ""),
            source=validated.get("source", ""),
            assigned_to_id=validated.get("assigned_to_id"),
            follow_up_reminder_at=validated.get("follow_up_reminder_at"),
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = LeadSerializer(lead).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        lead = LeadService.get_lead_by_id(pk)
        self.check_object_permissions(request, lead)

        response_data = LeadSerializer(lead).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))

    def partial_update(self, request: Request, pk: str = None) -> Response:
        lead = LeadService.get_lead_by_id(pk)
        self.check_object_permissions(request, lead)

        serializer = LeadUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_lead = LeadService.update_lead(
            lead_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = LeadSerializer(updated_lead).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))

    def update(self, request: Request, pk: str = None) -> Response:
        """Full update forwards to partial_update logic — matching the existing project convention."""
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        lead = LeadService.get_lead_by_id(pk)
        self.check_object_permissions(request, lead)

        LeadService.soft_delete_lead(pk, actor_user=request.user, request=request)
        return ApiResponse.success(
            data={"message": "Lead deleted successfully."},
            request_id=getattr(request, "request_id", None),
        )

    @extend_schema(
        summary="Transition Lead Status",
        description="Move a lead forward one step in the documented flow, or mark it lost. WON is never reachable here — see POST .../convert.",
        request=LeadStatusTransitionSerializer,
        responses={status.HTTP_200_OK: LeadSerializer},
        tags=["Leads"],
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def status_transition(self, request: Request, pk: str = None) -> Response:
        lead = LeadService.get_lead_by_id(pk)
        self.check_object_permissions(request, lead)

        serializer = LeadStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_lead = LeadService.transition_status(
            lead_id=pk,
            target_status=serializer.validated_data["status"],
            actor_user=request.user,
            request=request,
        )
        response_data = LeadSerializer(updated_lead).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))

    @extend_schema(
        summary="Mark Lead Lost",
        description="Mark a lead as lost. Requires a loss reason; an optional follow-up reminder date may also be set.",
        request=LeadMarkLostSerializer,
        responses={status.HTTP_200_OK: LeadSerializer},
        tags=["Leads"],
    )
    @action(detail=True, methods=["post"], url_path="mark-lost")
    def mark_lost(self, request: Request, pk: str = None) -> Response:
        lead = LeadService.get_lead_by_id(pk)
        self.check_object_permissions(request, lead)

        serializer = LeadMarkLostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated_lead = LeadService.mark_lost(
            lead_id=pk,
            loss_reason=validated["loss_reason"],
            follow_up_reminder_at=validated.get("follow_up_reminder_at"),
            actor_user=request.user,
            request=request,
        )
        response_data = LeadSerializer(updated_lead).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))

    @extend_schema(
        summary="Convert Lead",
        description="Convert a lead into a real Client (optionally also creating a Project). Idempotent — calling this again on an already-converted lead returns the existing result.",
        request=LeadConvertSerializer,
        responses={status.HTTP_200_OK: LeadSerializer},
        tags=["Leads"],
    )
    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request: Request, pk: str = None) -> Response:
        lead = LeadService.get_lead_by_id(pk)
        self.check_object_permissions(request, lead)

        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated_lead = LeadService.convert_lead(
            lead_id=pk,
            create_project=validated.get("create_project", False),
            project_name=validated.get("project_name"),
            actor_user=request.user,
            request=request,
        )
        response_data = LeadSerializer(updated_lead).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))
