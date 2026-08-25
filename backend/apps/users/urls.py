from django.urls import re_path

from apps.users.views import RoleViewSet

role_list = RoleViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

role_detail = RoleViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

urlpatterns = [
    re_path(r"^roles/?$", role_list, name="role-list"),
    re_path(
        r"^roles/(?P<pk>[0-9a-fA-F-]{36})/?$",
        role_detail,
        name="role-detail",
    ),
]
