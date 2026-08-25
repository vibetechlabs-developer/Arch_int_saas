"""
BE-006 – Global Exception Handler Tests
Covers all exception mapping, error code standards, custom domain exceptions,
validation flattening, requestId propagation, and security invariants.
"""

import django.core.exceptions as django_exceptions
from django.http import Http404
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.common.exceptions import (
    BusinessRuleError,
    BusinessRuleException,
    ConflictError,
    ConflictException,
    ExternalServiceBadGateway,
    ExternalServiceError,
    ExternalServiceException,
    ExternalServiceUnavailable,
    custom_exception_handler,
    flatten_validation_errors,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _call_handler(exc: Exception, request_id: str = "req_9f2c81a7b3d4") -> Response:
    """
    Build a minimal context and call custom_exception_handler directly.
    """
    factory = APIRequestFactory()
    request = factory.get("/api/test/")
    request.request_id = request_id
    context = {"request": request, "view": None, "args": (), "kwargs": {}}
    return custom_exception_handler(exc, context)


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

class ExceptionHandlerTestCase(TestCase):
    """
    Full test suite for BE-006 – custom_exception_handler.
    Every test asserts:
      - correct HTTP status code
      - correct UPPER_SNAKE_CASE error code
      - success == False
      - requestId propagated
      - X-Request-ID header present
      - no internal detail in response body (for 5xx/external errors)
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.request_id = "req_9f2c81a7b3d4"

    # --- 1. ValidationError → 400 + VALIDATION_ERROR ---

    def test_validation_error_returns_400(self):
        exc = drf_exceptions.ValidationError({"name": ["This field is required."]})
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")
        self.assertIsInstance(response.data["error"]["details"], list)
        self.assertGreater(len(response.data["error"]["details"]), 0)
        self.assertEqual(response.data["requestId"], self.request_id)
        self.assertEqual(response.headers["X-Request-ID"], self.request_id)

    # --- 2. ParseError → 400 + PARSE_ERROR ---

    def test_parse_error_returns_400(self):
        exc = drf_exceptions.ParseError("JSON parse error")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "PARSE_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)

    # --- 3. NotAuthenticated → 401 + AUTHENTICATION_ERROR ---

    def test_not_authenticated_returns_401_authentication_error(self):
        exc = drf_exceptions.NotAuthenticated()
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "AUTHENTICATION_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)

    # --- 4. AuthenticationFailed → 401 + AUTHENTICATION_ERROR ---

    def test_authentication_failed_returns_401_authentication_error(self):
        exc = drf_exceptions.AuthenticationFailed("Token expired.")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "AUTHENTICATION_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)

    # --- 5. PermissionDenied (DRF) → 403 + PERMISSION_ERROR ---

    def test_drf_permission_denied_returns_403_permission_error(self):
        exc = drf_exceptions.PermissionDenied()
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "PERMISSION_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)

    # --- 6. PermissionDenied (Django) → 403 + PERMISSION_ERROR ---

    def test_django_permission_denied_returns_403_permission_error(self):
        exc = django_exceptions.PermissionDenied("Access denied.")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "PERMISSION_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)

    # --- 7. NotFound (DRF) → 404 + NOT_FOUND ---

    def test_drf_not_found_returns_404(self):
        exc = drf_exceptions.NotFound()
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "NOT_FOUND")
        self.assertEqual(response.data["error"]["details"], [])

    # --- 8. Http404 (Django) → 404 + NOT_FOUND ---

    def test_django_http404_returns_404(self):
        exc = Http404("Page not found.")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "NOT_FOUND")
        self.assertEqual(response.data["error"]["details"], [])

    # --- 9. MethodNotAllowed → 405 + METHOD_NOT_ALLOWED ---

    def test_method_not_allowed_returns_405(self):
        exc = drf_exceptions.MethodNotAllowed("DELETE")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "METHOD_NOT_ALLOWED")
        self.assertEqual(response.data["error"]["details"], [])

    # --- 10. ConflictError → 409 + CONFLICT ---

    def test_conflict_error_returns_409(self):
        exc = ConflictError()
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "CONFLICT")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)
        self.assertEqual(response.headers["X-Request-ID"], self.request_id)

    def test_conflict_exception_with_custom_message(self):
        exc = ConflictException("An invoice with this number already exists.")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"]["code"], "CONFLICT")
        self.assertEqual(
            response.data["error"]["message"],
            "An invoice with this number already exists.",
        )
        self.assertEqual(response.data["error"]["details"], [])

    # --- 11. BusinessRuleError → 422 + BUSINESS_RULE_ERROR ---

    def test_business_rule_error_returns_422(self):
        exc = BusinessRuleError()
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "BUSINESS_RULE_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)
        self.assertEqual(response.headers["X-Request-ID"], self.request_id)

    def test_business_rule_exception_custom_code_and_message(self):
        exc = BusinessRuleException(
            detail="This invoice has already been fully paid.",
            code="INVOICE_ALREADY_PAID",
        )
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["error"]["code"], "INVOICE_ALREADY_PAID")
        self.assertEqual(
            response.data["error"]["message"],
            "This invoice has already been fully paid.",
        )
        self.assertEqual(response.data["error"]["details"], [])

    # --- 12. Throttled → 429 + RATE_LIMIT_EXCEEDED ---

    def test_throttled_returns_429(self):
        exc = drf_exceptions.Throttled(wait=60)
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "RATE_LIMIT_EXCEEDED")
        self.assertEqual(response.data["error"]["details"], [])

    # --- 13. ExternalServiceError → 502 / 503 + EXTERNAL_SERVICE_ERROR ---

    def test_external_service_bad_gateway_returns_502(self):
        exc = ExternalServiceError()
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "EXTERNAL_SERVICE_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)
        self.assertEqual(response.headers["X-Request-ID"], self.request_id)

    def test_external_service_unavailable_returns_503(self):
        exc = ExternalServiceUnavailable()
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "EXTERNAL_SERVICE_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        self.assertEqual(response.data["requestId"], self.request_id)
        self.assertEqual(response.headers["X-Request-ID"], self.request_id)

    def test_external_service_exception_alias(self):
        exc = ExternalServiceBadGateway("Payment provider unreachable.")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["error"]["code"], "EXTERNAL_SERVICE_ERROR")
        self.assertEqual(response.data["error"]["message"], "Payment provider unreachable.")

    # --- 14. Unhandled Exception → 500 + INTERNAL_ERROR ---

    def test_unhandled_exception_returns_500(self):
        exc = RuntimeError("Database connection failed: password authentication failed")
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "INTERNAL_ERROR")
        self.assertEqual(response.data["error"]["details"], [])
        # The raw exception message must NEVER appear in the response
        response_str = str(response.data)
        self.assertNotIn("Database connection failed", response_str)
        self.assertNotIn("password authentication failed", response_str)
        self.assertNotIn("RuntimeError", response_str)

    # --- 15. requestId propagated from request.request_id ---

    def test_request_id_propagated_into_error_envelope(self):
        custom_id = "req_aabbcc112233"
        exc = drf_exceptions.NotFound()
        response = _call_handler(exc, custom_id)

        self.assertEqual(response.data["requestId"], custom_id)
        self.assertEqual(response.headers["X-Request-ID"], custom_id)

    # --- 16. X-Request-ID header present on all error responses ---

    def test_x_request_id_header_always_present(self):
        exceptions_to_test = [
            drf_exceptions.ValidationError({"field": ["required"]}),
            drf_exceptions.NotAuthenticated(),
            drf_exceptions.PermissionDenied(),
            drf_exceptions.NotFound(),
            ConflictError(),
            BusinessRuleError(),
            drf_exceptions.Throttled(),
            ExternalServiceError(),
            ExternalServiceUnavailable(),
            RuntimeError("something went wrong"),
        ]

        for exc in exceptions_to_test:
            response = _call_handler(exc, self.request_id)
            self.assertIn(
                "X-Request-ID",
                response.headers,
                msg=f"X-Request-ID missing for {type(exc).__name__}",
            )
            self.assertEqual(
                response.headers["X-Request-ID"],
                self.request_id,
                msg=f"X-Request-ID mismatch for {type(exc).__name__}",
            )

    # --- 17. Validation error detail flattening — dict-of-lists ---

    def test_flatten_validation_errors_dict_of_lists(self):
        detail = {
            "quantity": ["Must be a positive number.", "This field is required."],
            "clientId": ["This field is required."],
        }
        result = flatten_validation_errors(detail)

        self.assertEqual(len(result), 3)
        fields = [item["field"] for item in result]
        self.assertIn("quantity", fields)
        self.assertIn("clientId", fields)

        quantity_issues = [item["issue"] for item in result if item["field"] == "quantity"]
        self.assertIn("Must be a positive number.", quantity_issues)
        self.assertIn("This field is required.", quantity_issues)

    # --- 18. Validation error detail flattening — nested dict (dot notation) ---

    def test_flatten_validation_errors_nested_dict(self):
        detail = {
            "lineItems": {
                "0": {
                    "quantity": ["Must be greater than 0."],
                }
            }
        }
        result = flatten_validation_errors(detail)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["field"], "lineItems.0.quantity")
        self.assertEqual(result[0]["issue"], "Must be greater than 0.")

    # --- 19. Validation error detail — non_field_errors → __all__ ---

    def test_flatten_validation_errors_non_field_errors(self):
        detail = {
            "non_field_errors": ["Passwords do not match.", "Account is locked."],
        }
        result = flatten_validation_errors(detail)

        self.assertEqual(len(result), 2)
        for item in result:
            self.assertEqual(item["field"], "__all__")

        issues = [item["issue"] for item in result]
        self.assertIn("Passwords do not match.", issues)
        self.assertIn("Account is locked.", issues)

    # --- 20. Django (non-DRF) ValidationError normalized ---

    def test_django_validation_error_normalized(self):
        exc = django_exceptions.ValidationError(
            ["This value is not valid.", "Must be a future date."]
        )
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")
        details = response.data["error"]["details"]
        self.assertIsInstance(details, list)
        self.assertGreater(len(details), 0)
        for item in details:
            self.assertIn("field", item)
            self.assertIn("issue", item)

    # --- 21. 500 response body contains no stack trace / internal info ---

    def test_500_response_contains_no_internal_information(self):
        exc = ValueError(
            "FATAL: password authentication failed for user 'postgres'"
        )
        response = _call_handler(exc, self.request_id)

        self.assertEqual(response.status_code, 500)

        # Flatten all response data to a single string for inspection
        response_text = str(response.data)

        forbidden_strings = [
            "ValueError",
            "FATAL",
            "postgres",
            "Traceback",
            "File ",
            "line ",
            "authentication failed for user",
        ]
        for forbidden in forbidden_strings:
            self.assertNotIn(
                forbidden,
                response_text,
                msg=f"Internal detail '{forbidden}' leaked into 500 response body",
            )

        # The message must be generic
        self.assertEqual(
            response.data["error"]["message"],
            "An unexpected error occurred. Please try again or contact support.",
        )
        self.assertEqual(response.data["error"]["details"], [])

