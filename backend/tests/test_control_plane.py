# Tests for runtime snapshots and agent session control plane
import json
import os

import pytest
from fastapi.testclient import TestClient

from app.control_plane import APP_CAPABILITIES, AgentRuntimeSnapshot, UsageSnapshot, build_runtime_snapshot
from app.database import get_db_path, init_db
from app.main import app


def make_runtime_snapshot(**overrides):
    payload = {
        "app_id": "flatwatch",
        "auth_mode": "api_key",
        "model": "composer-2.5",
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
    init_db()
    yield
    db_path = get_db_path()
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def resident_token(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "resident@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


def test_runtime_snapshot_returns_auth_mode_and_usage(client, resident_token, monkeypatch):
    snapshot = make_runtime_snapshot()
    monkeypatch.setattr("app.routers.control_plane.build_runtime_snapshot", lambda *args, **kwargs: snapshot)

    response = client.get(
        "/api/agent/runtime?app=flatwatch",
        headers={"Authorization": f"Bearer {resident_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["auth_mode"] == "api_key"
    assert payload["runtime_available"] is True
    assert payload["mode"] == "read_only"
    assert payload["usage"]["requests_used"] == 0


@pytest.mark.parametrize(
    "trust_state",
    [
        "no_identity",
        "identity_present_unverified",
        "verified",
        "manual_review",
        "revoked_or_blocked",
    ],
)
def test_flatwatch_runtime_snapshot_trust_fixture_matrix(monkeypatch, trust_state):
    from app.runtime_config import AgentRuntimePolicy

    monkeypatch.setattr(
        "app.control_plane.resolve_runtime_policy",
        lambda request=None: AgentRuntimePolicy(
            runtime_available=True,
            auth_mode="api_key",
            model="composer-2.5",
            blocked_reason=None,
        ),
    )

    snapshot = build_runtime_snapshot(
        subject_id=f"resident-{trust_state}",
        app_id="flatwatch",
        trust_state=trust_state,
        trust_reason=f"Trust reason for {trust_state}.",
    )

    assert snapshot.runtime_available is True
    assert snapshot.agent_access is True
    assert snapshot.trust_state == trust_state
    assert snapshot.trust_required_for_write is True

    if trust_state == "verified":
        assert snapshot.mode == "full"
        assert snapshot.blocked_reason is None
        assert snapshot.allowed_capabilities == (
            APP_CAPABILITIES["flatwatch"]["read"] + APP_CAPABILITIES["flatwatch"]["write"]
        )
        return

    assert snapshot.mode == "read_only"
    assert snapshot.blocked_reason == f"Trust reason for {trust_state}."
    assert snapshot.allowed_capabilities == APP_CAPABILITIES["flatwatch"]["read"]
    for write_capability in APP_CAPABILITIES["flatwatch"]["write"]:
        assert write_capability not in snapshot.allowed_capabilities


def test_runtime_unavailable_blocks_session_creation(client, resident_token, monkeypatch):
    snapshot = make_runtime_snapshot(
        auth_mode="unavailable",
        runtime_available=False,
        agent_access=False,
        mode="blocked",
        allowed_capabilities=[],
        blocked_reason="Cursor runtime unavailable in this environment.",
    )
    monkeypatch.setattr("app.routers.control_plane.build_runtime_snapshot", lambda *args, **kwargs: snapshot)

    response = client.post(
        "/api/agent/flatwatch/sessions",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"task_type": "chat_guard", "context": {"surface": "chat"}},
    )

    assert response.status_code == 403
    assert "runtime unavailable" in response.json()["detail"].lower()


def test_agent_session_message_stream_emits_result_and_usage(client, resident_token, monkeypatch):
    snapshot = make_runtime_snapshot()
    monkeypatch.setattr("app.routers.control_plane.build_runtime_snapshot", lambda *args, **kwargs: snapshot)

    async def fake_stream_agent_response(session, prompt, runtime_snapshot):
        yield {
            "type": "init",
            "session_id": session["session_id"],
            "sdk_session_id": session.get("sdk_session_id"),
            "mode": session["mode"],
        }
        yield {
            "type": "result",
            "content": f"Handled: {prompt}",
            "sdk_session_id": "sdk-session-1",
            "estimated_cost_usd": 0.0125,
            "timestamp": 1,
        }

    monkeypatch.setattr("app.routers.control_plane.stream_agent_response", fake_stream_agent_response)

    session = client.post(
        "/api/agent/flatwatch/sessions",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"task_type": "chat_guard", "context": {"surface": "chat"}},
    )
    assert session.status_code == 200
    session_payload = session.json()
    assert session_payload["mode"] == "read_only"

    response = client.post(
        "/api/agent/flatwatch/messages",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"session_id": session_payload["session_id"], "message": "What is the balance?"},
    )

    assert response.status_code == 200
    events = []
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        data = line.removeprefix("data: ").strip()
        if not data or data == "[DONE]":
            continue
        events.append(json.loads(data))

    event_types = [event["type"] for event in events]
    assert "init" in event_types
    assert "result" in event_types
    assert "usage" in event_types
