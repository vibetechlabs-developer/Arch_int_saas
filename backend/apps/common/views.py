from django.http import Http404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import ApiResponse


class HealthCheckView(APIView):
    """
    Unauthenticated liveness endpoint for container/orchestrator health
    checks (BE-020; 07_DevOps/CI_CD.md §4, Docker.md). Deliberately has no
    dependency on the database, cache, or any other service — a health
    check that can itself fail from an unrelated outage defeats its own
    purpose as a liveness signal.

    `authentication_classes = []` means TenantJWTAuthentication never runs
    for this view at all, regardless of whether the caller supplies a
    Bearer token — a stronger guarantee than adding this path to
    TenantJWTAuthentication's `exempt_paths` list (BE-016's approach for
    /schema//docs//redoc/), and one that can't be broken by a future
    trailing-slash mismatch in that list.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return ApiResponse.success(
            data={"status": "ok"},
            request_id=getattr(request, "request_id", None),
        )


class ObjectPermission404Mixin:
    """
    Returns 404 instead of DRF's default 403 when an object-level permission
    check fails.

    Error_Handling.md §5 (non-negotiable): a request for another tenant's
    resource by ID must return 404, never 403 — a 403 confirms the resource
    exists, which is an information leak about another tenant's data.

    Only affects OBJECT-level checks (has_object_permission, reached after
    an object has already been fetched by ID — e.g. retrieve/partial_update
    on a resource that exists but the caller isn't authorized for). A
    VIEW-level check failure (has_permission, e.g. a non-admin attempting a
    platform-admin-only action like list/create/delete) is unaffected and
    still raises the normal 403, since no specific object's existence is
    being probed there — DRF's check_permissions() runs before this method
    and short-circuits first for those cases.
    """

    def check_object_permissions(self, request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                raise Http404
