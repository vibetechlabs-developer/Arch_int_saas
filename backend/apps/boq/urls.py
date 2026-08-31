from django.urls import re_path

from apps.boq.views import BOQDetailView, BOQSectionListCreateView, BOQSectionViewSet

section_detail = BOQSectionViewSet.as_view(
    {
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

urlpatterns = [
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/boq/?$",
        BOQDetailView.as_view(),
        name="boq-detail",
    ),
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/boq/sections/?$",
        BOQSectionListCreateView.as_view(),
        name="boq-section-list",
    ),
    re_path(
        r"^boq-sections/(?P<pk>[0-9a-fA-F-]{36})/?$",
        section_detail,
        name="boq-section-detail",
    ),
]
