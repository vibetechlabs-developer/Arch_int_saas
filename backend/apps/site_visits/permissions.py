from apps.common.permissions import TenantScopedPermission

__all__ = ["SiteVisitPermission"]


class SiteVisitPermission(TenantScopedPermission):
    """
    Permission class for Site Visit endpoints. Mirrors
    apps.leads.permissions.LeadPermission exactly — logic lives entirely
    in the shared `TenantScopedPermission`; tenant isolation plus the
    permission code each view's `permission_code`/`permission_code_map`
    declares (`site_visit.view`/`site_visit.create`/`site_visit.edit`/
    `site_visit.delete`).
    """
