from rest_framework import permissions
from rest_framework.request import Request


def is_platform_admin(request: Request) -> bool:
    """
    Check if the authenticated user is a Platform Super Admin.
    Checks either Django superuser status or platform_admin JWT token claim.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False

    if getattr(user, "is_superuser", False):
        return True

    # Check JWT claims payload if present
    auth = getattr(request, "auth", None)
    if isinstance(auth, dict) and auth.get("token_type") == "platform_admin":
        return True

    return False


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
    - Regular users can only retrieve or update companies where they hold active membership.
    - Regular users cannot list all companies or delete companies.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if is_platform_admin(request):
            return True

        # Non-admins can only attempt retrieve (GET detail) or update (PATCH detail)
        # Create (POST), List (GET list), and Delete (DELETE) require Platform Admin
        if view.action in ["retrieve", "partial_update", "update"]:
            return True

        return False

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if is_platform_admin(request):
            return True

        # Check active company membership for the user
        user = request.user
        return user.memberships.filter(
            company=obj,
            status="active",
            deleted_at__isnull=True,
        ).exists()
