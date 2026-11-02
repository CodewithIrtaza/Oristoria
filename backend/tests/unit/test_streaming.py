"""Unit tests for the v2 stream parts -> SSE event mapper.

Uses recorded fixture parts shaped exactly like LangGraph v2 stream parts:
    {"type": "messages", "ns": (...), "data": (AIMessageChunk, metadata)}
    {"type": "updates",  "ns": (...), "data": {"agent": {"messages": [AIMessage]}}}
(recorded from a FakeListChatModel probe; see Docs/TASKS.md T02).
"""
from langchain_core.messages import AIMessage, AIMessageChunk
from fastapi.sse import ServerSentEvent

from app.graph.streaming import SSEStreamMapper

RUN_ID = "lc_run--01a19c0a-651f-72e8-a7c0-22e6f7206229"
META = {"langgraph_node": "agent", "thread_id": "conv-1"}


def _messages_part(content: str) -> dict:
    return {
        "type": "messages",
        "ns": (),
        "data": (AIMessageChunk(content=content, id=RUN_ID), META),
    }


def _updates_part(content: str, **msg_kwargs) -> dict:
    msg = AIMessage(content=content, id=RUN_ID, **msg_kwargs)
    return {
        "type": "updates",
        "ns": (),
        "data": {"agent": {"messages": [msg]}},
    }


def _names(events: list[ServerSentEvent]) -> list[str]:
    return [e.event for e in events]


def test_stream_mapper_emits_expected_sse_sequence():
    """message_start, delta tokens, message_end – in that order."""
    mapper = SSEStreamMapper(conversation_id="conv-1")
    parts = [
        _messages_part("Hello"),
        _messages_part(","),
        _messages_part(" world!"),
        _updates_part("Hello, world!"),
    ]
    events: list[ServerSentEvent] = []
    for part in parts:
        events.extend(mapper.map(part))

    assert _names(events) == [
        "message_start",
        "token",
        "token",
        "token",
        "message_end",
    ]

    start = events[0]
    assert start.data == {"message_id": RUN_ID, "conversation_id": "conv-1"}

    tokens = "".join(e.data["delta"] for e in events if e.event == "token")
    assert tokens == "Hello, world!"

    end = events[-1]
    assert end.data["message_id"] == RUN_ID
    assert end.data["finish_reason"] == "stop"
    assert end.data["usage"] == {"input_tokens": 0, "output_tokens": 0}


def test_stream_mapper_skips_empty_and_non_text_chunks():
    """Empty chunks (e.g. between model runs) must not emit token events."""
    mapper = SSEStreamMapper(conversation_id="conv-1")
    parts = [
        _messages_part(""),  # empty content -> no token, no message_start
        _messages_part("Hi"),
    ]
    events = mapper.map(parts[0]) + mapper.map(parts[1])
    assert _names(events) == ["message_start", "token"]
    assert events[0].data == {"message_id": RUN_ID, "conversation_id": "conv-1"}
    assert events[1].data == {"delta": "Hi"}


def test_stream_mapper_unknown_part_type_is_ignored():
    """Robustness: future/unknown modes must not crash the stream."""
    mapper = SSEStreamMapper(conversation_id="conv-1")
    events = mapper.map({"type": "something_new", "ns": (), "data": {"odd": 1}})
    assert events == []


def test_stream_mapper_reports_stopped_finish_reason():
    """Interrupted partial messages carry {'stopped': True} -> finish_reason 'stopped'."""
    mapper = SSEStreamMapper(conversation_id="conv-1")
    events = mapper.map(_messages_part("partial an"))
    events.extend(
        mapper.map(
            _updates_part(
                "partial an",
                additional_kwargs={"stopped": True},
                response_metadata={"finish_reason": "stop"},
            )
        )
    )
    assert _names(events) == ["message_start", "token", "message_end"]
    assert events[-1].data["finish_reason"] == "stopped"


def test_stream_mapper_handles_run_without_streamed_tokens():
    """A run that emits no messages-mode chunks still gets start + end."""
    mapper = SSEStreamMapper(conversation_id="conv-1")
    events = mapper.map(_updates_part("full reply"))
    assert _names(events) == ["message_start", "message_end"]
    assert events[-1].data["finish_reason"] == "stop"
