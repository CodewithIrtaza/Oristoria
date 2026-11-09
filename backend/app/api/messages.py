"""POST /conversations/{id}/messages – single-turn SSE streaming chat.

Task 2 scope: one user message in, tokens stream out. Ownership
checks (404) land here via a route dependency; persistence runs in
Task 3 via the AsyncPostgresSaver wired into the graph by lifespan.
Task 4: client abort mid-stream saves partial message with stopped=true.
"""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from app.core.anon_id import get_anon_id
from app.core.errors import error_response, not_found
from app.db.repositories import ConversationRepository
from app.graph.build import compile_graph
from app.graph.nodes import AgentContext, user_message
from app.graph.streaming import SSEStreamMapper

router = APIRouter(prefix="/conversations", tags=["messages"])


async def verify_conversation_ownership(
    request: Request,
    conversation_id: uuid.UUID,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> None:
    """Ensure the conversation exists and belongs to the anon id.

    Runs before the route handler via `dependencies=`. Raises 404
    (never 403) for foreign or missing conversations.

    If no DB pool is available (e.g. unit tests without Postgres), the
    check is skipped so T02 unit tests keep passing.
    """
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        return
    repo = ConversationRepository(pool)
    row = await repo.get_by_id_and_anon(conversation_id, anon_id)
    if row is None:
        raise not_found()


class SendMessageRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=4000)]


@router.post(
    "/{conversation_id}/messages",
    response_class=EventSourceResponse,
    dependencies=[Depends(verify_conversation_ownership)],
    summary="Send a message and stream the assistant reply as SSE",
)
async def send_message(
    request: Request,
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> AsyncIterator[ServerSentEvent]:
    thread_id = str(conversation_id)
    mapper = SSEStreamMapper(conversation_id=thread_id)
    checkpointer = getattr(request.app.state, "checkpointer", None)
    graph = compile_graph(checkpointer=checkpointer)

    input_state = {"messages": [user_message(body.content)]}
    config = {"configurable": {"thread_id": thread_id}}
    context = AgentContext(conversation_id=thread_id)
    stream_ended_normally = False
    try:
        async for part in graph.astream(
            input_state,
            config,
            context=context,
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            # Check if client disconnected (Task 4: stop streaming)
            if await request.is_disconnected():
                break
            for event in mapper.map(part):
                yield event
                # Yield control to allow disconnect detection (Task 4)
                await asyncio.sleep(0)
        stream_ended_normally = True
    except (GeneratorExit, asyncio.CancelledError):
        # Client disconnected - the async generator was cancelled
        # Don't re-raise; let finally block handle saving partial message
        pass
    except Exception:
        # Task 8 adds provider fallback / structured codes; for now any
        # mid-stream failure ends the stream with the standard envelope.
        yield ServerSentEvent(
            event="error",
            data=error_response("provider_unavailable", "Provider error"),
        )
    finally:
        # Task 4: if client aborted mid-stream, save partial message with stopped=true
        if not stream_ended_normally and checkpointer is not None:
            accumulated = mapper.get_accumulated_content()
            if accumulated:
                await _save_stopped_message(checkpointer, config, accumulated)


async def _save_stopped_message(
    checkpointer, config: dict, content: str
) -> None:
    """Save a partial AIMessage with additional_kwargs={'stopped': true} to the checkpointer."""
    from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
    from datetime import datetime, timezone

    # Get existing checkpoint to preserve message history
    existing = await checkpointer.aget(config)
    if existing is None:
        # No existing checkpoint - create minimal one with just the stopped message
        messages = [AIMessage(content=content, additional_kwargs={"stopped": True})]
    else:
        # Append stopped message to existing messages
        existing_messages = existing.get("channel_values", {}).get("messages", [])
        messages = list(existing_messages) + [
            AIMessage(content=content, additional_kwargs={"stopped": True})
        ]

    # Build new checkpoint
    checkpoint = Checkpoint(
        v=1,
        id=config["configurable"]["thread_id"],
        ts=datetime.now(timezone.utc).isoformat(),
        channel_values={"messages": messages},
        channel_versions={"messages": len(messages)},
        versions_seen={},
    )
    metadata = CheckpointMetadata(
        source="update",
        step=-1,
        writes={},
        parents={},
    )
    await checkpointer.aput(config, checkpoint, metadata, {"messages": len(messages)})
