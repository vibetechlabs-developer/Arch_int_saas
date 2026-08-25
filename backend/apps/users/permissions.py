from typing import Optional
from rest_framework import permissions
from rest_framework.request import Request

from apps.common.permissions import is_platform_admin

__all__ = ["is_platform_admin", "has_permission", "RolePermission"]


def has_permission(request: Request, permission_code: str, company_id: Optional[str] = None) -> bool:
    """
    Check if the authenticated request has the specified permission code.
    Platform Super Admins have universal access.
    Company users must have an active membership in the relevant company.
    """
    if not request.user or not request.user.is_authenticated:
        return False

    if is_platform_admin(request):
        return True

    memberships = request.user.memberships.filter(status="active", deleted_at__isnull=True)
    if company_id:
        memberships = memberships.filter(company_id=company_id)

    return memberships.exists()


class RolePermission(permissions.BasePermission):
    """
    Permission class for Role endpoints:
    - Platform Super Admins have full access across all operations.
    - Regular users can manage roles only within companies where they hold active membership.
    - Cross-tenant access is strictly denied.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if is_platform_admin(request):
            return True

        # Regular user must have active membership in at least one company
        return request.user.memberships.filter(
            status="active",
            deleted_at__isnull=True,
        ).exists()

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if is_platform_admin(request):
            return True

        user = request.user
        return user.memberships.filter(
            company_id=obj.company_id,
            status="active",
            deleted_at__isnull=True,
        ).exists()
