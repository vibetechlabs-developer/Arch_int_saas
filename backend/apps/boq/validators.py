def require_section_name(name: str) -> str:
    """
    Enforce BOQSection.name is present and non-blank. Mirrors
    apps.products.validators.require_category_name.
    """
    if not name or not name.strip():
        raise ValueError("Section name cannot be blank or empty.")
    return name.strip()
