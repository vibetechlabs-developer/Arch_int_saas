from typing import Optional
from rest_framework import permissions
from rest_framework.request import Request


def is_platform_admin(request: Request) -> bool:
    """
    Check if the authenticated user is a Platform Super Admin.
    Checks either Django superuser status or platform_admin JWT token claim.
    Fails closed (returns False) on any missing, malformed, or invalid auth.
    """
    try:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        auth = getattr(request, "auth", None)
        if hasattr(auth, "get"):
            if auth.get("token_type") == "platform_admin":
                return True
        elif isinstance(auth, dict) and auth.get("token_type") == "platform_admin":
            return True

        return False
    except Exception:
        return False


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
