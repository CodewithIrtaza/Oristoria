"""psycopg 3 async connection pool.

Opened in app lifespan; closed on shutdown. Uses autocommit=True and
dict_row as required by AsyncPostgresSaver (Docs/AGENTS.md).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

# Module-level pool; assigned during app lifespan startup.
pool: "AsyncConnectionPool | None" = None


async def open_pool(dsn: str) -> None:
    """Open the async connection pool (autocommit + dict_row)."""
    global pool
    from psycopg_pool import AsyncConnectionPool
    from psycopg.rows import dict_row

    # psycopg does not understand SQLAlchemy-style "+psycopg" driver specifiers.
    dsn = dsn.replace("+psycopg", "", 1)

    pool = AsyncConnectionPool(
        dsn,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=True,
    )


async def close_pool() -> None:
    """Close the async connection pool."""
    global pool
    if pool is not None:
        await pool.close()
        pool = None
