from django.urls import re_path

from apps.company.views import CompanyViewSet

company_list = CompanyViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

company_detail = CompanyViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

urlpatterns = [
    re_path(r"^companies/?$", company_list, name="company-list"),
    re_path(
        r"^companies/(?P<pk>[0-9a-fA-F-]{36})/?$",
        company_detail,
        name="company-detail",
    ),
]
