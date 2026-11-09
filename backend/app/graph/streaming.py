"""Map LangGraph v2 stream parts to SSE events.

LangGraph `astream(..., stream_mode=["messages", "updates"], version="v2")`
yields typed dicts:

    {"type": "messages", "ns": (...), "data": (AIMessageChunk, metadata)}
    {"type": "updates",  "ns": (...), "data": {"agent": {"messages": [AIMessage]}}}

`SSEStreamMapper` turns those into FastAPI `ServerSentEvent`s with the
payload shapes from Docs/TECH_DESIGN.md §4:

    message_start {"message_id", "conversation_id"}
    token         {"delta"}
    message_end   {"message_id", "finish_reason", "usage"}

Events carry stable LangChain message ids, which the frontend uses as
React keys. Tool events (`tool_start`/`tool_end`) land in Task 7.
"""
from __future__ import annotations

from typing import Any

from fastapi.sse import ServerSentEvent
from langchain_core.messages import AIMessage


def _sse(event: str, data: dict[str, Any]) -> ServerSentEvent:
    return ServerSentEvent(event=event, data=data)


class SSEStreamMapper:
    """Stateful mapper: one instance per streamed run.

    Sequence per run: message_start, token*, message_end. A run without
    streamed chunks (no `messages` parts) still gets start + end so the
    UI always receives a complete pair.
    """

    def __init__(self, conversation_id: str) -> None:
        self._conversation_id = conversation_id
        self._message_id: str | None = None
        self._started = False
        self._finished = False
        self._accumulated_content = ""

    def map(self, part: dict[str, Any]) -> list[ServerSentEvent]:
        """Translate one stream part into zero or more SSE events."""
        mode = part.get("type")
        if mode == "messages":
            return self._map_messages(part["data"])
        if mode == "updates":
            return self._map_updates(part["data"])
        return []  # unknown/future modes must not break the stream

    def _map_messages(self, data: Any) -> list[ServerSentEvent]:
        if not isinstance(data, tuple) or len(data) != 2:
            return []
        chunk, _metadata = data
        # Only plain text content becomes a token; tool-call argument
        # chunks come through as empty/non-string content (Task 7).
        content = chunk.content
        if not isinstance(content, str) or not content:
            return []

        events: list[ServerSentEvent] = []
        if not self._started:
            self._started = True
            self._message_id = chunk.id
            events.append(
                _sse(
                    "message_start",
                    {"message_id": chunk.id, "conversation_id": self._conversation_id},
                )
            )
        self._accumulated_content += content
        events.append(_sse("token", {"delta": content}))
        return events

    def _map_updates(self, data: Any) -> list[ServerSentEvent]:
        if not isinstance(data, dict) or self._finished:
            return []
        events: list[ServerSentEvent] = []
        for _node, delta in data.items():
            if not isinstance(delta, dict):
                continue
            for msg in delta.get("messages", []):
                if not isinstance(msg, AIMessage):
                    continue  # only assistant turns end the assistant stream
                if self._finished:
                    continue
                if not self._started:
                    self._started = True
                    self._message_id = msg.id
                    events.append(
                        _sse(
                            "message_start",
                            {
                                "message_id": msg.id,
                                "conversation_id": self._conversation_id,
                            },
                        )
                    )
                self._finished = True
                usage_meta = msg.usage_metadata or {}
                events.append(
                    _sse(
                        "message_end",
                        {
                            "message_id": msg.id,
                            "finish_reason": self._finish_reason(msg),
                            "usage": {
                                "input_tokens": usage_meta.get("input_tokens", 0),
                                "output_tokens": usage_meta.get("output_tokens", 0),
                            },
                        },
                    )
                )
        return events

    @staticmethod
    def _finish_reason(msg: AIMessage) -> str:
        # Stopped partials are saved with additional_kwargs={"stopped": True}
        # (see Docs/TECH_DESIGN.md §Conventions and Stop data flow).
        if msg.additional_kwargs.get("stopped"):
            return "stopped"
        return msg.response_metadata.get("finish_reason") or "stop"

    def get_accumulated_content(self) -> str:
        """Return the accumulated token content for this stream."""
        return self._accumulated_content
