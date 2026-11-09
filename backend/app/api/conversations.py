"""Conversation router: create, list, get conversations.

All routes are scoped by X-Anon-Id. Foreign or missing conversations
return 404 (never 403), per Docs/AGENTS.md.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

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


def _message_to_dict(msg: BaseMessage) -> dict[str, Any]:
    """Convert a LangChain message to the frontend-facing dict shape."""
    if isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    else:
        role = msg.type
    return {"role": role, "content": msg.content}


async def _thread_messages(checkpointer: Any, thread_id: str) -> list[dict[str, Any]]:
    """Fetch the latest checkpoint's messages for a thread."""
    if checkpointer is None:
        return []
    config = {"configurable": {"thread_id": thread_id}}
    tuple_ = await checkpointer.aget_tuple(config)
    if tuple_ is None:
        return []
    checkpoint = tuple_.checkpoint
    channel_values = checkpoint.get("channel_values", {})
    messages = channel_values.get("messages", [])
    return [_message_to_dict(m) for m in messages]


@router.post("", status_code=201, summary="Create a new conversation")
async def create_conversation(
    request: Request,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> JSONResponse:
    """Create a conversation row for the anon id and return its id."""
    repo = _repo(request)
    conversation_id = await repo.create(anon_id)
    return JSONResponse(status_code=201, content={"id": str(conversation_id)})


@router.get("", summary="List conversations for the current anon id")
async def list_conversations(
    request: Request,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> list[dict]:
    """Return all conversations belonging to the anon id."""
    repo = _repo(request)
    rows = await repo.list_by_anon(anon_id)
    return [
        {
            "id": str(r["id"]),
            "anon_id": str(r["anon_id"]),
            "title": r["title"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]


@router.get("/{conversation_id}", summary="Get a conversation by id")
async def get_conversation(
    request: Request,
    conversation_id: uuid.UUID,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> dict:
    """Return a conversation (with messages from the checkpointer) if it belongs to the anon id, else 404."""
    repo = _repo(request)
    row = await repo.get_by_id_and_anon(conversation_id, anon_id)
    if row is None:
        raise not_found()

    checkpointer = _checkpointer(request)
    messages = await _thread_messages(checkpointer, str(conversation_id)) if checkpointer else []

    return {
        "id": str(row["id"]),
        "anon_id": str(row["anon_id"]),
        "title": row["title"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "messages": messages,
    }
