"""Unit tests for POST /api/conversations/{id}/messages (SSE streaming)."""
import json
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ANON = "11111111-1111-1111-1111-111111111111"


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    """Parse the wire format into (event, data) pairs."""
    events: list[tuple[str, dict]] = []
    event_name: str | None = None
    for line in body.splitlines():
        if line.startswith("event: "):
            event_name = line[len("event: ") :]
        elif line.startswith("data: ") and event_name is not None:
            events.append((event_name, json.loads(line[len("data: ") :])))
    return events


def test_send_message_streams_sse_sequence():
    """200 text/event-stream with message_start -> token* -> message_end."""
    conv = uuid.uuid4()
    with client.stream(
        "POST",
        f"/api/conversations/{conv}/messages",
        json={"content": "hi"},
        headers={"X-Anon-Id": ANON},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = "".join(chunk.decode() for chunk in response.iter_raw())
    events = _parse_sse(body)
    names = [name for name, _ in events]
    assert names[0] == "message_start"
    assert names[-1] == "message_end"
    assert "token" in names
    assert all(name in {"message_start", "token", "message_end"} for name in names)
    delta = "".join(data["delta"] for name, data in events if name == "token")
    assert delta == "Hello! I am a fake LLM for testing."
    start = events[0][1]
    end = events[-1][1]
    assert start["conversation_id"] == str(conv)
    assert start["message_id"] == end["message_id"]


def test_send_message_requires_anon_id():
    """Missing X-Anon-Id is rejected (dependency raises 422)."""
    conv = uuid.uuid4()
    response = client.post(
        f"/api/conversations/{conv}/messages", json={"content": "hi"}
    )
    assert response.status_code == 422


def test_send_message_rejects_empty_and_oversized_content():
    conv = uuid.uuid4()
    response = client.post(
        f"/api/conversations/{conv}/messages",
        json={"content": ""},
        headers={"X-Anon-Id": ANON},
    )
    assert response.status_code == 422
    response = client.post(
        f"/api/conversations/{conv}/messages",
        json={"content": "x" * 4001},
        headers={"X-Anon-Id": ANON},
    )
    assert response.status_code == 422


def test_send_message_rejects_bad_conversation_id():
    """Non-UUID conversation id must not reach the graph."""
    response = client.post(
        "/api/conversations/not-a-uuid/messages",
        json={"content": "hi"},
        headers={"X-Anon-Id": ANON},
    )
    assert response.status_code == 422
