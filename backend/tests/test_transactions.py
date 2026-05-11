# Tests for transactions endpoints
import hashlib
import hmac
import json
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


@pytest.fixture
def auth_token(client):
    """Get auth token."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@flatwatch.test", "password": "any"},
    )
    return response.json()["access_token"]


def test_list_transactions_empty(client, auth_token):
    """Test listing transactions when empty."""
    response = client.get(
        "/api/transactions",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_list_transactions_unauthorized(client):
    """Test listing transactions without auth."""
    response = client.get("/api/transactions")
    assert response.status_code == 401


def test_trigger_sync(client, auth_token):
    """Test triggering transaction sync."""
    response = client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "saved" in data
    assert data["saved"] >= 0


def test_get_summary(client, auth_token):
    """Test getting financial summary."""
    # First sync some transactions
    client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    response = client.get(
        "/api/transactions/summary",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "balance" in data
    assert "total_inflow" in data
    assert "total_outflow" in data


def test_create_transaction(client, auth_token):
    """Test creating a transaction."""
    response = client.post(
        "/api/transactions",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "amount": 100.0,
            "transaction_type": "inflow",
            "description": "Test transaction",
            "vpa": "test@upi",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 100.0
    assert data["description"] == "Test transaction"


def test_filter_transactions_by_type(client, auth_token):
    """Test filtering transactions by type."""
    # Sync some transactions
    client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Filter by inflow
    response = client.get(
        "/api/transactions?txn_type=inflow",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    for txn in data:
        assert txn["transaction_type"] == "inflow"


def test_sync_saves_transactions(client, auth_token):
    """Test that sync saves new transactions."""
    from app.database import get_db_connection

    # Clear existing transactions
    conn = get_db_connection()
    conn.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()

    # Trigger sync
    response = client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] > 0

    # Verify transactions in DB
    conn = get_db_connection()
    cursor = conn.execute("SELECT COUNT(*) as count FROM transactions")
    count = cursor.fetchone()["count"]
    conn.close()
    assert count > 0


def test_razorpay_webhook_requires_valid_signature(client, monkeypatch):
    """Test Razorpay webhook rejects invalid signatures."""
    monkeypatch.setenv("FLATWATCH_RAZORPAY_WEBHOOK_SECRET", "webhook-secret")
    payload = {
        "source_transaction_id": "pay_123",
        "amount": 1200.0,
        "transaction_type": "inflow",
        "description": "Maintenance payment",
        "vpa": "resident@upi",
    }

    response = client.post(
        "/api/transactions/webhooks/razorpay",
        content=json.dumps(payload),
        headers={
            "X-Razorpay-Signature": "invalid",
            "Idempotency-Key": "event-123",
        },
    )

    assert response.status_code == 401


def test_razorpay_webhook_ingests_once_with_idempotency(client, monkeypatch):
    """Test signed Razorpay webhook stores source reference and de-duplicates."""
    monkeypatch.setenv("FLATWATCH_RAZORPAY_WEBHOOK_SECRET", "webhook-secret")
    payload = {
        "source_transaction_id": "pay_123",
        "amount": 1200.0,
        "transaction_type": "inflow",
        "description": "Maintenance payment",
        "vpa": "resident@upi",
    }
    body = json.dumps(payload)
    signature = hmac.new(b"webhook-secret", body.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "X-Razorpay-Signature": signature,
        "Idempotency-Key": "event-123",
    }

    response = client.post(
        "/api/transactions/webhooks/razorpay",
        content=body,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"
    assert data["source_transaction_id"] == "pay_123"

    duplicate = client.post(
        "/api/transactions/webhooks/razorpay",
        content=body,
        headers=headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "duplicate"
    assert duplicate.json()["transaction_id"] == data["transaction_id"]

    conn = get_db_connection()
    event_count = conn.execute("SELECT COUNT(*) as count FROM payment_ingestion_events").fetchone()["count"]
    txn_count = conn.execute("SELECT COUNT(*) as count FROM transactions").fetchone()["count"]
    event = conn.execute(
        "SELECT provider, source_transaction_id, raw_payload FROM payment_ingestion_events"
    ).fetchone()
    conn.close()

    assert event_count == 1
    assert txn_count == 1
    assert event["provider"] == "razorpay"
    assert event["source_transaction_id"] == "pay_123"
    assert json.loads(event["raw_payload"])["description"] == "Maintenance payment"


def test_ingestion_status_reconcile_retry_and_public_dashboard(client, auth_token, monkeypatch):
    """Test admin sync status surfaces and public aggregate privacy view."""
    monkeypatch.setenv("FLATWATCH_RAZORPAY_WEBHOOK_SECRET", "webhook-secret")
    payload = {
        "source_transaction_id": "pay_status",
        "amount": 1500.0,
        "transaction_type": "inflow",
        "description": "Maintenance payment",
        "vpa": "private@upi",
    }
    body = json.dumps(payload)
    signature = hmac.new(b"webhook-secret", body.encode("utf-8"), hashlib.sha256).hexdigest()

    response = client.post(
        "/api/transactions/webhooks/razorpay",
        content=body,
        headers={
            "X-Razorpay-Signature": signature,
            "Idempotency-Key": "event-status",
        },
    )
    assert response.status_code == 200

    status_response = client.get(
        "/api/transactions/ingestion/status",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["by_provider_status"][0]["status"] == "ingested"

    retry_response = client.post(
        "/api/transactions/ingestion/event-status/retry",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "retry_pending"

    reconcile_response = client.post(
        "/api/transactions/ingestion/reconcile",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert reconcile_response.status_code == 200
    assert reconcile_response.json()["unmatched_count"] == 0

    public_response = client.get("/api/transactions/public/dashboard")
    assert public_response.status_code == 200
    public_data = public_response.json()
    assert public_data["total_inflow"] == 1500.0
    assert "private@upi" not in json.dumps(public_data)
