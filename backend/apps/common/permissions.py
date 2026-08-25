from rest_framework.request import Request


def is_platform_admin(request: Request) -> bool:
    """
    Check if the authenticated user is a Platform Super Admin.
    Checks either Django superuser status or the platform_admin JWT token_type
    claim set by apps.authentication.authentication.TenantJWTAuthentication.
    Fails closed (returns False) on any missing, malformed, or invalid auth.

    Shared by apps.company.permissions and apps.users.permissions so the
    platform-admin check has exactly one implementation — see BACKEND_TASKS.md
    setup audit (2026-08-25) for the bug this duplication previously caused.
    """
    try:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        auth = getattr(request, "auth", None)
        if hasattr(auth, "get"):
            return auth.get("token_type") == "platform_admin"
        if isinstance(auth, dict):
            return auth.get("token_type") == "platform_admin"

        return False
    except Exception:
        return False
