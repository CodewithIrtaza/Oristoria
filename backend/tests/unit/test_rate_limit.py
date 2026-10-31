"""Unit tests for the in-memory rate limiter."""
import time

import pytest

from app.core.rate_limit import RateLimiter


def test_allows_first_request():
    limiter = RateLimiter(per_hour=5, per_day=10)
    allowed, retry_after = limiter.check("user1")
    assert allowed is True
    assert retry_after == 0


def test_blocks_after_hourly_limit():
    limiter = RateLimiter(per_hour=3, per_day=100)
    for _ in range(3):
        limiter.check("user1")
    allowed, retry_after = limiter.check("user1")
    assert allowed is False
    assert retry_after > 0


def test_per_key_isolation():
    limiter = RateLimiter(per_hour=1, per_day=10)
    limiter.check("user_a")
    # user_a is now at limit; user_b should still be allowed
    allowed_b, _ = limiter.check("user_b")
    assert allowed_b is True


def test_blocks_after_daily_limit():
    limiter = RateLimiter(per_hour=100, per_day=2)
    limiter.check("x")
    limiter.check("x")
    allowed, retry_after = limiter.check("x")
    assert allowed is False
    assert retry_after > 0
