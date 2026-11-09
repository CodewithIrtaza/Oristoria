"""Shared fixtures for integration tests.

These tests need a reachable Postgres (see Docs/AGENTS.md: docker
compose db is the canonical path). They are skipped, not failed, when
no database is reachable.

Concurrency note: these helpers deliberately use *sync* psycopg. The
app's own pool (psycopg_pool.AsyncConnectionPool) runs on the app's
event loop; the fixture-side connections are just for setup/teardown.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
import psycopg

from app.config import settings

CHECKPOINT_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")


def _dsn_for_tests() -> str:
    dsn = settings.database_url
    # Compose stores a SQLAlchemy-style DSN; psycopg wants the plain one.
    return dsn.replace("+psycopg", "", 1) if dsn else ""


@pytest.fixture
def db_available() -> str:
    """Return a psycopg DSN, or skip when the database is unreachable."""
    dsn = _dsn_for_tests()
    if not dsn:
        pytest.skip("DATABASE_URL is not set (integration needs Postgres)")
    try:
        psycopg.connect(dsn, autocommit=True, connect_timeout=5).close()
    except Exception:
        pytest.skip("No reachable Postgres for integration tests")
    return dsn


@pytest.fixture(autouse=True)
def db_cleaner(db_available: str) -> Iterator[None]:
    """Wipe app tables (and checkpoint rows if present) between tests."""

    def _clean() -> None:
        conn = psycopg.connect(db_available, autocommit=True)
        try:
            for table in (
                "conversations",
                "documents",
                "doc_chunks",
                *CHECKPOINT_TABLES,
            ):
                try:
                    conn.execute(f"TRUNCATE {table}")
                except psycopg.errors.UndefinedTable:
                    pass  # created lazily by migrations / AsyncPostgresSaver.setup()
        finally:
            conn.close()

    _clean()
    yield
    _clean()
