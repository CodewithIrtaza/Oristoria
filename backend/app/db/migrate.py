"""SQL migration runner.

Reads numbered .sql files from migrations/ and applies them in order.
Each file is applied only once (idempotent via a schema_migrations table).
"""
from __future__ import annotations

from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


async def run_migrations(pool) -> None:
    """Apply all pending migrations in filename order."""
    async with pool.connection() as conn:
        await conn.execute(
            """
            create table if not exists schema_migrations (
                id       integer primary key generated always as identity,
                name     text not null unique,
                applied_at timestamptz not null default now()
            )
            """
        )
        cursor = await conn.execute("select name from schema_migrations")
        rows = await cursor.fetchall()
        applied = {row["name"] for row in rows}

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for sql_file in sql_files:
        if sql_file.name in applied:
            continue
        sql = sql_file.read_text(encoding="utf-8")
        async with pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "insert into schema_migrations (name) values (%s)",
                    (sql_file.name,),
                )
