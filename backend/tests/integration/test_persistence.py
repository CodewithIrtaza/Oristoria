"""T03 integration tests: conversation persistence across app restarts.

Test-first entry point (Docs/TASKS.md T03):
    backend/tests/integration/test_persistence.py::test_conversation_survives_app_restart
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

# On Windows, psycopg 3's async pool cannot run on the ProactorEventLoop
# that anyio/TestClient uses by default. Force SelectorEventLoop so the
# lifespan (pool open + AsyncPostgresSaver.setup) works under TestClient.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _make_client() -> TestClient:
    """Build a TestClient whose event loop is psycopg-compatible."""
    from app.main import create_app

    application = create_app()
    return TestClient(application, backend_options={"loop_factory": asyncio.SelectorEventLoop})


@contextmanager
def _open_app() -> Iterator[TestClient]:
    """Each call builds a *fresh* app instance (simulates a restart)."""
    with _make_client() as client:
        yield client


ANON_A = "11111111-1111-1111-1111-111111111111"
ANON_B = "22222222-2222-2222-2222-222222222222"


def _send_message(client: TestClient, conversation_id: str, content: str) -> None:
    """POST one message and drain the SSE stream to completion."""
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": content},
        headers={"X-Anon-Id": ANON_A},
    )
    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers["content-type"]


def test_conversation_survives_app_restart():
    """Create conversation, send a message, restart the app, history intact."""
    # -- first app instance ------------------------------------------------
    with _open_app() as client:
        created = client.post(
            "/api/conversations",
            json={},
            headers={"X-Anon-Id": ANON_A},
        )
        assert created.status_code == 201, created.text
        conversation_id = created.json()["id"]

        _send_message(client, conversation_id, "Remember the word: banana")
        # client context exits -> pool closed, graph dropped (simulates restart)

    # -- app restart -------------------------------------------------------
    with _open_app() as client:
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


def test_foreign_anon_id_gets_404_not_403():
    """Another X-Anon-Id must never access a foreign conversation."""
    with _make_client() as client:
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
    with _make_client() as client:
        created = client.post(
            "/api/conversations", json={}, headers={"X-Anon-Id": ANON_A}
        )
        assert created.status_code == 201
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
