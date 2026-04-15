# Tests for authentication endpoints
import pytest
import os
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db_path


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


def test_login_success(client):
    """Test successful login."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@flatwatch.test", "password": "any-password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["email"] == "admin@flatwatch.test"
    assert data["user"]["role"] == "super_admin"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@test.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_signup_new_user(client):
    """Test user signup."""
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "newuser@test.com",
            "password": "password123",
            "name": "New User",
            "flat_number": "C-201",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@test.com"
    assert data["user"]["role"] == "resident"


def test_signup_existing_user(client):
    """Test signup with existing email."""
    response = client.post(
        "/api/auth/signup",
        json={"email": "admin@flatwatch.test", "password": "any"},
    )
    assert response.status_code == 400


def test_get_me_valid_token(client):
    """Test getting current user with valid token."""
    # First login
    login_response = client.post(
        "/api/auth/login",
        json={"email": "resident@flatwatch.test", "password": "any"},
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "resident@flatwatch.test"


def test_get_me_invalid_token(client):
    """Test getting current user with invalid token."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_verify_token_valid(client):
    """Test token verification."""
    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@flatwatch.test", "password": "any"},
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
