# Tests for chat endpoints
import os

import pytest
from fastapi.testclient import TestClient

from app.control_plane import AgentRuntimeSnapshot, UsageSnapshot
from app.main import app
from app.database import init_db, get_db_path


def make_runtime_snapshot(**overrides):
    payload = {
        "app_id": "flatwatch",
        "auth_mode": "local_cli",
        "model": "claude-haiku-4-5-20251001",
        "runtime_available": True,
        "agent_access": True,
        "trust_state": "manual_review",
        "trust_required_for_write": True,
        "mode": "read_only",
        "usage": UsageSnapshot(
            requests_used=0,
            requests_limit=0,
            period_start="2026-01-01T00:00:00+00:00",
            period_end="2026-02-01T00:00:00+00:00",
            estimated_cost_usd=0.0,
        ),
        "allowed_capabilities": [
            "transactions_query",
            "receipts_metadata",
            "challenges_summary",
            "bylaw_lookup",
        ],
        "blocked_reason": "Verification is still under manual review.",
    }
    payload.update(overrides)
    return AgentRuntimeSnapshot(**payload)


@pytest.fixture(autouse=True)
def setup_database():
    """Initialize database before each test."""
    init_db()
    yield
    db_path = get_db_path()
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Get auth token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


@pytest.fixture(autouse=True)
def patch_runtime(monkeypatch):
    snapshot = make_runtime_snapshot()
    monkeypatch.setattr("app.routers.chat.build_runtime_snapshot", lambda *args, **kwargs: snapshot)

    async def fake_stream_agent_response(session, prompt, runtime_snapshot):
        yield {
            "type": "result",
            "content": f"Handled: {prompt}",
            "sdk_session_id": "sdk-chat-1",
            "estimated_cost_usd": 0.0042,
            "timestamp": 1,
        }

    monkeypatch.setattr("app.routers.chat.stream_agent_response", fake_stream_agent_response)


def test_chat_query(client, auth_token):
    """Test basic chat query."""
    response = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "What is the balance?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Handled: What is the balance?"


def test_chat_query_about_transactions(client, auth_token):
    """Test chat about transactions."""
    response = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "Show water bills"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Handled: Show water bills"


def test_chat_query_unauthorized(client):
    """Test chat requires authentication."""
    response = client.post(
        "/api/chat/query",
        json={"query": "Hello"},
    )
    assert response.status_code == 401


def test_query_transactions(client, auth_token):
    """Test transaction querying via chat."""
    client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    response = client.post(
        "/api/chat/query-transactions",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "Show recent inflows"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "transactions" in data
    assert "count" in data


def test_chat_with_session(client, auth_token):
    """Test chat maintains session context."""
    session_id = "test_session_123"

    response1 = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "Hello", "session_id": session_id},
    )
    assert response1.status_code == 200

    response2 = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "And the balance?", "session_id": session_id},
    )
    assert response2.status_code == 200
    assert response2.json()["session_id"] == session_id
