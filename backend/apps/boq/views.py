from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.boq.models import BOQSection
from apps.boq.serializers import (
    BOQSectionCreateSerializer,
    BOQSectionSerializer,
    BOQSectionUpdateSerializer,
    BOQSerializer,
)
from apps.boq.services import BOQSectionService, BOQService
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.projects.permissions import ProjectPermission
from apps.projects.services import ProjectService


class BOQDetailView(ObjectPermission404Mixin, APIView):
    """
    `GET /projects/{projectId}/boq` (BE-035). Reuses ProjectPermission
    directly — object-level authorization here is "does the caller belong
    to this Project's company", the same check ProjectViewSet performs;
    mirrors ProjectTeamView's reasoning for not building a near-duplicate
    permission class. Auto-creates the BOQ on first access (Backend Lead
    decision, 2026-08-31) rather than requiring a separate create step.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Get Project BOQ",
        description="Get a project's BOQ (sections, and from BE-036 on, items). Auto-created on first access.",
        responses={status.HTTP_200_OK: BOQSerializer},
        tags=["BOQ"],
    )
    def get(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        boq = BOQService.get_or_create_boq_for_project(
            project, actor_user=request.user, request=request
        )

        response_data = BOQSerializer(boq).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class BOQSectionListCreateView(ObjectPermission404Mixin, APIView):
    """
    `POST /projects/{projectId}/boq/sections` (BE-035). No GET here —
    BOQ_API.md documents no separate section-list endpoint; sections are
    retrieved via the parent BOQDetailView's tree. Same permission reuse
    and auto-create-on-access pattern as BOQDetailView.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Add BOQ Section",
        description="Add a section to a project's BOQ (auto-created if it doesn't exist yet).",
        request=BOQSectionCreateSerializer,
        responses={status.HTTP_201_CREATED: BOQSectionSerializer},
        tags=["BOQ"],
    )
    def post(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        boq = BOQService.get_or_create_boq_for_project(
            project, actor_user=request.user, request=request
        )

        serializer = BOQSectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        section = BOQSectionService.create_section(
            boq=boq,
            name=serializer.validated_data["name"],
            actor_user=request.user,
            request=request,
        )

        response_data = BOQSectionSerializer(section).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


@extend_schema_view(
    partial_update=extend_schema(
        summary="Update BOQ Section",
        description="Partially update a BOQ section's name by UUID (added for CRUD consistency — not documented in BOQ_API.md).",
        request=BOQSectionUpdateSerializer,
        responses={status.HTTP_200_OK: BOQSectionSerializer},
        tags=["BOQ"],
    ),
    update=extend_schema(
        summary="Full Update BOQ Section",
        description="Update forwards to partial_update logic.",
        request=BOQSectionUpdateSerializer,
        responses={status.HTTP_200_OK: BOQSectionSerializer},
        tags=["BOQ"],
    ),
    destroy=extend_schema(
        summary="Delete BOQ Section",
        description="Soft-delete a BOQ section by UUID (added for CRUD consistency — not documented in BOQ_API.md).",
        responses={status.HTTP_200_OK: BOQSectionSerializer},
        tags=["BOQ"],
    ),
)
class BOQSectionViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    Flat detail-only actions for BOQSection (`/boq-sections/{id}`,
    BE-035) — mirrors ProductSubcategoryViewSet's split (list/create
    nested under the parent, detail actions flat). Tenant authorization
    resolves through `section.boq.company_id` (BOQSection has no direct
    `company` column) via ProjectPermission's generic `obj.company_id`
    check — BOQSectionService.get_section_by_id returns a section whose
    `.company_id` isn't a real attribute, so `check_object_permissions`
    is called against `section.boq` instead, not `section` itself.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    serializer_class = BOQSectionSerializer
    queryset = BOQSection.objects.none()

    def partial_update(self, request: Request, pk: str = None) -> Response:
        section = BOQSectionService.get_section_by_id(pk)
        self.check_object_permissions(request, section.boq)

        serializer = BOQSectionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_section = BOQSectionService.update_section(
            section_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = BOQSectionSerializer(updated_section).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic — matching the
        existing convention.
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        section = BOQSectionService.get_section_by_id(pk)
        self.check_object_permissions(request, section.boq)

        BOQSectionService.soft_delete_section(pk, actor_user=request.user, request=request)
        return ApiResponse.success(
            data={"message": "BOQ section deleted successfully."},
            request_id=getattr(request, "request_id", None),
        )
