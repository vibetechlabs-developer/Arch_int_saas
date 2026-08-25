from django.test import TestCase
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination


class DummyListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        # Generate 60 test items
        items = [{"id": i, "name": f"Item {i}"} for i in range(1, 61)]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(items, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(page)
        return paginator.get_paginated_response(items)


class DummyEmptyListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        items = []
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(items, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(page)
        return paginator.get_paginated_response(items)


class PaginationTestCase(TestCase):
    """
    Test suite for StandardResultsSetPagination and DRF integration.
    """

    def setUp(self):
        self.factory = APIRequestFactory()

    # --- 1. Paginated Response Structure ---

    def test_paginated_response_structure(self):
        request = self.factory.get("/api/items/?page=1&pageSize=25")
        request.request_id = "req_9f2c81a7b3d4"

        view = DummyListView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 25)

        pagination = response.data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["pageSize"], 25)
        self.assertEqual(pagination["totalItems"], 60)
        self.assertEqual(pagination["totalPages"], 3)

        self.assertEqual(response.data["requestId"], "req_9f2c81a7b3d4")
        self.assertEqual(response.headers["X-Request-ID"], "req_9f2c81a7b3d4")

    # --- 2. Empty Paginated Response ---

    def test_empty_paginated_response(self):
        request = self.factory.get("/api/empty-items/")
        request.request_id = "req_000000000000"

        view = DummyEmptyListView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"], [])

        pagination = response.data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["pageSize"], 25)
        self.assertEqual(pagination["totalItems"], 0)
        self.assertEqual(pagination["totalPages"], 0)

    # --- 3. Default Page Size ---

    def test_default_page_size(self):
        request = self.factory.get("/api/items/")
        view = DummyListView.as_view()
        response = view(request)

        self.assertEqual(response.data["pagination"]["pageSize"], 25)
        self.assertEqual(len(response.data["data"]), 25)

    # --- 4. Custom Page Size Parameter ---

    def test_custom_page_size(self):
        request = self.factory.get("/api/items/?pageSize=50")
        view = DummyListView.as_view()
        response = view(request)

        self.assertEqual(response.data["pagination"]["pageSize"], 50)
        self.assertEqual(len(response.data["data"]), 50)
        self.assertEqual(response.data["pagination"]["totalPages"], 2)

    # --- 5. Page Size Maximum Ceiling ---

    def test_page_size_maximum(self):
        request = self.factory.get("/api/items/?pageSize=200")
        view = DummyListView.as_view()
        response = view(request)

        # Capped at max_page_size = 100
        self.assertEqual(response.data["pagination"]["pageSize"], 100)
        self.assertEqual(len(response.data["data"]), 60)
        self.assertEqual(response.data["pagination"]["totalPages"], 1)

    # --- 6. Page Parameter ---

    def test_page_parameter(self):
        request = self.factory.get("/api/items/?page=2&pageSize=25")
        view = DummyListView.as_view()
        response = view(request)

        self.assertEqual(response.data["pagination"]["page"], 2)
        self.assertEqual(len(response.data["data"]), 25)
        self.assertEqual(response.data["data"][0]["id"], 26)

    # --- 7. Multiple Pages Calculation ---

    def test_multiple_pages(self):
        request = self.factory.get("/api/items/?page=3&pageSize=25")
        view = DummyListView.as_view()
        response = view(request)

        self.assertEqual(response.data["pagination"]["page"], 3)
        self.assertEqual(response.data["pagination"]["totalPages"], 3)
        self.assertEqual(len(response.data["data"]), 10)  # 60 - 50 = 10 items on page 3

    # --- 8. Request ID in Paginated Response ---

    def test_request_id_in_paginated_response(self):
        request = self.factory.get("/api/items/")
        request.request_id = "req_custom12345"

        view = DummyListView.as_view()
        response = view(request)

        self.assertEqual(response.data["requestId"], "req_custom12345")
        self.assertEqual(response.headers["X-Request-ID"], "req_custom12345")

    # --- 9. CamelCase Envelope Keys ---

    def test_pagination_uses_camel_case_keys(self):
        request = self.factory.get("/api/items/")
        view = DummyListView.as_view()
        response = view(request)

        # Top-level keys
        self.assertIn("requestId", response.data)
        self.assertNotIn("request_id", response.data)

        # Pagination keys
        pagination = response.data["pagination"]
        self.assertIn("pageSize", pagination)
        self.assertNotIn("page_size", pagination)
        self.assertIn("totalItems", pagination)
        self.assertNotIn("total_items", pagination)
        self.assertIn("totalPages", pagination)
        self.assertNotIn("total_pages", pagination)
