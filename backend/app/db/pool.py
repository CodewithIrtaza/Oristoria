"""psycopg 3 async connection pool.

Implemented in Task 1. Stub here; pool is opened in lifespan.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

# Module-level pool; assigned during app lifespan startup.
pool: "AsyncConnectionPool | None" = None

# TODO Task 1:
# async def open_pool(dsn: str) -> AsyncConnectionPool
# async def close_pool() -> None
