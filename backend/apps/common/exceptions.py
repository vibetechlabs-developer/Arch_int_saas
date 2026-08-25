"""
BE-006 – Global Exception Handler
Centralizes all DRF/Django/domain exception handling into a single
custom_exception_handler that enforces the project's standard error envelope
via ApiResponse.error() and propagates request.request_id from BE-005.

Error_Handling.md §3: errors are handled in exactly one place.
API_Response_Format.md §2: every error uses the standard envelope.
Logging_Standards.md §6: 5xx always logged with full stack trace server-side.
"""

import logging
from typing import Any

import django.core.exceptions as django_exceptions
from django.http import Http404, JsonResponse
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.middleware import generate_request_id
from apps.common.responses import ApiResponse

logger = logging.getLogger("apps.common.exceptions")


# ---------------------------------------------------------------------------
# Minimal reusable common exception classes for BE-006
# ---------------------------------------------------------------------------

class ConflictError(drf_exceptions.APIException):
    """
    Raised when a request conflicts with the current state of a resource (HTTP 409).
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflict occurred with the current state of the resource."
    default_code = "CONFLICT"

    def __init__(self, detail: str | None = None, code: str | None = None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.code = code
        super().__init__(detail=detail, code=code)


class BusinessRuleError(drf_exceptions.APIException):
    """
    Raised when a request violates domain or business logic (HTTP 422).
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The request could not be processed due to a business rule violation."
    default_code = "BUSINESS_RULE_ERROR"

    def __init__(self, detail: str | None = None, code: str | None = None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.code = code
        super().__init__(detail=detail, code=code)


class ExternalServiceError(drf_exceptions.APIException):
    """
    Raised when an upstream / third-party service fails (HTTP 502 Bad Gateway by default).
    """
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "An external service error occurred. Please try again later."
    default_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        if status_code is not None:
            self.status_code = status_code
        self.code = code
        super().__init__(detail=detail, code=code)


class ExternalServiceUnavailable(ExternalServiceError):
    """
    Raised when an upstream / third-party service is unavailable (HTTP 503).
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The service is temporarily unavailable. Please try again later."


# Aliases for flexibility and consistency
ConflictException = ConflictError
BusinessRuleException = BusinessRuleError
ExternalServiceException = ExternalServiceError
ExternalServiceBadGateway = ExternalServiceError


# ---------------------------------------------------------------------------
# Exception → (HTTP status, error code, client-safe message) mapping
# ---------------------------------------------------------------------------

#: Keyed by exception class. Value is (http_status, code, message).
#: Checked via isinstance so subclasses resolve to their closest registered parent.
EXCEPTION_MAP: dict[type, tuple[int, str, str]] = {
    # --- 400 Bad Request -------------------------------------------------------
    drf_exceptions.ValidationError: (
        status.HTTP_400_BAD_REQUEST,
        "VALIDATION_ERROR",
        "Request validation failed.",
    ),
    django_exceptions.ValidationError: (
        status.HTTP_400_BAD_REQUEST,
        "VALIDATION_ERROR",
        "Request validation failed.",
    ),
    drf_exceptions.ParseError: (
        status.HTTP_400_BAD_REQUEST,
        "PARSE_ERROR",
        "Malformed request body.",
    ),
    # --- 401 Unauthorized ------------------------------------------------------
    drf_exceptions.NotAuthenticated: (
        status.HTTP_401_UNAUTHORIZED,
        "AUTHENTICATION_ERROR",
        "Authentication credentials were not provided.",
    ),
    drf_exceptions.AuthenticationFailed: (
        status.HTTP_401_UNAUTHORIZED,
        "AUTHENTICATION_ERROR",
        "Invalid or expired authentication credentials.",
    ),
    # --- 403 Forbidden ---------------------------------------------------------
    # Code kept identical to django_exceptions.PermissionDenied below —
    # 00_Development_Standards/Error_Handling.md defines one PermissionError
    # category for 403s regardless of which layer raised it.
    drf_exceptions.PermissionDenied: (
        status.HTTP_403_FORBIDDEN,
        "PERMISSION_ERROR",
        "You do not have permission to perform this action.",
    ),
    django_exceptions.PermissionDenied: (
        status.HTTP_403_FORBIDDEN,
        "PERMISSION_ERROR",
        "You do not have permission to perform this action.",
    ),
    # --- 404 Not Found ---------------------------------------------------------
    drf_exceptions.NotFound: (
        status.HTTP_404_NOT_FOUND,
        "NOT_FOUND",
        "The requested resource was not found.",
    ),
    Http404: (
        status.HTTP_404_NOT_FOUND,
        "NOT_FOUND",
        "The requested resource was not found.",
    ),
    # --- 405 Method Not Allowed ------------------------------------------------
    drf_exceptions.MethodNotAllowed: (
        status.HTTP_405_METHOD_NOT_ALLOWED,
        "METHOD_NOT_ALLOWED",
        "Method not allowed.",
    ),
    # --- 406 Not Acceptable ----------------------------------------------------
    drf_exceptions.NotAcceptable: (
        status.HTTP_406_NOT_ACCEPTABLE,
        "NOT_ACCEPTABLE",
        "Could not satisfy the request Accept header.",
    ),
    # --- 409 Conflict ----------------------------------------------------------
    ConflictError: (
        status.HTTP_409_CONFLICT,
        "CONFLICT",
        "A conflict occurred with the current state of the resource.",
    ),
    # --- 415 Unsupported Media Type --------------------------------------------
    drf_exceptions.UnsupportedMediaType: (
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "UNSUPPORTED_MEDIA_TYPE",
        "Unsupported media type.",
    ),
    # --- 422 Unprocessable Entity (Business Rule Violation) -------------------
    BusinessRuleError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "BUSINESS_RULE_ERROR",
        "The request could not be processed due to a business rule violation.",
    ),
    # --- 429 Too Many Requests -------------------------------------------------
    drf_exceptions.Throttled: (
        status.HTTP_429_TOO_MANY_REQUESTS,
        "RATE_LIMIT_EXCEEDED",
        "Too many requests. Please try again later.",
    ),
    # --- 502 Bad Gateway / 503 Service Unavailable -----------------------------
    ExternalServiceUnavailable: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "EXTERNAL_SERVICE_ERROR",
        "The service is temporarily unavailable. Please try again later.",
    ),
    ExternalServiceError: (
        status.HTTP_502_BAD_GATEWAY,
        "EXTERNAL_SERVICE_ERROR",
        "An external service error occurred. Please try again later.",
    ),
}


# ---------------------------------------------------------------------------
# Validation error detail flattener
# ---------------------------------------------------------------------------

def flatten_validation_errors(
    detail: Any,
    prefix: str = "",
) -> list[dict[str, str]]:
    """
    Recursively flatten a DRF or Django ValidationError detail structure into
    the standard ``[{"field": "...", "issue": "..."}]`` list.

    Handles:
    - dict of lists (standard DRF field errors)
    - "non_field_errors" key → field "__all__"
    - nested dicts (dot-notation prefix)
    - plain list (non-field errors)
    - plain string (single-message error)
    - Django ValidationError instances
    """
    result: list[dict[str, str]] = []

    if isinstance(detail, dict):
        for field, errors in detail.items():
            full_field = f"{prefix}.{field}" if prefix else field
            # Normalize DRF's "non_field_errors" to "__all__"
            if field == "non_field_errors":
                full_field = "__all__"
            result.extend(flatten_validation_errors(errors, prefix=full_field))

    elif isinstance(detail, (list, tuple)):
        for item in detail:
            if isinstance(item, (dict, list, tuple)):
                result.extend(flatten_validation_errors(item, prefix=prefix))
            else:
                field = prefix if prefix else "__all__"
                result.append({"field": field, "issue": str(item)})

    elif isinstance(detail, django_exceptions.ValidationError):
        # Django (non-DRF) ValidationError wraps messages differently
        messages = detail.messages if hasattr(detail, "messages") else [str(detail)]
        field = prefix if prefix else "__all__"
        for msg in messages:
            result.append({"field": field, "issue": str(msg)})

    else:
        # Plain string or ErrorDetail
        field = prefix if prefix else "__all__"
        result.append({"field": field, "issue": str(detail)})

    return result


# ---------------------------------------------------------------------------
# Internal detail extractor — handles both DRF and Django ValidationError
# ---------------------------------------------------------------------------

def _extract_validation_details(exc: Exception) -> list[dict[str, str]]:
    """
    Extract and flatten validation error details from either a DRF or Django
    ValidationError, returning the standard ``[{"field", "issue"}]`` list.

    - DRF ValidationError stores errors in ``.detail`` (dict, list, or ErrorDetail)
    - Django ValidationError stores errors in ``.message_dict`` (field→list) or
      ``.messages`` (flat list of strings)
    """
    # DRF ValidationError
    drf_detail = getattr(exc, "detail", None)
    if drf_detail is not None:
        return flatten_validation_errors(drf_detail)

    # Django ValidationError — try field-keyed dict first
    message_dict = getattr(exc, "message_dict", None)
    if message_dict is not None:
        return flatten_validation_errors(message_dict)

    # Django ValidationError — flat messages list
    messages = getattr(exc, "messages", None)
    if messages is not None:
        return [{"field": "__all__", "issue": str(m)} for m in messages]

    # Last resort: use str(exc)
    return [{"field": "__all__", "issue": str(exc)}]


def _classify_exception(
    exc: Exception,
) -> tuple[int, str, str, list[dict[str, str]]]:
    """
    Return (http_status, error_code, client_message, details) for *exc*.

    Resolution order:
    1. Exact class match in EXCEPTION_MAP
    2. isinstance walk through EXCEPTION_MAP (catches registered subclasses)
    3. Generic APIException fallback (preserves status_code, returns safe code/message)
    4. Catch-all → 500 INTERNAL_ERROR
    """
    # 1. Exact match
    exc_type = type(exc)
    if exc_type in EXCEPTION_MAP:
        http_status, code, default_message = EXCEPTION_MAP[exc_type]
        details: list[dict[str, str]] = []
        if code == "VALIDATION_ERROR":
            details = _extract_validation_details(exc)
            message = default_message
        elif isinstance(exc, (ConflictError, BusinessRuleError, ExternalServiceError)):
            message = str(exc.detail) if getattr(exc, "detail", None) else default_message
            code = getattr(exc, "code", code)
            http_status = getattr(exc, "status_code", http_status)
        else:
            message = default_message
        return http_status, code, message, details

    # 2. isinstance walk (catches registered subclasses)
    for registered_type, (http_status, code, default_message) in EXCEPTION_MAP.items():
        if isinstance(exc, registered_type):
            details = []
            if code == "VALIDATION_ERROR":
                details = _extract_validation_details(exc)
                message = default_message
            elif isinstance(exc, (ConflictError, BusinessRuleError, ExternalServiceError)):
                message = str(exc.detail) if getattr(exc, "detail", None) else default_message
                code = getattr(exc, "code", code)
                http_status = getattr(exc, "status_code", http_status)
            else:
                message = default_message
            return http_status, code, message, details

    # 3. Generic APIException fallback (unmapped DRF exceptions)
    if isinstance(exc, drf_exceptions.APIException):
        status_code = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
        raw_code = getattr(exc, "default_code", None)
        code = str(raw_code).upper() if raw_code else "API_ERROR"
        return (
            status_code,
            code,
            "An API error occurred. Please try again.",
            [],
        )

    # 4. Unhandled exception → 500
    return (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "An unexpected error occurred. Please try again or contact support.",
        [],
    )


# ---------------------------------------------------------------------------
# Custom exception handler (registered in settings.py EXCEPTION_HANDLER)
# ---------------------------------------------------------------------------

def custom_exception_handler(exc: Exception, context: dict) -> Response:
    """
    DRF custom exception handler enforcing the project's standard error envelope.

    Registered via REST_FRAMEWORK["EXCEPTION_HANDLER"] in config/settings.py.

    Design:
    - Calls DRF's built-in handler first so Http404 / PermissionDenied are
      coerced to DRF exceptions before our classification step.
    - Extracts request_id from context["request"].request_id (set by
      RequestIDMiddleware in BE-005); falls back to generate_request_id().
    - Logs 5xx at ERROR with exc_info=True (stack trace server-side only).
    - Logs 4xx at WARNING.
    - Never exposes raw exception messages, class names, or tracebacks to clients.
    - Wrapped in a safety try/except so a handler crash never propagates as an
      unhandled Django exception.
    """
    try:
        # Let DRF coerce Http404 and django PermissionDenied to DRF exceptions
        drf_exception_handler(exc, context)

        # Extract request_id — safe against None request in context
        request: Request | None = context.get("request")
        request_id: str = getattr(request, "request_id", None) or generate_request_id()

        # Classify the exception
        http_status, code, message, details = _classify_exception(exc)

        # Log appropriately
        if http_status >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error(
                "Unhandled server exception [%s]",
                type(exc).__name__,
                extra={"request_id": request_id, "exc_type": type(exc).__name__},
                exc_info=True,
            )
        else:
            logger.warning(
                "Client error [%s] → %s %s",
                type(exc).__name__,
                http_status,
                code,
                extra={"request_id": request_id, "status_code": http_status},
            )

        return ApiResponse.error(
            code=code,
            message=message,
            details=details,
            status_code=http_status,
            request_id=request_id,
        )

    except Exception as handler_exc:  # noqa: BLE001
        # Safety net: if the handler itself fails, return a minimal 500
        # without exposing any internal detail.
        logger.error(
            "Exception handler itself raised an exception: %s",
            type(handler_exc).__name__,
            exc_info=True,
        )
        return JsonResponse(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        "An unexpected error occurred. "
                        "Please try again or contact support."
                    ),
                    "details": [],
                },
                "requestId": generate_request_id(),
            },
            status=500,
        )

