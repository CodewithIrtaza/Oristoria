"""T03 integration tests: conversation persistence across app restarts.

Test-first entry point (Docs/TASKS.md T03):
    backend/tests/integration/test_persistence.py::test_conversation_survives_app_restart
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

ANON_A = "11111111-1111-1111-1111-111111111111"
ANON_B = "22222222-2222-2222-2222-222222222222"


def _open_app() -> Iterator[TestClient]:
    """Each call builds a *fresh* app instance (simulates a restart)."""
    from app.main import create_app

    application = create_app()
    with TestClient(application) as client:
        yield client


def _send_message(client: TestClient, conversation_id: str, content: str) -> None:
    """POST one message and drain the SSE stream to completion."""
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": content},
        headers={"X-Anon-Id": ANON_A},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_conversation_survives_app_restart():
    """Create conversation, send a message, restart the app, history intact."""
    # -- first app instance ------------------------------------------------
    client = _open_app()
    created = client.post(
        "/api/conversations",
        json={},
        headers={"X-Anon-Id": ANON_A},
    )
    assert created.status_code == 201, created.text
    conversation_id = created.json()["id"]

    _send_message(client, conversation_id, "Remember the word: banana")
    client.close()  # full teardown: pool closed, graph dropped

    # -- app restart -------------------------------------------------------
    client = _open_app()
    listed = client.get(
        "/api/conversations", headers={"X-Anon-Id": ANON_A}
    )
    assert listed.status_code == 200
    assert any(item["id"] == conversation_id for item in listed.json())

    detail = client.get(
        f"/api/conversations/{conversation_id}",
        headers={"X-Anon-Id": ANON_A},
    )
    assert detail.status_code == 200, detail.text
    messages = detail.json()["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant"]
    assert messages[0]["content"] == "Remember the word: banana"
    assert messages[1]["content"] != ""
    client.close()


def test_foreign_anon_id_gets_404_not_403():
    """Another X-Anon-Id must never access a foreign conversation."""
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        created = client.post(
            "/api/conversations", json={}, headers={"X-Anon-Id": ANON_A}
        )
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        # Foreign anon: all read paths must be 404 (never 403).
        assert (
            client.get(
                f"/api/conversations/{conversation_id}",
                headers={"X-Anon-Id": ANON_B},
            ).status_code
            == 404
        )
        assert (
            client.get(
                "/api/conversations", headers={"X-Anon-Id": ANON_B}
            ).status_code
            == 200
        )

        # Unknown id must look identical to "foreign".
        assert (
            client.get(
                f"/api/conversations/{uuid.uuid4()}",
                headers={"X-Anon-Id": ANON_A},
            ).status_code
            == 404
        )


def test_messages_post_rejects_foreign_or_missing_conversation():
    """The messages route must 404 for foreign / nonexistent threads."""
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        created = client.post(
            "/api/conversations", json={}, headers={"X-Anon-Id": ANON_A}
        )
        conversation_id = created.json()["id"]

        foreign = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "hi"},
            headers={"X-Anon-Id": ANON_B},
        )
        assert foreign.status_code == 404

        missing = client.post(
            f"/api/conversations/{uuid.uuid4()}/messages",
            json={"content": "hi"},
            headers={"X-Anon-Id": ANON_A},
        )
        assert missing.status_code == 404
