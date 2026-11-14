"""Data-access layer: conversations and documents repository.

Only conversation *metadata* lives here. Message history lives solely in
the LangGraph checkpointer (Docs/AGENTS.md → Never copy messages into app
tables), so this module never queries the checkpointer's tables.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

DEFAULT_TITLE = "New chat"


class ConversationRepository:
    """CRUD for conversations and documents, scoped by anon_id."""

    def __init__(self, pool: "AsyncConnectionPool") -> None:
        self._pool = pool

    async def create(self, anon_id: uuid.UUID | str, title: str = DEFAULT_TITLE) -> dict:
        """Insert a conversation row and return it."""
        conversation_id = uuid.uuid4()
        async with self._pool.connection() as conn:
            row = await conn.execute(
                """
                insert into conversations (id, anon_id, title)
                values (%s, %s, %s)
                returning id, anon_id, title, created_at, updated_at
                """,
                (conversation_id, str(anon_id), title),
            )
            created = await row.fetchone()
        assert created is not None
        return dict(created)

    async def list_by_anon(self, anon_id: uuid.UUID | str) -> list[dict]:
        """List all conversations for an anon id, most recently updated first."""
        async with self._pool.connection() as conn:
            rows = await conn.execute(
                """
                select id, anon_id, title, created_at, updated_at
                from conversations
                where anon_id = %s
                order by updated_at desc
                """,
                (str(anon_id),),
            )
            return [dict(r) for r in await rows.fetchall()]

    async def get_by_id_and_anon(
        self, conversation_id: uuid.UUID | str, anon_id: uuid.UUID | str
    ) -> dict | None:
        """Fetch a conversation only if it belongs to the given anon id.

        Returns None for both missing and foreign conversations (404, never 403).
        """
        async with self._pool.connection() as conn:
            row = await conn.execute(
                """
                select id, anon_id, title, created_at, updated_at
                from conversations
                where id = %s and anon_id = %s
                """,
                (str(conversation_id), str(anon_id)),
            )
            result = await row.fetchone()
            return dict(result) if result else None

    async def mark_activity(
        self,
        conversation_id: uuid.UUID | str,
        anon_id: uuid.UUID | str,
        title: str,
    ) -> None:
        """Record activity on a conversation after a turn.

        Bumps updated_at so the sidebar sorts by activity, and names an
        untitled conversation after its first user message. An explicit
        rename (Task 9) is never overwritten because the title is only
        filled in while it is still the default.
        """
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                update conversations
                set title = case when title = %s then %s else title end,
                    updated_at = now()
                where id = %s and anon_id = %s
                """,
                (
                    DEFAULT_TITLE,
                    title,
                    str(conversation_id),
                    str(anon_id),
                ),
            )

    # --- Document methods ---

    async def count_documents(self, conversation_id: uuid.UUID | str) -> int:
        """Count documents for a conversation."""
        async with self._pool.connection() as conn:
            row = await conn.execute(
                """
                select count(*) as cnt from documents where conversation_id = %s
                """,
                (str(conversation_id),),
            )
            result = await row.fetchone()
            return result["cnt"] if result else 0

    async def list_documents(self, conversation_id: uuid.UUID | str) -> list[dict]:
        """List documents for a conversation."""
        async with self._pool.connection() as conn:
            rows = await conn.execute(
                """
                select id, conversation_id, filename, size_bytes, page_count, chunk_count, status, error, created_at
                from documents
                where conversation_id = %s
                order by created_at desc
                """,
                (str(conversation_id),),
            )
            return [dict(r) for r in await rows.fetchall()]

    async def create_document(
        self,
        document_id: uuid.UUID,
        conversation_id: uuid.UUID,
        filename: str,
        size_bytes: int,
        page_count: int,
        chunk_count: int,
        status: str = "ready",
        error: str | None = None,
    ) -> dict:
        """Insert a document record."""
        async with self._pool.connection() as conn:
            row = await conn.execute(
                """
                insert into documents (id, conversation_id, filename, size_bytes, page_count, chunk_count, status, error)
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                returning id, conversation_id, filename, size_bytes, page_count, chunk_count, status, error, created_at
                """,
                (
                    document_id,
                    conversation_id,
                    filename,
                    size_bytes,
                    page_count,
                    chunk_count,
                    status,
                    error,
                ),
            )
            created = await row.fetchone()
            assert created is not None
            return dict(created)

    async def delete_document(
        self, document_id: uuid.UUID | str, conversation_id: uuid.UUID | str
    ) -> bool:
        """Delete a document (cascades to doc_chunks via FK)."""
        async with self._pool.connection() as conn:
            row = await conn.execute(
                """
                delete from documents where id = %s and conversation_id = %s
                """,
                (str(document_id), str(conversation_id)),
            )
            return row.rowcount > 0

    async def get_document(
        self, document_id: uuid.UUID | str, conversation_id: uuid.UUID | str
    ) -> dict | None:
        """Get a document by ID, scoped to conversation."""
        async with self._pool.connection() as conn:
            row = await conn.execute(
                """
                select id, conversation_id, filename, size_bytes, page_count, chunk_count, status, error, created_at
                from documents
                where id = %s and conversation_id = %s
                """,
                (str(document_id), str(conversation_id)),
            )
            result = await row.fetchone()
            return dict(result) if result else None