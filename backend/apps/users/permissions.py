from rest_framework import permissions
from rest_framework.request import Request

from apps.common.permissions import is_platform_admin

__all__ = ["is_platform_admin", "RolePermission"]


class RolePermission(permissions.BasePermission):
    """
    Permission class for Role endpoints:
    - Platform Super Admins have full access across all operations.
    - Regular users can manage roles only within the single company
      TenantJWTAuthentication resolved for this request (request.company_id)
      — never re-derived from request.user.memberships here (BE-021: that
      duplicated, and could diverge from, the authentication layer's own
      resolution).
    - Cross-tenant access is strictly denied.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if is_platform_admin(request):
            return True

        # TenantJWTAuthentication has already rejected any company user with
        # no active membership (or an unresolved ambiguous one) before this
        # ever runs, so a non-admin reaching here is guaranteed to have a
        # resolved request.company_id.
        return getattr(request, "company_id", None) is not None

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if is_platform_admin(request):
            return True

        return str(getattr(request, "company_id", None)) == str(obj.company_id)
