from apps.common.permissions import TenantScopedPermission, is_platform_admin

__all__ = ["is_platform_admin", "RolePermission", "CompanyMembershipPermission"]


class CompanyMembershipPermission(TenantScopedPermission):
    """
    Permission class for Company Membership management endpoints
    (BE-052/BE-054). Logic lives entirely in the shared
    `TenantScopedPermission` — tenant isolation plus the permission code
    `CompanyMembershipViewSet.permission_code_map` declares per action
    (`user.view`/`user.manage`). Kept as a named subclass for import
    stability and readability.
    """


class RolePermission(TenantScopedPermission):
    """
    Permission class for Role endpoints (BE-014/BE-054). Logic lives
    entirely in the shared `TenantScopedPermission` — tenant isolation
    plus the permission code `RoleViewSet.permission_code_map` declares
    per action (`role.view`/`role.manage`). Kept as a named subclass for
    import stability and readability.
    """
