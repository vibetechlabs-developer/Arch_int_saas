from PIL import Image, UnidentifiedImageError
from rest_framework import exceptions as drf_exceptions


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

#: 5 MB — no existing project convention for an upload size limit (this is
#: the first file upload anywhere in the backend), chosen as a reasonable
#: ceiling for a catalog thumbnail/photo rather than a magic number
#: scattered inline.
MAX_PRODUCT_IMAGE_SIZE_BYTES = 5 * 1024 * 1024

#: Pillow format name -> (storage file extension, IANA content type).
#: JPEG/PNG/WEBP only, per the brief — SVG is deliberately excluded (an SVG
#: can carry embedded <script>, so admitting it would need dedicated
#: sanitization this task doesn't scope in).
ALLOWED_PRODUCT_IMAGE_FORMATS: dict[str, tuple[str, str]] = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


def validate_product_image(uploaded_file) -> tuple[str, str]:
    """
    Validate an uploaded product image by its actual decoded content —
    never by filename extension or the browser-supplied Content-Type
    header, both of which are trivially spoofable. Returns
    (file_extension, content_type) on success; raises DRF ValidationError
    (-> standard VALIDATION_ERROR/400 envelope) otherwise.
    """
    if uploaded_file is None:
        raise drf_exceptions.ValidationError({"image": ["An image file is required."]})

    if uploaded_file.size > MAX_PRODUCT_IMAGE_SIZE_BYTES:
        raise drf_exceptions.ValidationError({"image": ["Image must be smaller than 5 MB."]})

    if uploaded_file.size == 0:
        raise drf_exceptions.ValidationError({"image": ["The uploaded file is empty."]})

    try:
        with Image.open(uploaded_file) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise drf_exceptions.ValidationError({"image": ["The uploaded file is not a valid image."]})

    # Image.verify() leaves the file object unusable for further decoding —
    # re-open a fresh handle on the same (seeked-back) stream to read the
    # format, matching Pillow's own documented verify() usage pattern.
    uploaded_file.seek(0)
    try:
        with Image.open(uploaded_file) as decoded:
            image_format = decoded.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise drf_exceptions.ValidationError({"image": ["The uploaded file is not a valid image."]})

    if image_format not in ALLOWED_PRODUCT_IMAGE_FORMATS:
        raise drf_exceptions.ValidationError(
            {"image": ["Only JPEG, PNG, and WEBP images are supported."]}
        )

    uploaded_file.seek(0)
    return ALLOWED_PRODUCT_IMAGE_FORMATS[image_format]
