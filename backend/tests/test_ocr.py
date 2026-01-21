# Tests for OCR endpoints
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db_path
from app.routers.receipts import UPLOAD_DIR
from app.ocr import extract_receipt_data, match_transaction


@pytest.fixture(autouse=True)
def setup_database():
    """Initialize database before each test."""
    init_db()
    yield
    # Clean up
    import os
    db_path = get_db_path()
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture(autouse=True)
def setup_upload_dir():
    """Ensure upload directory exists."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Clean up
    for file in UPLOAD_DIR.iterdir():
        if file.is_file():
            file.unlink()


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


@pytest.mark.asyncio
async def test_extract_receipt_data():
    """Test OCR data extraction."""
    result = await extract_receipt_data("water_bill.pdf")
    assert result["amount"] == 8500.0
    assert result["vendor"] == "Water Supply Co"
    assert result["confidence"] > 0.8


@pytest.mark.asyncio
async def test_match_transaction():
    """Test transaction matching."""
    transactions = [
        {"amount": 8500.0, "description": "Water bill payment", "timestamp": "2025-01-20T10:00:00"},
        {"amount": 6000.0, "description": "Maintenance", "timestamp": "2025-01-15T10:00:00"},
    ]
    receipt_data = {"amount": 8500.0, "date": "2025-01-20", "vendor": "Water Supply Co"}

    match = await match_transaction(receipt_data, transactions)
    assert match is not None
    assert match["amount"] == 8500.0


@pytest.mark.asyncio
async def test_match_transaction_no_match():
    """Test transaction matching with no match."""
    transactions = [
        {"amount": 100.0, "description": "Small expense", "timestamp": "2025-01-20T10:00:00"},
    ]
    receipt_data = {"amount": 5000.0, "date": "2025-01-20", "vendor": "Unknown"}

    match = await match_transaction(receipt_data, transactions)
    assert match is None


def test_process_receipt(client, auth_token):
    """Test receipt processing endpoint."""
    # First sync some transactions
    client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Process receipt
    response = client.post(
        "/api/ocr/process/water_bill.pdf",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "extracted" in data
    assert "flag_level" in data


def test_match_suggestions(client, auth_token):
    """Test match suggestions endpoint."""
    # Sync transactions first
    client.post(
        "/api/transactions/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    response = client.get(
        "/api/ocr/match-suggestions?amount=6000",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data


def test_process_receipt_unauthorized(client):
    """Test OCR requires authentication."""
    response = client.post("/api/ocr/process/test.pdf")
    assert response.status_code == 401
