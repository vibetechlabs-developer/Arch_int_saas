from apps.common.permissions import TenantScopedPermission

__all__ = ["ProductCategoryPermission"]


class ProductCategoryPermission(TenantScopedPermission):
    """
    Permission class for Product/Category/Subcategory endpoints. As of
    BE-054, logic lives entirely in the shared `TenantScopedPermission` —
    tenant isolation plus the permission code each view's
    `permission_code_map` declares (`product.view`/`product.manage`).
    Kept as a named subclass for import stability and readability.
    """
