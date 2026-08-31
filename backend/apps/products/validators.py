def require_category_name(name: str) -> str:
    """
    Enforce ProductCategory.name is present and non-blank — the model's
    only field beyond `company`. Mirrors apps.clients.validators.require_name.
    """
    if not name or not name.strip():
        raise ValueError("Category name cannot be blank or empty.")
    return name.strip()


def require_subcategory_name(name: str) -> str:
    """
    Enforce ProductSubcategory.name is present and non-blank. Mirrors
    require_category_name.
    """
    if not name or not name.strip():
        raise ValueError("Subcategory name cannot be blank or empty.")
    return name.strip()
