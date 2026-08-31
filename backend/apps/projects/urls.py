from django.urls import re_path

from apps.projects.views import ProjectTeamMemberView, ProjectTeamView, ProjectViewSet

project_list = ProjectViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

project_detail = ProjectViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

project_status = ProjectViewSet.as_view(
    {
        "patch": "status_transition",
    }
)

urlpatterns = [
    re_path(r"^projects/?$", project_list, name="project-list"),
    re_path(
        r"^projects/(?P<pk>[0-9a-fA-F-]{36})/?$",
        project_detail,
        name="project-detail",
    ),
    re_path(
        r"^projects/(?P<pk>[0-9a-fA-F-]{36})/status/?$",
        project_status,
        name="project-status",
    ),
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/team/?$",
        ProjectTeamView.as_view(),
        name="project-team-list",
    ),
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/team/(?P<user_id>[0-9a-fA-F-]{36})/?$",
        ProjectTeamMemberView.as_view(),
        name="project-team-detail",
    ),
]
