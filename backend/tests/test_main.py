# Tests for FlatWatch FastAPI backend
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db_path, get_db_connection


@pytest.fixture(autouse=True)
def setup_database():
    """Initialize database before each test."""
    init_db()
    yield
    # Clean up after test
    import os
    db_path = get_db_path()
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "FlatWatch API"
    assert "version" in data


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "unhealthy"]
    assert "database" in data
    assert "version" in data


def test_database_initialized():
    """Test database tables are created."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "transactions" in tables
    assert "users" in tables
    assert "challenges" in tables


def test_database_file_created():
    """Test database file is created."""
    db_path = get_db_path()
    init_db()
    assert db_path.exists()


def test_init_db_migrates_legacy_sqlite_users_table():
    """Test older local SQLite databases receive auth hardening columns."""
    db_path = get_db_path()
    if db_path.exists():
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firebase_uid TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'resident',
                flat_number TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    init_db()

    conn = get_db_connection()
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    seeded = conn.execute(
        "SELECT password_hash, token_version FROM users WHERE email = ?",
        ("admin@flatwatch.test",),
    ).fetchone()
    conn.close()

    assert "password_hash" in columns
    assert "token_version" in columns
    assert seeded["password_hash"]
    assert seeded["token_version"] == 0


def test_cors_headers(client):
    """Test CORS middleware is configured."""
    response = client.get("/", headers={"Origin": "http://localhost:43105"})
    assert response.status_code == 200
