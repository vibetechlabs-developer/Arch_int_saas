from apps.common.storage import validate_image_upload


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


def require_product_name(name: str) -> str:
    """
    Enforce Product.name is present and non-blank. Mirrors
    require_category_name/require_subcategory_name.
    """
    if not name or not name.strip():
        raise ValueError("Product name cannot be blank or empty.")
    return name.strip()


# --- Product image upload -------------------------------------------------

def validate_product_image(uploaded_file) -> tuple[str, str]:
    """
    Validate an uploaded product image by its actual decoded content —
    never by filename extension or the browser-supplied Content-Type
    header, both of which are trivially spoofable. Returns
    (file_extension, content_type) on success; raises DRF ValidationError
    (-> standard VALIDATION_ERROR/400 envelope) otherwise.

    BE-078: delegates to the shared `apps.common.storage.validate_image_upload`
    (identical JPEG/PNG/WEBP/5MB rules this function originally implemented
    standalone, BE-036) — kept as a thin wrapper so existing imports of
    `apps.products.validators.validate_product_image` keep working
    unchanged, now that Company logos share the same validation logic.
    """
    return validate_image_upload(uploaded_file)
