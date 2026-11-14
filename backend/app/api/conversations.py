"""Conversation router: create, list, get conversations.

All routes are scoped by X-Anon-Id. Foreign or missing conversations
return 404 (never 403), per Docs/AGENTS.md.

Response shapes follow Docs/TECH_DESIGN.md §4:

    POST /conversations       -> 201 {"id","title","created_at","updated_at"}
    GET  /conversations       -> 200 {"items":[{"id","title","updated_at"}]}
    GET  /conversations/{id}  -> 200 {"conversation":{...},"messages":[...],"documents":[...]}

Message history is read back from the LangGraph checkpointer, never from
an app table.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.core.anon_id import get_anon_id
from app.core.errors import not_found
from app.db.repositories import ConversationRepository

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _repo(request: Request) -> ConversationRepository:
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=500, detail="Database pool not available")
    return ConversationRepository(pool)


def _checkpointer(request: Request) -> Any:
    return getattr(request.app.state, "checkpointer", None)


def _timestamp(value: Any) -> str | None:
    return value.isoformat() if value else None


def _conversation_payload(row: dict) -> dict:
    """The conversation metadata object shared by every response."""
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "created_at": _timestamp(row["created_at"]),
        "updated_at": _timestamp(row["updated_at"]),
    }


def _message_to_dict(msg: BaseMessage, index: int) -> dict[str, Any]:
    """Convert a LangChain message to the frontend-facing dict shape."""
    if isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    else:
        role = msg.type
    return {
        "id": msg.id or f"msg-{index}",
        "role": role,
        "content": msg.content if isinstance(msg.content, str) else str(msg.content),
        "stopped": bool(msg.additional_kwargs.get("stopped", False)),
        "tools": [],
    }


async def _thread_messages(checkpointer: Any, thread_id: str) -> list[dict[str, Any]]:
    """Fetch the latest checkpoint's messages for a thread."""
    if checkpointer is None:
        return []
    config = {"configurable": {"thread_id": thread_id}}
    tuple_ = await checkpointer.aget_tuple(config)
    if tuple_ is None:
        return []
    channel_values = tuple_.checkpoint.get("channel_values", {})
    messages = channel_values.get("messages", [])
    return [_message_to_dict(m, i) for i, m in enumerate(messages)]


@router.post("", status_code=201, summary="Create a new conversation")
async def create_conversation(
    request: Request,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> JSONResponse:
    """Create a conversation row for the anon id."""
    repo = _repo(request)
    row = await repo.create(anon_id)
    return JSONResponse(status_code=201, content=_conversation_payload(row))


@router.get("", summary="List conversations for the current anon id")
async def list_conversations(
    request: Request,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> dict:
    """Return the anon id's conversations, newest first."""
    repo = _repo(request)
    rows = await repo.list_by_anon(anon_id)
    return {
        "items": [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "updated_at": _timestamp(row["updated_at"]),
            }
            for row in rows
        ]
    }


async def get_conversation_or_404(
    conversation_id: uuid.UUID,
    anon_id: str,
    pool,
) -> dict:
    """Fetch a conversation or raise 404 if not found or not owned.

    Used by other routers (documents, etc.) that need to verify ownership
    without returning full conversation details.
    """
    repo = ConversationRepository(pool)
    row = await repo.get_by_id_and_anon(conversation_id, anon_id)
    if row is None:
        raise not_found()
    return row


@router.get("/{conversation_id}", summary="Get a conversation by id")
async def get_conversation(
    request: Request,
    conversation_id: uuid.UUID,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> dict:
    """Return a conversation with its messages, or 404 when it is not ours."""
    repo = _repo(request)
    row = await repo.get_by_id_and_anon(conversation_id, anon_id)
    if row is None:
        raise not_found()

    checkpointer = _checkpointer(request)
    messages = await _thread_messages(checkpointer, str(conversation_id))

    return {
        "conversation": _conversation_payload(row),
        "messages": messages,
        "documents": [],
    }
