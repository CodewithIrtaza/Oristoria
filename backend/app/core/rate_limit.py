"""In-memory sliding-window rate limiter keyed by anon_id or IP.

Implemented in Task 2. Stub here for import structure.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from app.config import settings


class RateLimiter:
    """Per-key sliding window rate limiter."""

    def __init__(self, per_hour: int, per_day: int) -> None:
        self.per_hour = per_hour
        self.per_day = per_day
        # key → deque of timestamps (seconds)
        self._windows: dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds). allowed=True means OK."""
        now = time.time()
        window = self._windows[key]

        # Evict entries older than 24 hours
        cutoff_day = now - 86_400
        while window and window[0] < cutoff_day:
            window.popleft()

        day_count = len(window)
        hour_count = sum(1 for t in window if t > now - 3_600)

        if day_count >= self.per_day:
            retry_after = int(window[0] + 86_400 - now) + 1
            return False, retry_after
        if hour_count >= self.per_hour:
            # Find oldest in the last hour
            hour_start = next(t for t in window if t > now - 3_600)
            retry_after = int(hour_start + 3_600 - now) + 1
            return False, retry_after

        window.append(now)
        return True, 0


# Module-level singleton; keys are anon_id strings
rate_limiter = RateLimiter(
    per_hour=settings.rate_limit_per_hour,
    per_day=settings.rate_limit_per_day,
)
