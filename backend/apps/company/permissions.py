from rest_framework import permissions
from rest_framework.request import Request

from apps.common.permissions import (
    get_active_membership_for_request,
    is_platform_admin,
    resolve_required_permission_code,
)

__all__ = ["is_platform_admin", "IsPlatformAdmin", "IsPlatformAdminOrCompanyAccess"]


class IsPlatformAdmin(permissions.BasePermission):
    """
    Allows access only to authenticated Platform Super Admins.
    """

    def has_permission(self, request: Request, view) -> bool:
        return is_platform_admin(request)


class IsPlatformAdminOrCompanyAccess(permissions.BasePermission):
    """
    Permission for Company endpoints:
    - Platform Super Admins have full access across all operations.
    - Regular users can only retrieve or update companies where they hold
      active membership, and only with the permission code
      (`company.view`/`company.manage`, per CompanyViewSet's
      `permission_code_map`) their role grants (BE-054).
    - Regular users cannot list all companies or delete companies.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if is_platform_admin(request):
            return True

        # Non-admins can only attempt retrieve (GET detail) or update (PATCH detail)
        # Create (POST), List (GET list), and Delete (DELETE) require Platform Admin
        if view.action not in ["retrieve", "partial_update", "update"]:
            return False

        from apps.users.services import PermissionService

        code = resolve_required_permission_code(request, view)
        if code is None:
            return True

        membership = get_active_membership_for_request(request)
        return PermissionService.has_permission(membership, code)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if is_platform_admin(request):
            return True

        # obj IS the tenant here (Company), so the object-level check is a
        # direct comparison against the single company TenantJWTAuthentication
        # already resolved for this request — never re-derived from
        # request.user.memberships (BE-021: that duplicated, and could
        # diverge from, the authentication layer's own resolution).
        return str(getattr(request, "company_id", None)) == str(obj.id)
