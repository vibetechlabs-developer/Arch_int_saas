from django.urls import re_path

from apps.clients.views import ClientViewSet

client_list = ClientViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

client_detail = ClientViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

urlpatterns = [
    re_path(r"^clients/?$", client_list, name="client-list"),
    re_path(
        r"^clients/(?P<pk>[0-9a-fA-F-]{36})/?$",
        client_detail,
        name="client-detail",
    ),
]
