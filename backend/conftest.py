import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """
    DRF's ScopedRateThrottle stores request counts in Django's cache
    backend (LocMemCache by default), which is a process-level cache that
    persists across test methods — unlike the database, which each test
    rolls back via a transaction. Without clearing it, a test that hits a
    throttled endpoint (login, forgot-password, reset-password, refresh)
    can be spuriously rate-limited by an earlier, unrelated test's calls to
    the same endpoint within the same pytest run.
    """
    cache.clear()
    yield
    cache.clear()
