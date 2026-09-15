from django.urls import re_path

from apps.leads.views import LeadViewSet

lead_list = LeadViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

lead_detail = LeadViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

lead_status = LeadViewSet.as_view(
    {
        "patch": "status_transition",
    }
)

lead_mark_lost = LeadViewSet.as_view(
    {
        "post": "mark_lost",
    }
)

lead_convert = LeadViewSet.as_view(
    {
        "post": "convert",
    }
)

urlpatterns = [
    re_path(r"^leads/?$", lead_list, name="lead-list"),
    re_path(
        r"^leads/(?P<pk>[0-9a-fA-F-]{36})/?$",
        lead_detail,
        name="lead-detail",
    ),
    re_path(
        r"^leads/(?P<pk>[0-9a-fA-F-]{36})/status/?$",
        lead_status,
        name="lead-status",
    ),
    re_path(
        r"^leads/(?P<pk>[0-9a-fA-F-]{36})/mark-lost/?$",
        lead_mark_lost,
        name="lead-mark-lost",
    ),
    re_path(
        r"^leads/(?P<pk>[0-9a-fA-F-]{36})/convert/?$",
        lead_convert,
        name="lead-convert",
    ),
]
