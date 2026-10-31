"""RunRegistry: tracks active LangGraph runs per thread.

Guarantees at most one concurrent run per thread_id (returns 409 otherwise).
Also owns the global generation semaphore.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from app.config import settings


class RunRegistry:
    """Thread-level run lock + global concurrency semaphore."""

    def __init__(self, max_concurrent: int) -> None:
        self._active: set[str] = set()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def is_active(self, thread_id: str) -> bool:
        async with self._lock:
            return thread_id in self._active

    @asynccontextmanager
    async def run(self, thread_id: str):
        """Context manager that acquires the per-thread lock and semaphore.

        Raises RuntimeError if the thread already has an active run.
        """
        async with self._lock:
            if thread_id in self._active:
                raise RuntimeError(f"Run already active for thread {thread_id}")
            self._active.add(thread_id)

        async with self._semaphore:
            try:
                yield
            finally:
                async with self._lock:
                    self._active.discard(thread_id)


# Module-level singleton
run_registry = RunRegistry(max_concurrent=settings.max_concurrent_generations)
