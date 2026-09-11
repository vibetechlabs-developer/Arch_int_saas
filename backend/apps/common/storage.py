"""
Shared file-storage abstraction (BE-078). Business apps call into this
module rather than touching `django.core.files.storage`/boto3 directly, so
the storage backend (local `FileSystemStorage` in development,
S3-compatible object storage in production, selected via `STORAGE_BACKEND`
in `config/settings.py`) stays swappable purely via settings +
environment configuration, with no business-logic change anywhere that
calls in here.

Every uploaded file is classified PUBLIC or PRIVATE at the call site via
`scope`, matching the "classify every file type" requirement:

- PUBLIC scopes (`products`, `companies` -- product images, company logos)
  resolve through the `"default"` storage alias: publicly readable,
  permanent absolute URL, persisted directly into a `URLField`. This is
  exactly how `Product.imageUrl` has always worked (`ProductImageService`,
  pre-BE-078) -- unchanged behavior, just moved to shared infrastructure.

- PRIVATE scopes (`documents`, `expenses`, `payments` -- project documents,
  expense receipts, payment receipts) resolve through the `"private"`
  storage alias, which is never publicly reachable: in local development
  it is a plain filesystem directory *outside* `MEDIA_ROOT` (so nginx's
  `/media/` alias can never accidentally serve it -- no `base_url` is
  configured for it at all, so calling `.url()` against it raises); in S3
  production mode it is a private-ACL bucket path only ever resolved to a
  short-lived signed URL, generated on demand and never persisted to the
  database. Callers for these scopes store the storage *key* on their own
  model (e.g. `Document.file_storage_key`), never a URL, and only ever
  resolve a live URL from inside an already tenant/RBAC-checked proxy view
  immediately before using it -- see `apps.documents.views.DocumentDownloadView`
  and its Expense/Payment receipt equivalents.
"""

import mimetypes
import os
import uuid
from typing import Optional, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.http import FileResponse, HttpResponseRedirect
from PIL import Image, UnidentifiedImageError
from rest_framework import exceptions as drf_exceptions

PUBLIC_SCOPES = frozenset({"products", "companies"})
PRIVATE_SCOPES = frozenset({"documents", "expenses", "payments"})

#: 5 MB -- matches the pre-existing Product image limit (BE-036) exactly;
#: reused unchanged for Company logos, the other PUBLIC image scope.
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024

#: Pillow format name -> (storage file extension, IANA content type).
#: JPEG/PNG/WEBP only -- SVG is deliberately excluded everywhere in this
#: codebase (an SVG can carry embedded <script>, and admitting it would
#: need dedicated sanitization no upload surface here scopes in).
ALLOWED_IMAGE_FORMATS: dict = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}

#: 20 MB -- matches nginx's own `client_max_body_size 20M` (backend/nginx/
#: nginx.conf) exactly, so a document/receipt this size is never silently
#: rejected by the proxy in front of a request that Django itself would
#: have accepted.
MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024


def _storage_for_scope(scope: str):
    if scope in PRIVATE_SCOPES:
        return storages["private"]
    if scope in PUBLIC_SCOPES:
        return storages["default"]
    raise ValueError(f"Unknown storage scope: {scope!r}")


def generate_storage_key(scope: str, company_id, extension: str) -> str:
    """
    UUID-based, tenant-namespaced storage key -- never the caller's raw
    filename (collision risk, and a real path-traversal vector if a
    filename like "../../etc/passwd.jpg" were ever used directly), never
    predictable/overwritable. Matches the key scheme
    `ProductImageService.upload_image` originally established
    (`products/{company_id}/{uuid}.{ext}`), generalized across scopes.
    """
    return f"{scope}/{company_id}/{uuid.uuid4()}.{extension}"


def save_upload(scope: str, storage_key: str, uploaded_file) -> str:
    """
    Persists an already-validated uploaded file under `storage_key` and
    returns the actual saved path (equal to `storage_key` unless the
    backend needed to deduplicate -- it never should, since the key is
    already a fresh UUID). Reads the file fully into memory via
    `ContentFile` -- matches the pre-existing Product image behavior;
    uploads are capped at `MAX_DOCUMENT_SIZE_BYTES` (20 MB) so this never
    approaches a problematic memory footprint.
    """
    storage = _storage_for_scope(scope)
    uploaded_file.seek(0)
    return storage.save(storage_key, ContentFile(uploaded_file.read()))


def delete_file(scope: str, storage_key: str) -> None:
    """
    Best-effort delete -- a blank/`None` key (never uploaded through this
    module, e.g. a legacy manually-entered URL) is a deliberate no-op, and
    any backend error is swallowed rather than propagated: deleting a
    superseded blob is cleanup, not a operation whose failure should ever
    fail the request that triggered it (a Product save that already
    committed successfully, for instance).
    """
    if not storage_key:
        return
    storage = _storage_for_scope(scope)
    try:
        storage.delete(storage_key)
    except Exception:
        pass


def public_url(scope: str, storage_key: str, request=None) -> str:
    """
    PUBLIC scopes only -- a permanent, absolute URL suitable for direct
    `<img>` use and for persisting directly in a `URLField`
    (`Product.imageUrl`, `Company.logoUrl`), matching the pre-existing
    contract exactly. Resolves a request-relative path
    (`storage.url()` for local `FileSystemStorage` returns one rooted at
    `MEDIA_URL`) to an absolute URL when a `request` is supplied; an S3
    backend's `.url()` is already absolute, so it passes through
    unchanged.
    """
    if scope not in PUBLIC_SCOPES:
        raise ValueError(f"public_url() called for a non-public scope: {scope!r}")
    storage = _storage_for_scope(scope)
    relative_url = storage.url(storage_key)
    if request is not None and relative_url.startswith("/"):
        return request.build_absolute_uri(relative_url)
    return relative_url


def private_signed_url(scope: str, storage_key: str) -> str:
    """
    PRIVATE scopes only -- called only from inside an already
    tenant/RBAC-checked proxy view (`DocumentDownloadView` and
    equivalents), immediately before redirecting the client to it. Never
    persisted to a model field -- generated fresh on every access, so it
    naturally expires along with whatever `querystring_expire` the
    production S3 backend is configured with, and a stale/leaked link
    stops working on its own.
    """
    if scope not in PRIVATE_SCOPES:
        raise ValueError(f"private_signed_url() called for a non-private scope: {scope!r}")
    storage = _storage_for_scope(scope)
    return storage.url(storage_key)


def open_private_file(scope: str, storage_key: str):
    """
    PRIVATE scopes, used by the proxy view when the active backend has no
    safe redirect target (local `FileSystemStorage`, which has no
    `base_url` configured for the `"private"` alias -- see module
    docstring) -- streams the file's bytes directly through the Django
    app server instead via `FileResponse`.
    """
    if scope not in PRIVATE_SCOPES:
        raise ValueError(f"open_private_file() called for a non-private scope: {scope!r}")
    storage = _storage_for_scope(scope)
    return storage.open(storage_key, "rb")


def read_public_file_bytes(scope: str, storage_key: str) -> bytes:
    """
    PUBLIC scopes only -- reads a file's bytes directly from storage,
    never via HTTP. Used for server-side embedding (a company logo
    inlined as a base64 data URI in a PDF export, `pdf_service.
    company_logo_data_uri`) where fetching the company's own `logoUrl`
    over HTTP would be an unnecessary network round-trip the PDF
    renderer would make on the caller's behalf -- and an unsafe one if
    that URL were ever manually entered rather than uploaded through
    this app's own endpoint, since it could then point anywhere,
    including an internal address (SSRF). Callers must only use this
    when they already hold a `*_storage_key` this app itself wrote --
    never derived from an arbitrary URL.
    """
    if scope not in PUBLIC_SCOPES:
        raise ValueError(f"read_public_file_bytes() called for a non-public scope: {scope!r}")
    storage = _storage_for_scope(scope)
    with storage.open(storage_key, "rb") as f:
        return f.read()


def private_file_exists(scope: str, storage_key: str) -> bool:
    storage = _storage_for_scope(scope)
    return bool(storage_key) and storage.exists(storage_key)


def private_file_response(scope: str, storage_key: str, download_filename: str):
    """
    Returns an `HttpResponse` for an already-authorized request to read a
    PRIVATE-scope file -- callers (`DocumentDownloadView` and its Expense/
    Payment receipt equivalents) must already have performed their own
    tenant/RBAC check (`check_object_permissions`) before calling this.

    On the S3 backend, redirects (302) to a freshly-generated signed URL
    rather than proxying file bytes through the Django app server --
    avoids tying up a Gunicorn worker on I/O for a large file and lets S3
    serve it directly. On local `FileSystemStorage`, there is no safe
    redirect target (the "private" alias has no `base_url` at all, by
    design -- see module docstring), so this streams the file directly via
    `FileResponse` instead.
    """
    if settings.STORAGE_BACKEND == "s3":
        return HttpResponseRedirect(private_signed_url(scope, storage_key))

    file_handle = open_private_file(scope, storage_key)
    content_type, _ = mimetypes.guess_type(download_filename)
    return FileResponse(
        file_handle,
        as_attachment=False,
        filename=download_filename,
        content_type=content_type or "application/octet-stream",
    )


def safe_display_filename(original_name: str) -> str:
    """
    Cosmetic only -- never used as a storage key or filesystem path. Strips
    directory components (defends against a client sending a
    path-traversal-shaped `name`, e.g. "../../etc/passwd.jpg") and
    truncates to a sane display length.
    """
    return os.path.basename(original_name or "file")[:255]


def validate_image_upload(uploaded_file) -> Tuple[str, str]:
    """
    Validate an uploaded image by its actual decoded content -- never by
    filename extension or the browser-supplied Content-Type header, both
    trivially spoofable. Returns (file_extension, content_type) on
    success; raises DRF ValidationError (-> standard 400 envelope)
    otherwise. Shared by Product images and Company logos -- the same
    validation `apps.products.validators.validate_product_image`
    originally implemented standalone (BE-036), generalized here so it
    isn't duplicated for the second PUBLIC image scope.
    """
    if uploaded_file is None:
        raise drf_exceptions.ValidationError({"image": ["An image file is required."]})

    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        raise drf_exceptions.ValidationError({"image": ["Image must be smaller than 5 MB."]})

    if uploaded_file.size == 0:
        raise drf_exceptions.ValidationError({"image": ["The uploaded file is empty."]})

    try:
        with Image.open(uploaded_file) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise drf_exceptions.ValidationError({"image": ["The uploaded file is not a valid image."]})

    # Image.verify() leaves the file object unusable for further decoding --
    # re-open a fresh handle on the same (seeked-back) stream to read the
    # format, matching Pillow's own documented verify() usage pattern.
    uploaded_file.seek(0)
    try:
        with Image.open(uploaded_file) as decoded:
            image_format = decoded.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise drf_exceptions.ValidationError({"image": ["The uploaded file is not a valid image."]})

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise drf_exceptions.ValidationError(
            {"image": ["Only JPEG, PNG, and WEBP images are supported."]}
        )

    uploaded_file.seek(0)
    return ALLOWED_IMAGE_FORMATS[image_format]


def validate_document_upload(uploaded_file) -> Tuple[str, str]:
    """
    Validate an uploaded document/receipt by actual content -- never
    filename/Content-Type. Accepts PDF (real magic-byte signature check,
    `%PDF-`) or JPEG/PNG/WEBP (Pillow-decoded, same as
    `validate_image_upload`). Rejects everything else outright, including
    HTML/JS/executables/archives even when mislabeled with a PDF or image
    extension. Returns (file_extension, content_type) on success; raises
    DRF ValidationError otherwise.
    """
    if uploaded_file is None:
        raise drf_exceptions.ValidationError({"file": ["A file is required."]})

    if uploaded_file.size > MAX_DOCUMENT_SIZE_BYTES:
        raise drf_exceptions.ValidationError({"file": ["File must be smaller than 20 MB."]})

    if uploaded_file.size == 0:
        raise drf_exceptions.ValidationError({"file": ["The uploaded file is empty."]})

    uploaded_file.seek(0)
    header = uploaded_file.read(5)
    uploaded_file.seek(0)
    if header == b"%PDF-":
        return "pdf", "application/pdf"

    try:
        with Image.open(uploaded_file) as probe:
            probe.verify()
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as decoded:
            image_format = decoded.format
    except (UnidentifiedImageError, OSError, ValueError):
        raise drf_exceptions.ValidationError(
            {"file": ["Only PDF, JPEG, PNG, or WEBP files are supported."]}
        )
    finally:
        uploaded_file.seek(0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise drf_exceptions.ValidationError(
            {"file": ["Only PDF, JPEG, PNG, or WEBP files are supported."]}
        )

    uploaded_file.seek(0)
    return ALLOWED_IMAGE_FORMATS[image_format]
