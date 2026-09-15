from django.urls import re_path

from apps.site_visits.views import SiteVisitViewSet

site_visit_list = SiteVisitViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

site_visit_detail = SiteVisitViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

site_visit_report = SiteVisitViewSet.as_view(
    {
        "post": "submit_report",
    }
)

urlpatterns = [
    re_path(r"^site-visits/?$", site_visit_list, name="site-visit-list"),
    re_path(
        r"^site-visits/(?P<pk>[0-9a-fA-F-]{36})/?$",
        site_visit_detail,
        name="site-visit-detail",
    ),
    re_path(
        r"^site-visits/(?P<pk>[0-9a-fA-F-]{36})/report/?$",
        site_visit_report,
        name="site-visit-report",
    ),
]
