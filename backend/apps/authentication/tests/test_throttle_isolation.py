from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tests.base import ThrottleIsolatedTestCase


class ThrottleCacheResetsBetweenEveryTestTestCase(ThrottleIsolatedTestCase):
    """
    BE-070 regression test.

    Both methods below drain the *same* auth_forgot_password scope from
    a cold start and assert the exact same boundary: 5 requests allowed,
    the 6th throttled. Neither method depends on which of the two runs
    first — each simply asserts "this scope, starting clean, allows
    exactly 5 requests." Before ThrottleIsolatedTestCase's cache reset
    existed, whichever of these two methods ran second would inherit the
    first one's exhausted counter and trip 429 on an earlier call than
    expected (the exact shape the original bug took in
    test_reset_password_endpoint_throttles_after_configured_rate — an
    assertNotEqual(response.status_code, 429) failing mid-loop). Running
    this file with either test runner, in any collection order, must
    keep passing.
    """

    def _drain_and_confirm_exact_boundary(self, email):
        client = APIClient()
        for _ in range(5):
            response = client.post("/auth/forgot-password", {"email": email}, format="json")
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = client.post("/auth/forgot-password", {"email": email}, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_run_one_drains_scope_from_a_cold_start(self):
        self._drain_and_confirm_exact_boundary("iso-one@example.com")

    def test_run_two_drains_scope_from_a_cold_start(self):
        self._drain_and_confirm_exact_boundary("iso-two@example.com")
