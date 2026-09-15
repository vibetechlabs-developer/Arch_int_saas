from apps.common.permissions import TenantScopedPermission

__all__ = ["LeadPermission"]


class LeadPermission(TenantScopedPermission):
    """
    Permission class for Lead endpoints. Mirrors
    apps.clients.permissions.ClientPermission exactly — logic lives
    entirely in the shared `TenantScopedPermission`; tenant isolation plus
    the permission code each view's `permission_code`/`permission_code_map`
    declares (`lead.view`/`lead.create`/`lead.edit`/`lead.delete`/`lead.convert`).
    """
