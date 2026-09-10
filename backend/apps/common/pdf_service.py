"""
Shared PDF rendering infrastructure (document export: BOQ/Quotation/
Invoice). Layering: View builds context from already-authorized/already-
fetched model instances and backend-computed totals -> this module turns
an HTML template + that context into PDF bytes -> View wraps the bytes in
an HttpResponse. No financial calculation happens anywhere in this file
or in the templates it renders -- every number in the context must
already be the real, backend-computed value.
"""

import logging
import re
import unicodedata
from io import BytesIO
from typing import Any, Dict

from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa

logger = logging.getLogger("apps.common.pdf_service")


class PdfRenderError(Exception):
    """
    Raised when the PDF rendering engine fails to produce a document.
    Deliberately unregistered in apps.common.exceptions.EXCEPTION_MAP --
    it falls through to that handler's existing catch-all (500
    INTERNAL_ERROR, "An unexpected error occurred..."), which already
    satisfies "return a standard structured error, never an HTML
    traceback, log the real cause server-side only" without needing a
    second error-handling path.
    """


def render_pdf(template_name: str, context: Dict[str, Any]) -> bytes:
    """
    Render `template_name` with `context` to PDF bytes via xhtml2pdf.
    `render_to_string` autoescapes every context value by Django's own
    default template behavior (BE's HTML-safety rule: never mark
    caller-supplied text `|safe`), so user-entered strings (client names,
    notes, item descriptions) can never inject markup into the document.
    """
    html = render_to_string(template_name, context)
    buffer = BytesIO()
    result = pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
    if result.err:
        logger.error(
            "PDF generation failed (template=%s, pisa_err_count=%s)",
            template_name,
            result.err,
        )
        raise PdfRenderError(f"PDF generation failed for template '{template_name}'.")
    return buffer.getvalue()


def sanitize_filename(name: str, fallback: str = "document") -> str:
    """
    Reduce `name` to characters safe for both a filesystem and a
    Content-Disposition header value: transliterates accented characters,
    strips everything but alnum/dot/space/hyphen/underscore, and
    collapses whitespace to single hyphens. Never raises and never
    returns an empty string -- falls back to `fallback` if nothing safe
    remains (e.g. a name that was entirely non-Latin script).
    """
    normalized = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "", normalized).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = cleaned.strip("-_.")
    return cleaned or fallback


def pdf_http_response(pdf_bytes: bytes, filename: str, inline: bool = False) -> HttpResponse:
    """
    Wrap already-rendered PDF bytes in a real `application/pdf` response
    -- never JSON/base64-encoded. `inline` drives Preview vs Download
    (Content-Disposition: inline vs attachment); `filename` is sanitized
    here so no call site can accidentally leak an unsafe or UUID-only name.
    """
    # sanitize_filename already restricts the result to [A-Za-z0-9._ -],
    # so it's already safe to interpolate directly into the header value
    # (no quotes/CRLF/control characters possible) -- no separate HTTP
    # header-escaping step is needed.
    safe_stem = sanitize_filename(filename[:-4] if filename.lower().endswith(".pdf") else filename)
    disposition = "inline" if inline else "attachment"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{safe_stem}.pdf"'
    response["Content-Length"] = str(len(pdf_bytes))
    return response
