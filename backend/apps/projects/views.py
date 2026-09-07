from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.projects.models import Project
from apps.projects.permissions import ProjectPermission
from apps.projects.serializers import (
    ProjectCreateSerializer,
    ProjectListQuerySerializer,
    ProjectMemberCreateSerializer,
    ProjectMemberSerializer,
    ProjectSerializer,
    ProjectStatusTransitionSerializer,
    ProjectUpdateSerializer,
)
from apps.projects.services import ProjectMemberService, ProjectService
from apps.users.permissions import is_platform_admin


@extend_schema_view(
    list=extend_schema(
        summary="List Projects",
        description=(
            "List tenant projects. Filterable by status/client/assignedTo/"
            "priority/startDateFrom/startDateTo/deadlineFrom/deadlineTo, "
            "orderable via ?ordering=."
        ),
        parameters=[ProjectListQuerySerializer],
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
    ViewSet for Project CRUD operations (BE-025), plus the status
    transition action (BE-027), list filtering/ordering (BE-028), and
    audit logging (BE-029, via ProjectService — this ViewSet only
    forwards `actor_user`/`request`). Mirrors
    apps.clients.views.ClientViewSet — orchestration only, all business
    logic lives in ProjectService. Team/member endpoints (BE-026) live
    below in ProjectTeamView/ProjectTeamMemberView — not on this ViewSet,
    since their compound URL (`/projects/{projectId}/team/{userId}`)
    doesn't fit a single-lookup-field @action.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    pagination_class = StandardPagination
    serializer_class = ProjectSerializer
    queryset = Project.objects.none()
    # BE-054: status_transition uses project.edit per the Backend-Lead-
    # approved provisional mapping (RBAC_Enforcement_Matrix.md §4) — a
    # dedicated project.status_manage code was considered and explicitly
    # deferred, not introduced in this task.
    permission_code_map = {
        "list": "project.view",
        "create": "project.create",
        "retrieve": "project.view",
        "partial_update": "project.edit",
        "update": "project.edit",
        "destroy": "project.delete",
        "status_transition": "project.edit",
    }

    def list(self, request: Request) -> Response:
        query = ProjectListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = ProjectService.list_projects_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=None,
            status=validated["status"],
            client_id=validated["client_id"],
            assigned_to_id=validated["assigned_to_id"],
            priority=validated["priority"] or None,
            start_date_from=validated["start_date_from"],
            start_date_to=validated["start_date_to"],
            deadline_from=validated["deadline_from"],
            deadline_to=validated["deadline_to"],
            ordering=validated["ordering"],
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
            actor_user=request.user,
            request=request,
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
            actor_user=request.user,
            request=request,
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

        ProjectService.soft_delete_project(pk, actor_user=request.user, request=request)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Project deleted successfully."},
            request_id=request_id,
        )

    @extend_schema(
        summary="Transition Project Status",
        description=(
            "Transition a project to a new lifecycle status. Only "
            "transitions reachable per the documented status graph are "
            "allowed (409 if not); freely setting any status is not "
            "supported (Project_API.md's own documented constraint)."
        ),
        request=ProjectStatusTransitionSerializer,
        responses={status.HTTP_200_OK: ProjectSerializer},
        tags=["Project"],
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def status_transition(self, request: Request, pk: str = None) -> Response:
        project = ProjectService.get_project_by_id(pk)
        self.check_object_permissions(request, project)

        serializer = ProjectStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_project = ProjectService.transition_status(
            project_id=pk,
            target_status=serializer.validated_data["status"],
            actor_user=request.user,
            request=request,
        )
        response_data = ProjectSerializer(updated_project).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class ProjectTeamView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /projects/{projectId}/team` (BE-026). Reuses
    ProjectPermission directly — object-level authorization here is
    fundamentally "does the caller belong to this Project's company",
    the same check ProjectViewSet already performs; a separate
    ProjectMemberPermission class would just duplicate it. Fetches the
    parent Project exactly like ProjectViewSet.retrieve does (bare
    get_project_by_id + check_object_permissions), so a cross-tenant
    projectId 404s instead of 403ing, per Error_Handling.md §5.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "project.view", "post": "project.manage"}

    @extend_schema(
        summary="List Project Team",
        description="List the users assigned to this project's team.",
        responses={status.HTTP_200_OK: ProjectMemberSerializer(many=True)},
        tags=["Project"],
    )
    def get(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        members = ProjectMemberService.list_members(project)
        serializer = ProjectMemberSerializer(members, many=True)
        return ApiResponse.success(
            data=serializer.data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Add Project Team Member",
        description="Assign a user to this project's team. The user must be an active member of the project's company.",
        request=ProjectMemberCreateSerializer,
        responses={status.HTTP_201_CREATED: ProjectMemberSerializer},
        tags=["Project"],
    )
    def post(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        serializer = ProjectMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = ProjectMemberService.add_member(
            project=project,
            user_id=serializer.validated_data["user_id"],
            assigned_by_id=getattr(request.user, "id", None),
            actor_user=request.user,
            request=request,
        )

        response_data = ProjectMemberSerializer(member).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class ProjectTeamMemberView(ObjectPermission404Mixin, APIView):
    """
    `DELETE /projects/{projectId}/team/{userId}` (BE-026). Same
    parent-Project authorization pattern as ProjectTeamView.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "project.manage"

    @extend_schema(
        summary="Remove Project Team Member",
        description="Remove a user from this project's team.",
        responses={status.HTTP_200_OK: None},
        tags=["Project"],
    )
    def delete(self, request: Request, project_id: str = None, user_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        ProjectMemberService.remove_member(
            project=project, user_id=user_id, actor_user=request.user, request=request
        )

        return ApiResponse.success(
            data={"message": "Team member removed successfully."},
            request_id=getattr(request, "request_id", None),
        )
