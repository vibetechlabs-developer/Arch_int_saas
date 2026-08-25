"""
Test-only support view + URLconf for TenantAuthIntegrationTest.

Exposes the request.company_id / request.is_platform_admin attributes that
TenantJWTAuthentication (apps/authentication/authentication.py) resolves,
so the tenant-resolution matrix can be exercised end-to-end through real URL
routing without shipping a diagnostic endpoint in the production URLconf.
"""

from django.urls import re_path
from rest_framework.views import APIView

from apps.common.responses import ApiResponse


class TenantInfoView(APIView):
    def get(self, request, *args, **kwargs):
        data = {
            "company_id": getattr(request, "company_id", None),
            "is_platform_admin": getattr(request, "is_platform_admin", False),
        }
        return ApiResponse.success(data=data)


urlpatterns = [
    re_path(r"^test/tenant-info/?$", TenantInfoView.as_view(), name="tenant-info"),
]
