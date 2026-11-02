"""POST /conversations/{id}/messages – single-turn SSE streaming chat.

Task 2 scope: one user message in, tokens stream out. Ownership
checks (404), run locks, rate limits and persistence land in
Tasks 3 / 4 / 8 – this slice only proves the stream end-to-end and
stays DB-free (works with LLM_PROVIDER=fake, no .env, no Postgres).
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field

from app.core.anon_id import get_anon_id
from app.core.errors import error_response
from app.graph.build import compile_graph
from app.graph.nodes import AgentContext, user_message
from app.graph.streaming import SSEStreamMapper

router = APIRouter(prefix="/conversations", tags=["messages"])


class SendMessageRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=4000)]


@router.post(
    "/{conversation_id}/messages",
    response_class=EventSourceResponse,
    summary="Send a message and stream the assistant reply as SSE",
)
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    anon_id: Annotated[str, Depends(get_anon_id)],
) -> AsyncIterator[ServerSentEvent]:
    thread_id = str(conversation_id)
    mapper = SSEStreamMapper(conversation_id=thread_id)
    graph = compile_graph()

    input_state = {"messages": [user_message(body.content)]}
    config = {"configurable": {"thread_id": thread_id}}
    context = AgentContext(conversation_id=thread_id)
    try:
        async for part in graph.astream(
            input_state,
            config,
            context=context,
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            for event in mapper.map(part):
                yield event
    except Exception:
        # Task 8 adds provider fallback / structured codes; for now any
        # mid-stream failure ends the stream with the standard envelope.
        yield ServerSentEvent(
            event="error",
            data=error_response("provider_unavailable", "Provider error"),
        )
