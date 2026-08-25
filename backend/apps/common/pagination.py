from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.common.responses import ApiResponse


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for INT Projects SaaS API.
    Enforces pageSize defaults, pageSize query parameter, max_page_size ceiling,
    and the documented JSON pagination envelope.
    """

    page_size = 25
    page_size_query_param = "pageSize"
    max_page_size = 100

    def get_paginated_response(self, data) -> Response:
        total_items = self.page.paginator.count
        total_pages = self.page.paginator.num_pages if total_items > 0 else 0
        page_number = self.page.number if total_items > 0 else 1
        page_size = self.get_page_size(self.request) or self.page_size
        request_id = getattr(self.request, "request_id", None)

        return ApiResponse.paginated(
            data=data if data is not None else [],
            page=page_number,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            request_id=request_id,
        )

    def get_paginated_response_schema(self, schema):
        """
        OpenAPI response schema generation for drf-spectacular compatibility.
        """
        return {
            "type": "object",
            "properties": {
                "success": {
                    "type": "boolean",
                    "example": True,
                },
                "data": schema,
                "pagination": {
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "example": 1,
                        },
                        "pageSize": {
                            "type": "integer",
                            "example": 25,
                        },
                        "totalItems": {
                            "type": "integer",
                            "example": 100,
                        },
                        "totalPages": {
                            "type": "integer",
                            "example": 4,
                        },
                    },
                    "required": ["page", "pageSize", "totalItems", "totalPages"],
                },
                "requestId": {
                    "type": "string",
                    "example": "req_9f2c81a7b3d4",
                },
            },
            "required": ["success", "data", "pagination", "requestId"],
        }


# Aliases for convenience
StandardPagination = StandardResultsSetPagination

