from rest_framework import permissions
from rest_framework.request import Request

_MISSING_CODE = object()


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


def get_active_membership_for_request(request: Request):
    """
    Resolve the caller's own active CompanyMembership within
    `request.company_id` (BE-054). Memoized on the request object so
    repeated permission checks within one request don't re-query — DRF
    calls `has_permission` once per configured permission class, and this
    codebase's views only ever declare one, so in practice this runs at
    most once per request today; memoization is defensive, not covering a
    known N+1.

    Returns None for a platform admin (no company membership exists to
    resolve), for an unauthenticated caller, or when no active membership
    matches — every caller must treat None as "no permission codes",
    never as an error.
    """
    sentinel = "__unresolved__"
    cached = getattr(request, "_rbac_membership_cache", sentinel)
    if cached != sentinel:
        return cached

    membership = None
    company_id = getattr(request, "company_id", None)
    user = getattr(request, "user", None)

    if company_id and user is not None and getattr(user, "is_authenticated", False):
        from apps.users.models import CompanyMembership, CompanyMembershipStatus

        membership = (
            CompanyMembership.objects.select_related("role")
            .filter(user_id=user.id, company_id=company_id, status=CompanyMembershipStatus.ACTIVE)
            .first()
        )

    request._rbac_membership_cache = membership
    return membership


def resolve_required_permission_code(request: Request, view):
    """
    Resolve the permission code a view requires for the current
    action/method (BE-054), from declarative view attributes rather than
    an if/else chain per endpoint:

    - `view.permission_code_exempt = True` — deliberately open to any
      authenticated, tenant-resolved caller beyond that point (e.g. the
      global `GET /permissions` catalog). Returns None (no code required).
    - `view.permission_code` — a single code covering every action this
      view handles (typical for a single-HTTP-method APIView).
    - `view.permission_code_map` — a `{action_or_method: code}` dict for a
      view handling more than one action. Keyed by `view.action` for a
      ViewSet (set by DRF's `ViewSetMixin` from the `.as_view({...})`
      method mapping, including custom `@action` names), or by
      `request.method.lower()` for a plain multi-method APIView (which has
      no `.action`).

    Returns `_MISSING_CODE` when none of the above resolve a code — this
    is deliberately distinct from "no code required" (`None`): a view that
    reaches TenantScopedPermission without declaring any of the above is
    treated as a configuration gap and fails closed, not as an
    accidentally-open endpoint.
    """
    if getattr(view, "permission_code_exempt", False):
        return None

    single_code = getattr(view, "permission_code", None)
    if single_code:
        return single_code

    code_map = getattr(view, "permission_code_map", None)
    if code_map:
        key = getattr(view, "action", None) or request.method.lower()
        return code_map.get(key, _MISSING_CODE)

    return _MISSING_CODE


class TenantScopedPermission(permissions.BasePermission):
    """
    The one shared permission mechanism for every tenant-owned business
    resource (BE-054). Replaces the byte-for-byte-identical tenant-only
    permission classes that used to be duplicated per app
    (ClientPermission, ProjectPermission, ProductCategoryPermission,
    RolePermission, CompanyMembershipPermission each defined the same
    `has_permission`/`has_object_permission` bodies independently) — those
    names are kept as thin subclasses for import stability, but the logic
    now lives here exactly once.

    - `has_permission`: authenticated + platform-admin bypass (unchanged
      from before BE-054) + tenant resolved, **plus** the caller's active
      CompanyMembership must hold the permission code
      `resolve_required_permission_code` resolves for this view/action.
      Fails closed: no membership, no role, an inactive role, a
      soft-deleted grant, or an unresolved/missing code declaration all
      deny access (`PermissionService.has_permission` returns False for
      every one of these).
    - `has_object_permission`: unchanged from before BE-054 — platform
      admin bypass, else the caller's `company_id` must match the
      object's. This stays a *pure tenant* check, deliberately not
      re-checking the permission code, so cross-tenant access keeps
      404ing via `ObjectPermission404Mixin` (anti-enumeration) while a
      same-tenant-but-wrong-permission caller gets an ordinary 403 from
      `has_permission` instead — the two failure modes must stay visibly
      different, not collapsed into one.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if is_platform_admin(request):
            return True

        if getattr(request, "company_id", None) is None:
            return False

        from apps.users.services import PermissionService

        code = resolve_required_permission_code(request, view)
        if code is None:
            return True
        if code is _MISSING_CODE:
            return False

        membership = get_active_membership_for_request(request)
        return PermissionService.has_permission(membership, code)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if is_platform_admin(request):
            return True

        return str(getattr(request, "company_id", None)) == str(obj.company_id)
