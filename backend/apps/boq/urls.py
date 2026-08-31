from django.urls import re_path

from apps.boq.views import (
    BOQDetailView,
    BOQItemListCreateView,
    BOQItemViewSet,
    BOQSectionListCreateView,
    BOQSectionViewSet,
    BOQSummaryView,
)

section_detail = BOQSectionViewSet.as_view(
    {
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

item_detail = BOQItemViewSet.as_view(
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
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/boq/summary/?$",
        BOQSummaryView.as_view(),
        name="boq-summary",
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
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/boq/sections/(?P<section_id>[0-9a-fA-F-]{36})/items/?$",
        BOQItemListCreateView.as_view(),
        name="boq-item-list",
    ),
    re_path(
        r"^boq-items/(?P<pk>[0-9a-fA-F-]{36})/?$",
        item_detail,
        name="boq-item-detail",
    ),
]
