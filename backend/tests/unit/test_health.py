"""Unit tests for the /api/health endpoint.

Tests the hello-world endpoint without any DB or network connections.
This is the ONE required passing test for the scaffold.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    """GET /api/health must return 200 with {\"status\": \"ok\"}."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_require_anon_id():
    """Health endpoint is exempt from X-Anon-Id – no header → still 200."""
    response = client.get("/api/health", headers={})
    assert response.status_code == 200


def test_health_does_not_touch_database(monkeypatch):
    """T01 guard: /api/health is liveness-only — must not open DB connections."""
    import psycopg
    import psycopg_pool

    def _fail(*args, **kwargs):
        raise AssertionError("/api/health must not touch the database")

    monkeypatch.setattr(psycopg, "connect", _fail)
    monkeypatch.setattr(psycopg_pool, "AsyncConnectionPool", _fail)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready():
    """GET /api/ready must return 200 with {\"status\": \"ready\"} in the scaffold."""
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
