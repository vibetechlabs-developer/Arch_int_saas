from apps.common.permissions import TenantScopedPermission

__all__ = ["ClientPermission"]


class ClientPermission(TenantScopedPermission):
    """
    Permission class for Client endpoints. As of BE-054, logic lives
    entirely in the shared `TenantScopedPermission` — tenant isolation
    plus the permission code `ClientViewSet.permission_code_map` declares
    per action (`client.view`/`client.create`/`client.edit`/`client.delete`).
    Kept as a named subclass (rather than importing TenantScopedPermission
    directly into views.py) purely for import stability and readability.
    """
