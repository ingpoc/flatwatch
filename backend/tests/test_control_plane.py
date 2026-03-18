# Tests for entitlement and agent session control plane
import json
import os

import pytest
from fastapi.testclient import TestClient

from app.database import get_db_path, init_db
from app.main import app


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


def test_entitlement_snapshot_returns_subscription_and_usage(client, resident_token):
    response = client.get(
        "/api/entitlements/me?app=flatwatch",
        headers={"Authorization": f"Bearer {resident_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["subscription_status"] == "active"
    assert payload["agent_access"] is True
    assert payload["plan_tier"] == "pilot"
    assert payload["usage"]["requests_limit"] == 100


def test_inactive_subscription_blocks_session_creation(client):
    signup = client.post(
        "/api/auth/signup",
        json={"email": "newuser@flatwatch.test", "password": "any", "name": "New User"},
    )
    token = signup.json()["access_token"]

    response = client.post(
        "/api/agent/flatwatch/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"task_type": "chat_guard", "context": {"surface": "chat"}},
    )

    assert response.status_code == 403
    assert "subscription" in response.json()["detail"].lower()


def test_agent_session_message_stream_emits_result_and_usage(client, resident_token):
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
