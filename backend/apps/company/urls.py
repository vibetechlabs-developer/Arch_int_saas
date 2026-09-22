from django.urls import re_path

from apps.company.views import CompanyLogoUploadView, CompanyViewSet

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

company_owner_set_password = CompanyViewSet.as_view({"post": "set_owner_password"})

urlpatterns = [
    re_path(r"^companies/?$", company_list, name="company-list"),
    re_path(
        r"^companies/(?P<pk>[0-9a-fA-F-]{36})/?$",
        company_detail,
        name="company-detail",
    ),
    re_path(
        r"^companies/(?P<pk>[0-9a-fA-F-]{36})/logo/upload/?$",
        CompanyLogoUploadView.as_view(),
        name="company-logo-upload",
    ),
    re_path(
        r"^companies/(?P<pk>[0-9a-fA-F-]{36})/owner/set-password/?$",
        company_owner_set_password,
        name="company-owner-set-password",
    ),
]
