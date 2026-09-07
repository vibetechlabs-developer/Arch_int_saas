from apps.common.permissions import TenantScopedPermission

__all__ = ["ProjectPermission"]


class ProjectPermission(TenantScopedPermission):
    """
    Permission class for Project endpoints — also reused directly (import
    from this module) by every nested-under-Project resource in this
    codebase: apps.boq, apps.quotations, apps.invoices, apps.payments,
    apps.expenses, apps.documents, apps.reports, apps.dashboard,
    apps.audit. As of BE-054, logic lives entirely in the shared
    `TenantScopedPermission` — tenant isolation plus the permission code
    each view's `permission_code`/`permission_code_map` declares. Kept as
    a named subclass for import stability and readability, since so many
    other apps import this exact name.
    """
