from rest_framework import permissions
from rest_framework.request import Request

from apps.common.permissions import is_platform_admin

__all__ = ["ClientPermission"]


class ClientPermission(permissions.BasePermission):
    """
    Permission class for Client endpoints. Mirrors
    apps.users.permissions.RolePermission exactly — a coarse
    tenant-membership gate, not fine-grained per-action permission codes
    (client.view/create/edit/delete). Building the latter would require a
    Permission/RolePermission model that doesn't exist yet (see
    05_Security/Permissions.md §7 "Open Items" — the canonical permission
    code list is still pending client sign-off). Per Backend Lead decision
    (2026-08-27), Client authorization stays at this same coarse level
    until a dedicated RBAC task builds fine-grained codes for every module.

    - Platform Super Admins have full access across all operations.
    - Regular users can manage clients only within the single company
      TenantJWTAuthentication resolved for this request (request.company_id)
      — never re-derived from request.user.memberships.
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
