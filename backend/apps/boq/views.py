from django.http import Http404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.boq.models import BOQItem, BOQSection
from apps.boq.serializers import (
    BOQItemCreateSerializer,
    BOQItemSerializer,
    BOQItemUpdateSerializer,
    BOQSectionCreateSerializer,
    BOQSectionSerializer,
    BOQSectionUpdateSerializer,
    BOQSerializer,
)
from apps.boq.services import BOQItemService, BOQSectionService, BOQService
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


class BOQItemListCreateView(ObjectPermission404Mixin, APIView):
    """
    `POST /projects/{projectId}/boq/sections/{sectionId}/items` (BE-036).
    No GET here — items are retrieved via BOQDetailView's tree. Resolves
    `project_id` from the URL for the permission check, then verifies
    `section_id` actually belongs to that project's BOQ (not just the
    same company) — a company can have many projects, each with its own
    BOQ, so a company-level check alone wouldn't catch a section_id from
    a sibling project under the same tenant.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Add BOQ Item",
        description="Add an item to a BOQ section (product reference or free-text).",
        request=BOQItemCreateSerializer,
        responses={status.HTTP_201_CREATED: BOQItemSerializer},
        tags=["BOQ"],
    )
    def post(self, request: Request, project_id: str = None, section_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        section = BOQSectionService.get_section_by_id(section_id, company_id=project.company_id)
        if str(section.boq.project_id) != str(project.id):
            raise Http404

        serializer = BOQItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        item = BOQItemService.create_item(
            section=section,
            product_id=validated.get("product_id"),
            description=validated.get("description", ""),
            quantity=validated["quantity"],
            unit=validated.get("unit", ""),
            rate=validated.get("rate"),
            discount=validated.get("discount"),
            tax=validated.get("tax"),
            is_optional=validated.get("is_optional", False),
            is_alternative=validated.get("is_alternative", False),
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = BOQItemSerializer(item).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


@extend_schema_view(
    partial_update=extend_schema(
        summary="Update BOQ Item",
        description="Edit item (quantity/rate/discount/tax/notes/optional/alternative flags), plus description/unit.",
        request=BOQItemUpdateSerializer,
        responses={status.HTTP_200_OK: BOQItemSerializer},
        tags=["BOQ"],
    ),
    update=extend_schema(
        summary="Full Update BOQ Item",
        description="Update forwards to partial_update logic.",
        request=BOQItemUpdateSerializer,
        responses={status.HTTP_200_OK: BOQItemSerializer},
        tags=["BOQ"],
    ),
    destroy=extend_schema(
        summary="Remove BOQ Item",
        description="Soft-delete a BOQ item by UUID.",
        responses={status.HTTP_200_OK: BOQItemSerializer},
        tags=["BOQ"],
    ),
)
class BOQItemViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    Flat detail-only actions for BOQItem (`/boq-items/{id}`, BE-036),
    matching BOQ_API.md's documented `PATCH`/`DELETE .../boq/items/{itemId}`
    paths exactly (minus the `/projects/{projectId}/boq` prefix — an
    item's own id is already globally unique and sufficient to resolve
    it, the same flat-detail convention every other nested list/create
    endpoint in this codebase uses).
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    serializer_class = BOQItemSerializer
    queryset = BOQItem.objects.none()

    def partial_update(self, request: Request, pk: str = None) -> Response:
        item = BOQItemService.get_item_by_id(pk)
        self.check_object_permissions(request, item.boq_section.boq)

        serializer = BOQItemUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_item = BOQItemService.update_item(
            item_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = BOQItemSerializer(updated_item).data
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
        item = BOQItemService.get_item_by_id(pk)
        self.check_object_permissions(request, item.boq_section.boq)

        BOQItemService.soft_delete_item(pk, actor_user=request.user, request=request)
        return ApiResponse.success(
            data={"message": "BOQ item deleted successfully."},
            request_id=getattr(request, "request_id", None),
        )
