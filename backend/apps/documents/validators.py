from rest_framework import exceptions as drf_exceptions


def require_file_url(file_url: str) -> str:
    """
    Enforce a non-blank Document.file_url when it is the one being
    supplied. Mirrors apps.products.validators.require_category_name's
    shape.
    """
    if not file_url or not file_url.strip():
        raise ValueError("fileUrl cannot be blank or empty.")
    return file_url.strip()


def require_exactly_one_file_source(file_url: str, file_storage_key: str) -> None:
    """
    BE-078: a Document is registered from exactly one source -- either a
    legacy/manual fileUrl string, or a fileStorageKey from a real
    POST /documents/upload call -- never both (ambiguous which one is
    authoritative) and never neither (nothing to attach at all).
    """
    has_url = bool(file_url and file_url.strip())
    has_key = bool(file_storage_key and file_storage_key.strip())
    if has_url and has_key:
        raise drf_exceptions.ValidationError(
            {"fileUrl": ["Provide either fileUrl or fileStorageKey, not both."]}
        )
    if not has_url and not has_key:
        raise drf_exceptions.ValidationError(
            {"fileUrl": ["Either fileUrl or fileStorageKey is required."]}
        )
