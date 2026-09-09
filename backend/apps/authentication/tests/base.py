from django.core.cache import cache
from django.test import TestCase


class ThrottleIsolatedTestCase(TestCase):
    """
    Base class for every TestCase in this app that exercises a
    throttle_scope'd endpoint (login, forgot-password, reset-password,
    refresh, platform-auth login) or the throttling behavior itself.

    DRF's ScopedRateThrottle keys its request counters on
    f"throttle_{scope}_{ident}" in Django's cache backend (LocMemCache
    here), where `ident` is the client IP for these pre-auth endpoints —
    a process-level store that persists across test methods and test
    classes, unlike the database, which django.test.TestCase rolls back
    via a transaction after every test. Left unhandled, an earlier test's
    calls to a throttled endpoint silently consume part of a later,
    unrelated test's rate budget, since the Django test client always
    presents the same IP.

    A repo-root conftest.py already clears the cache via an autouse
    pytest fixture, but that only runs when the suite is invoked with
    `pytest` — pytest fixtures do not exist under Django's own
    `manage.py test` runner, so that mechanism alone does not protect
    this app's tests against the leak when run that way.

    This clears the cache from `_pre_setup`/`_post_teardown` rather than
    `setUp`/`tearDown`: Django's own `SimpleTestCase` hooks its DB
    transaction wrapping into those same two methods precisely so it
    keeps working even when a subclass overrides `setUp`/`tearDown`
    without calling `super()` (every existing TestCase in this app does
    exactly that). Using the same hooks means every subclass gets
    isolation automatically, with no risk of a future test class losing
    protection by forgetting a `super().setUp()` call.
    """

    def _pre_setup(self):
        super()._pre_setup()
        cache.clear()

    def _post_teardown(self):
        cache.clear()
        super()._post_teardown()
