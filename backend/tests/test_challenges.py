# Tests for challenges endpoints
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db_path


@pytest.fixture(autouse=True)
def setup_database():
    """Initialize database before each test."""
    init_db()
    yield
    import os
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


def test_create_challenge(client, resident_token, admin_token):
    """Test creating a challenge."""
    # First sync a transaction
    client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Create challenge
    response = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"transaction_id": 1, "reason": "Amount seems incorrect"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data


def test_create_challenge_invalid_txn(client, resident_token):
    """Test challenge on non-existent transaction."""
    response = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {resident_token}"},
        json={"transaction_id": 999, "reason": "Test"},
    )
    assert response.status_code == 404


def test_list_challenges(client, resident_token):
    """Test listing challenges."""
    response = client.get(
        "/api/challenges",
        headers={"Authorization": f"Bearer {resident_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_resolve_challenge(client, admin_token):
    """Test resolving a challenge."""
    # First create a challenge
    client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    challenge_response = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"transaction_id": 1, "reason": "Verify this"},
    )
    challenge_id = challenge_response.json()["id"]

    # Resolve it
    response = client.put(
        f"/api/challenges/{challenge_id}/resolve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"evidence": "Receipt uploaded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "resolved" in data["message"].lower()


def test_reject_challenge(client, admin_token):
    """Test rejecting a challenge."""
    challenge_response = client.post(
        "/api/challenges",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"transaction_id": 1, "reason": "Test"},
    )
    challenge_id = challenge_response.json()["id"]

    response = client.put(
        f"/api/challenges/{challenge_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Invalid challenge"},
    )
    assert response.status_code == 200


def test_pending_count(client, admin_token):
    """Test getting pending challenge count."""
    response = client.get(
        "/api/challenges/pending/count",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "pending_over_48h" in data


def test_challenge_stats(client, admin_token):
    """Test challenge statistics."""
    response = client.get(
        "/api/challenges/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "by_status" in data
