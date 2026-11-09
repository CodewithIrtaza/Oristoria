"""Data-access layer: conversations repository."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool


class ConversationRepository:
    """CRUD for conversations, scoped by anon_id."""

    def __init__(self, pool: "AsyncConnectionPool") -> None:
        self._pool = pool

    async def create(self, anon_id: uuid.UUID | str, title: str = "New chat") -> uuid.UUID:
        """Insert a conversation row and return its id."""
        conversation_id = uuid.uuid4()
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                insert into conversations (id, anon_id, title)
                values (%s, %s, %s)
                """,
                (conversation_id, str(anon_id), title),
            )
        return conversation_id

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

    async def message_count(self, conversation_id: uuid.UUID | str) -> int:
        """Return the number of messages in a thread's checkpointer history.

        Used to derive a default title from the first user message.
        """
        async with self._pool.connection() as conn:
            row = await conn.execute(
                "select count(*) as c from checkpoints where thread_id = %s",
                (str(conversation_id),),
            )
            result = await row.fetchone()
            return int(result["c"]) if result else 0
