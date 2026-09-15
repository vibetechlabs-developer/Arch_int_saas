from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.site_visits.models import SiteVisit
from apps.site_visits.permissions import SiteVisitPermission
from apps.site_visits.serializers import (
    SiteVisitCreateSerializer,
    SiteVisitListQuerySerializer,
    SiteVisitReportSerializer,
    SiteVisitSerializer,
    SiteVisitUpdateSerializer,
)
from apps.site_visits.services import SiteVisitService
from apps.users.permissions import is_platform_admin


@extend_schema_view(
    list=extend_schema(
        summary="List Site Visits",
        description="List tenant site visits. Filterable by lead/project/assignedTo, orderable via ?ordering=.",
        parameters=[
            OpenApiParameter(name="lead", required=False, type=str),
            OpenApiParameter(name="project", required=False, type=str),
            OpenApiParameter(name="assignedTo", required=False, type=str),
            OpenApiParameter(name="ordering", required=False, type=str),
        ],
        responses={status.HTTP_200_OK: SiteVisitSerializer(many=True)},
        tags=["Site Visits"],
    ),
    create=extend_schema(
        summary="Create Site Visit",
        description="Schedule a new site visit against a lead and/or a project.",
        request=SiteVisitCreateSerializer,
        responses={status.HTTP_201_CREATED: SiteVisitSerializer},
        tags=["Site Visits"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Site Visit",
        responses={status.HTTP_200_OK: SiteVisitSerializer},
        tags=["Site Visits"],
    ),
    partial_update=extend_schema(
        summary="Update Site Visit",
        description="Update a site visit's captured-on-site fields. Lead/project links are not settable here.",
        request=SiteVisitUpdateSerializer,
        responses={status.HTTP_200_OK: SiteVisitSerializer},
        tags=["Site Visits"],
    ),
    update=extend_schema(
        summary="Full Update Site Visit",
        description="Update forwards to partial_update logic.",
        request=SiteVisitUpdateSerializer,
        responses={status.HTTP_200_OK: SiteVisitSerializer},
        tags=["Site Visits"],
    ),
    destroy=extend_schema(
        summary="Delete Site Visit",
        description="Soft-delete a site visit by UUID.",
        responses={status.HTTP_200_OK: SiteVisitSerializer},
        tags=["Site Visits"],
    ),
)
class SiteVisitViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for SiteVisit CRUD + report-submission operations (BE-062).
    Mirrors apps.leads.views.LeadViewSet's structure. Orchestration
    only — all business logic lives in SiteVisitService.
    """

    permission_classes = [IsAuthenticated, SiteVisitPermission]
    pagination_class = StandardPagination
    serializer_class = SiteVisitSerializer
    queryset = SiteVisit.objects.none()
    permission_code_map = {
        "list": "site_visit.view",
        "create": "site_visit.create",
        "retrieve": "site_visit.view",
        "partial_update": "site_visit.edit",
        "update": "site_visit.edit",
        "destroy": "site_visit.delete",
        "submit_report": "site_visit.report",
    }

    def list(self, request: Request) -> Response:
        query = SiteVisitListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = SiteVisitService.list_site_visits_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=None,
            lead_id=validated["lead_id"],
            project_id=validated["project_id"],
            assigned_to_id=validated["assigned_to_id"],
            ordering=validated["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = SiteVisitSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SiteVisitSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        serializer = SiteVisitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        target_company_id = SiteVisitService.resolve_create_target_company_id(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            supplied_company_id=validated.get("company_id"),
        )

        site_visit = SiteVisitService.create_site_visit(
            company_id=target_company_id,
            lead_id=validated.get("lead_id"),
            project_id=validated.get("project_id"),
            visit_date=validated["visit_date"],
            assigned_to_id=validated.get("assigned_to_id"),
            address=validated.get("address", ""),
            measurements=validated.get("measurements", ""),
            requirements=validated.get("requirements", ""),
            photo_urls=validated.get("photo_urls"),
            video_urls=validated.get("video_urls"),
            notes=validated.get("notes", ""),
            budget=validated.get("budget"),
            site_conditions=validated.get("site_conditions", ""),
            follow_up_actions=validated.get("follow_up_actions", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = SiteVisitSerializer(site_visit).data
        request_id = getattr(request, "request_id", None)
        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        site_visit = SiteVisitService.get_site_visit_by_id(pk)
        self.check_object_permissions(request, site_visit)

        response_data = SiteVisitSerializer(site_visit).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))

    def partial_update(self, request: Request, pk: str = None) -> Response:
        site_visit = SiteVisitService.get_site_visit_by_id(pk)
        self.check_object_permissions(request, site_visit)

        serializer = SiteVisitUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_site_visit = SiteVisitService.update_site_visit(
            site_visit_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = SiteVisitSerializer(updated_site_visit).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))

    def update(self, request: Request, pk: str = None) -> Response:
        """Full update forwards to partial_update logic — matching the existing project/lead convention."""
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        site_visit = SiteVisitService.get_site_visit_by_id(pk)
        self.check_object_permissions(request, site_visit)

        SiteVisitService.soft_delete_site_visit(pk, actor_user=request.user, request=request)
        return ApiResponse.success(
            data={"message": "Site visit deleted successfully."},
            request_id=getattr(request, "request_id", None),
        )

    @extend_schema(
        summary="Submit Site Visit Report",
        description="Mark a site visit complete, optionally creating a new project from its resolved client. Idempotent.",
        request=SiteVisitReportSerializer,
        responses={status.HTTP_200_OK: SiteVisitSerializer},
        tags=["Site Visits"],
    )
    @action(detail=True, methods=["post"], url_path="report")
    def submit_report(self, request: Request, pk: str = None) -> Response:
        site_visit = SiteVisitService.get_site_visit_by_id(pk)
        self.check_object_permissions(request, site_visit)

        serializer = SiteVisitReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated_site_visit = SiteVisitService.submit_report(
            site_visit_id=pk,
            create_project=validated.get("create_project", False),
            project_name=validated.get("project_name"),
            actor_user=request.user,
            request=request,
        )
        response_data = SiteVisitSerializer(updated_site_visit).data
        return ApiResponse.success(data=response_data, request_id=getattr(request, "request_id", None))
