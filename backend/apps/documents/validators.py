def require_file_url(file_url: str) -> str:
    """
    Enforce Document.file_url is present and non-blank -- the model's one
    truly required field beyond company/project. Mirrors
    apps.products.validators.require_category_name's shape.
    """
    if not file_url or not file_url.strip():
        raise ValueError("fileUrl cannot be blank or empty.")
    return file_url.strip()
