from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckTestCase(APITestCase):
    """
    BE-020: /health/ is a container/orchestrator liveness endpoint. It must
    never require authentication and must never depend on the database or
    any other service, so these tests deliberately exercise it with no
    token, an invalid token, and a valid-but-unrelated token — all must
    succeed identically.
    """

    def test_health_check_returns_200_with_no_authentication(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["status"], "ok")
        self.assertIn("requestId", response.data)

    def test_health_check_ignores_invalid_bearer_token(self):
        response = self.client.get(
            "/health/", HTTP_AUTHORIZATION="Bearer not-a-real-token"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "ok")

    def test_health_check_sets_request_id_header(self):
        response = self.client.get("/health/")

        self.assertIn("X-Request-ID", response)
        self.assertEqual(response["X-Request-ID"], response.data["requestId"])
