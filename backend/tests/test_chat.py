# Tests for chat endpoints
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
def auth_token(client):
    """Get auth token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


def test_chat_query(client, auth_token):
    """Test basic chat query."""
    response = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "What is the balance?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "₹" in data["response"]


def test_chat_query_about_transactions(client, auth_token):
    """Test chat about transactions."""
    response = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "Show water bills"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


def test_chat_query_unauthorized(client):
    """Test chat requires authentication."""
    response = client.post(
        "/api/chat/query",
        json={"query": "Hello"},
    )
    assert response.status_code == 401


def test_query_transactions(client, auth_token):
    """Test transaction querying via chat."""
    # First sync some transactions
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

    # First message
    response1 = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "Hello", "session_id": session_id},
    )
    assert response1.status_code == 200

    # Second message in same session
    response2 = client.post(
        "/api/chat/query",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"query": "And the balance?", "session_id": session_id},
    )
    assert response2.status_code == 200
    assert response2.json()["session_id"] == session_id
