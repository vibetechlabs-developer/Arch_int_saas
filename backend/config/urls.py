"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework.permissions import AllowAny
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.common.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    # BE-020: container/orchestrator liveness endpoint. Unauthenticated
    # (HealthCheckView disables authentication_classes entirely), unprefixed
    # to match every other route in this project.
    path("health/", HealthCheckView.as_view(), name="health-check"),
    # BE-016: OpenAPI schema + interactive docs. Unprefixed, matching every
    # other route in this project (API_Response_Format.md §6 — unversioned
    # by default). Publicly readable (AllowAny) since the schema only
    # describes endpoint shapes, never tenant data.
    path(
        "schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema", permission_classes=[AllowAny]
        ),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(
            url_name="schema", permission_classes=[AllowAny]
        ),
        name="redoc",
    ),
    path("", include("apps.authentication.urls")),
    path("", include("apps.company.urls")),
    path("", include("apps.users.urls")),
    path("", include("apps.clients.urls")),
    path("", include("apps.projects.urls")),
    path("", include("apps.products.urls")),
]
