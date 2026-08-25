from typing import Any, Optional
from rest_framework import status
from rest_framework.response import Response

from apps.common.middleware import generate_request_id


class ApiResponse:
    """
    Standardized API Response builder for Django REST Framework.
    Enforces the platform's standard JSON response envelope and X-Request-ID header.
    """

    @classmethod
    def _prepare_headers(
        cls,
        request_id: str,
        custom_headers: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Merge custom headers with the mandatory X-Request-ID header.
        """
        headers = dict(custom_headers) if custom_headers else {}
        headers["X-Request-ID"] = request_id
        return headers

    @classmethod
    def success(
        cls,
        data: Any,
        status_code: int = status.HTTP_200_OK,
        request_id: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> Response:
        """
        Standard success response envelope (HTTP 200 by default).
        """
        req_id = request_id or generate_request_id()
        payload = {
            "success": True,
            "data": data,
            "requestId": req_id,
        }
        return Response(
            data=payload,
            status=status_code,
            headers=cls._prepare_headers(req_id, headers),
        )

    @classmethod
    def created(
        cls,
        data: Any,
        request_id: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> Response:
        """
        Standard resource created response envelope (HTTP 201 Created).
        """
        return cls.success(
            data=data,
            status_code=status.HTTP_201_CREATED,
            request_id=request_id,
            headers=headers,
        )

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        details: Optional[list[dict[str, Any]]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        request_id: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> Response:
        """
        Standard error response envelope (HTTP 4xx / 5xx).
        """
        req_id = request_id or generate_request_id()
        payload = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details if details is not None else [],
            },
            "requestId": req_id,
        }
        return Response(
            data=payload,
            status=status_code,
            headers=cls._prepare_headers(req_id, headers),
        )

    @classmethod
    def paginated(
        cls,
        data: list[Any],
        page: int,
        page_size: int,
        total_items: int,
        total_pages: int,
        request_id: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> Response:
        """
        Standard paginated collection response envelope.
        """
        req_id = request_id or generate_request_id()
        payload = {
            "success": True,
            "data": data if data is not None else [],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_items,
                "totalPages": total_pages,
            },
            "requestId": req_id,
        }
        return Response(
            data=payload,
            status=status.HTTP_200_OK,
            headers=cls._prepare_headers(req_id, headers),
        )

    @classmethod
    def no_content(
        cls,
        request_id: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> Response:
        """
        Standard HTTP 204 No Content response with empty body and X-Request-ID header.
        """
        req_id = request_id or generate_request_id()
        return Response(
            status=status.HTTP_204_NO_CONTENT,
            headers=cls._prepare_headers(req_id, headers),
        )
