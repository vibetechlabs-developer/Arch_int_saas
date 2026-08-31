from rest_framework import permissions
from rest_framework.request import Request

from apps.common.permissions import is_platform_admin

__all__ = ["ProjectPermission"]


class ProjectPermission(permissions.BasePermission):
    """
    Permission class for Project endpoints. Mirrors
    apps.clients.permissions.ClientPermission exactly — the same coarse
    tenant-membership gate, not fine-grained project.* permission codes
    (same standing Backend Lead decision applied to Client/Role).

    - Platform Super Admins have full access across all operations.
    - Regular users can manage projects only within the single company
      TenantJWTAuthentication resolved for this request (request.company_id).
    - Cross-tenant access is strictly denied.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if is_platform_admin(request):
            return True

        return getattr(request, "company_id", None) is not None

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if is_platform_admin(request):
            return True

        return str(getattr(request, "company_id", None)) == str(obj.company_id)
