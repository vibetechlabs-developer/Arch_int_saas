from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.projects.models import Project
from apps.projects.permissions import ProjectPermission
from apps.projects.serializers import (
    ProjectCreateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)
from apps.projects.services import ProjectService
from apps.users.permissions import is_platform_admin


@extend_schema_view(
    list=extend_schema(
        summary="List Projects",
        description="List tenant projects. Search/filtering belongs to a later task (BE-028).",
        responses={status.HTTP_200_OK: ProjectSerializer(many=True)},
        tags=["Project"],
    ),
    create=extend_schema(
        summary="Create Project",
        description="Create a new project for a company tenant. Status always starts at 'draft'.",
        request=ProjectCreateSerializer,
        responses={status.HTTP_201_CREATED: ProjectSerializer},
        tags=["Project"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Project",
        description="Retrieve project details by UUID.",
        responses={status.HTTP_200_OK: ProjectSerializer},
        tags=["Project"],
    ),
    partial_update=extend_schema(
        summary="Update Project",
        description="Partially update project details by UUID (name/dates/priority/assignedTo only).",
        request=ProjectUpdateSerializer,
        responses={status.HTTP_200_OK: ProjectSerializer},
        tags=["Project"],
    ),
    update=extend_schema(
        summary="Full Update Project",
        description="Update forwards to partial_update logic.",
        request=ProjectUpdateSerializer,
        responses={status.HTTP_200_OK: ProjectSerializer},
        tags=["Project"],
    ),
    destroy=extend_schema(
        summary="Delete Project",
        description="Soft-delete a project by UUID.",
        responses={status.HTTP_200_OK: ProjectSerializer},
        tags=["Project"],
    ),
)
class ProjectViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for Project CRUD operations (BE-025). Mirrors
    apps.clients.views.ClientViewSet exactly — orchestration only, all
    business logic lives in ProjectService. No status-transition endpoint
    here (BE-027), no team/member endpoints here (BE-026), no
    search/filter query params here (BE-028), no audit calls here (BE-029).
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    pagination_class = StandardPagination
    serializer_class = ProjectSerializer
    queryset = Project.objects.none()

    def list(self, request: Request) -> Response:
        queryset = ProjectService.list_projects_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=None,
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = ProjectSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProjectSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        target_company_id = ProjectService.resolve_create_target_company_id(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            supplied_company_id=validated.get("company_id"),
        )

        project = ProjectService.create_project(
            company_id=target_company_id,
            client_id=validated["client_id"],
            name=validated["name"],
            start_date=validated.get("start_date"),
            deadline=validated.get("deadline"),
            priority=validated.get("priority", ""),
            assigned_to_id=validated.get("assigned_to_id"),
            follow_up_reminder_at=validated.get("follow_up_reminder_at"),
        )

        response_data = ProjectSerializer(project).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        project = ProjectService.get_project_by_id(pk)
        self.check_object_permissions(request, project)

        response_data = ProjectSerializer(project).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def partial_update(self, request: Request, pk: str = None) -> Response:
        project = ProjectService.get_project_by_id(pk)
        self.check_object_permissions(request, project)

        serializer = ProjectUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_project = ProjectService.update_project(
            project_id=pk,
            validated_data=serializer.validated_data,
        )
        response_data = ProjectSerializer(updated_project).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic — matching the
        existing project convention (RoleViewSet/ClientViewSet.update()).
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        project = ProjectService.get_project_by_id(pk)
        self.check_object_permissions(request, project)

        ProjectService.soft_delete_project(pk)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Project deleted successfully."},
            request_id=request_id,
        )
