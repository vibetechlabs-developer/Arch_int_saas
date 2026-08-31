from django.urls import re_path

from apps.projects.views import ProjectViewSet

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

urlpatterns = [
    re_path(r"^projects/?$", project_list, name="project-list"),
    re_path(
        r"^projects/(?P<pk>[0-9a-fA-F-]{36})/?$",
        project_detail,
        name="project-detail",
    ),
]
