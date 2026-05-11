# Tests for audit API endpoints
import os

import pytest
from fastapi.testclient import TestClient

from app.audit import AuditAction, log_action
from app.database import get_db_path, init_db
from app.main import app


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
def admin_token(client):
    """Get admin token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


@pytest.fixture
def resident_token(client):
    """Get resident token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "resident@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


def test_admin_can_list_audit_logs(client, admin_token):
    """Test admins can view audit logs."""
    log_action(AuditAction.CHALLENGE_CREATE, 2, "Challenge created", target_id=42, target_type="challenge")

    response = client.get(
        "/api/audit/logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert any(entry["action"] == "challenge_create" for entry in response.json())


def test_resident_cannot_list_audit_logs(client, resident_token):
    """Test residents cannot view audit logs."""
    response = client.get(
        "/api/audit/logs",
        headers={"Authorization": f"Bearer {resident_token}"},
    )

    assert response.status_code == 403


def test_admin_can_filter_audit_logs(client, admin_token):
    """Test audit log filters are exposed through the admin endpoint."""
    log_action(AuditAction.CHALLENGE_CREATE, 2, "Challenge created", target_id=42, target_type="challenge")
    log_action(AuditAction.TRANSACTION_CREATE, 1, "Transaction created", target_id=7, target_type="transaction")

    response = client.get(
        "/api/audit/logs?action=challenge_create&target_id=42&limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["action"] == "challenge_create"
    assert logs[0]["target_id"] == 42
    assert logs[0]["target_type"] == "challenge"


def test_invalid_audit_action_filter_returns_400(client, admin_token):
    """Test invalid audit action filters do not raise internal errors."""
    response = client.get(
        "/api/audit/logs?action=unknown_action",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400


def test_admin_can_view_audit_stats(client, admin_token):
    """Test audit stats endpoint supports admin review surfaces."""
    log_action(AuditAction.CHALLENGE_RESOLVE, 1, "Challenge resolved", target_id=42, target_type="challenge")

    response = client.get(
        "/api/audit/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["by_action"]["challenge_resolve"] >= 1
