import re
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.response import Response

from apps.common.middleware import (
    REQUEST_ID_REGEX,
    RequestIDMiddleware,
    generate_request_id,
    is_valid_request_id,
)
from apps.common.responses import ApiResponse


class ApiResponseTestCase(TestCase):
    """
    Test suite for standardized API response structures and RequestIDMiddleware.
    """

    def setUp(self):
        self.factory = RequestFactory()

    # --- 1. Success Response Tests ---

    def test_success_response_structure(self):
        data = {"id": "550e8400-e29b-41d4-a716-446655440000", "name": "Acme Studios"}
        response = ApiResponse.success(data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"], data)
        self.assertIn("requestId", response.data)
        self.assertTrue(bool(REQUEST_ID_REGEX.match(response.data["requestId"])))
        self.assertEqual(response.headers["X-Request-ID"], response.data["requestId"])

    # --- 2. Created Response Tests ---

    def test_created_response_structure(self):
        data = {"id": "550e8400-e29b-41d4-a716-446655440000", "name": "New Project"}
        response = ApiResponse.created(data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"], data)
        self.assertIn("requestId", response.data)
        self.assertTrue(bool(REQUEST_ID_REGEX.match(response.data["requestId"])))
        self.assertEqual(response.headers["X-Request-ID"], response.data["requestId"])

    # --- 3. Error Response Tests ---

    def test_error_response_structure(self):
        test_statuses = [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_409_CONFLICT,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_429_TOO_MANY_REQUESTS,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_502_BAD_GATEWAY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        for code_status in test_statuses:
            response = ApiResponse.error(
                code="INVOICE_ALREADY_PAID",
                message="This invoice has already been fully paid.",
                status_code=code_status,
            )

            self.assertEqual(response.status_code, code_status)
            self.assertFalse(response.data["success"])
            self.assertEqual(response.data["error"]["code"], "INVOICE_ALREADY_PAID")
            self.assertEqual(
                response.data["error"]["message"],
                "This invoice has already been fully paid.",
            )
            self.assertEqual(response.data["error"]["details"], [])
            self.assertIn("requestId", response.data)
            self.assertTrue(bool(REQUEST_ID_REGEX.match(response.data["requestId"])))
            self.assertEqual(response.headers["X-Request-ID"], response.data["requestId"])

    # --- 4. Validation Error Tests ---

    def test_validation_error_structure(self):
        details = [
            {"field": "quantity", "issue": "must be greater than 0"},
            {"field": "clientId", "issue": "required"},
        ]
        response = ApiResponse.error(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(response.data["error"]["message"], "Request validation failed")
        self.assertEqual(response.data["error"]["details"], details)
        self.assertIn("requestId", response.data)

    # --- 5. No Content Tests ---

    def test_no_content_response(self):
        custom_id = "req_112233445566"
        response = ApiResponse.no_content(request_id=custom_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)
        self.assertEqual(response.headers["X-Request-ID"], custom_id)

    # --- 6. Custom Headers & Request ID Propagation ---

    def test_request_id_is_present_in_response(self):
        custom_id = "req_abcdef123456"
        response = ApiResponse.success(data={"status": "ok"}, request_id=custom_id)

        self.assertEqual(response.data["requestId"], custom_id)
        self.assertEqual(response.headers["X-Request-ID"], custom_id)

    def test_custom_headers_are_preserved(self):
        custom_headers = {"X-Custom-Header": "TestValue", "X-Trace-Info": "Trace123"}
        response = ApiResponse.success(
            data={"test": True},
            headers=custom_headers,
        )

        self.assertEqual(response.headers["X-Custom-Header"], "TestValue")
        self.assertEqual(response.headers["X-Trace-Info"], "Trace123")
        self.assertIn("X-Request-ID", response.headers)

    # --- 7. RequestIDMiddleware Tests ---

    def test_middleware_generates_request_id_when_missing(self):
        request = self.factory.get("/api/test")
        middleware = RequestIDMiddleware(lambda req: HttpResponse("OK"))
        response = middleware(request)

        self.assertTrue(hasattr(request, "request_id"))
        self.assertTrue(bool(REQUEST_ID_REGEX.match(request.request_id)))
        self.assertEqual(response["X-Request-ID"], request.request_id)

    def test_middleware_propagates_valid_incoming_request_id(self):
        valid_incoming_id = "req_9f2c81a7b3d4"
        request = self.factory.get("/api/test", HTTP_X_REQUEST_ID=valid_incoming_id)
        middleware = RequestIDMiddleware(lambda req: HttpResponse("OK"))
        response = middleware(request)

        self.assertEqual(request.request_id, valid_incoming_id)
        self.assertEqual(response["X-Request-ID"], valid_incoming_id)

    def test_middleware_replaces_invalid_incoming_request_id(self):
        invalid_incoming_ids = [
            "invalid_id_format",
            "req_toolong1234567890",
            "req_short",
            "123456789012",
            "<script>alert(1)</script>",
        ]

        for invalid_id in invalid_incoming_ids:
            request = self.factory.get("/api/test", HTTP_X_REQUEST_ID=invalid_id)
            middleware = RequestIDMiddleware(lambda req: HttpResponse("OK"))
            response = middleware(request)

            self.assertNotEqual(request.request_id, invalid_id)
            self.assertTrue(bool(REQUEST_ID_REGEX.match(request.request_id)))
            self.assertEqual(response["X-Request-ID"], request.request_id)
