# Tests that elevated FlatWatch writes enforce AadhaarChain trust server-side
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db_path
from app.routers.receipts import UPLOAD_DIR
import os


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    for file in UPLOAD_DIR.iterdir():
        if file.is_file():
            file.unlink()
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


def test_receipt_upload_rejected_without_wallet(client, resident_token, monkeypatch):
    async def unverified(_wallet):
        return {
            "state": "no_identity",
            "eligible": False,
            "reason": "Connect a wallet-backed AadhaarChain identity before using trust-gated flows.",
        }

    monkeypatch.setattr("app.trust.fetch_trust_snapshot", unverified)

    response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {resident_token}"},
        files={"file": ("test_receipt.pdf", BytesIO(b"test receipt content"), "application/pdf")},
    )
    assert response.status_code == 403


def test_receipt_upload_rejected_when_unverified(client, resident_token, monkeypatch):
    async def unverified(_wallet):
        return {
            "state": "identity_present_unverified",
            "eligible": False,
            "reason": "Complete AadhaarChain verification before continuing.",
        }

    monkeypatch.setattr("app.trust.fetch_trust_snapshot", unverified)

    response = client.post(
        "/api/receipts/upload",
        headers={
            "Authorization": f"Bearer {resident_token}",
            "X-Wallet-Address": "UnverifiedWallet1111111111111111111111",
        },
        files={"file": ("test_receipt.pdf", BytesIO(b"test receipt content"), "application/pdf")},
    )
    assert response.status_code == 403


def test_challenge_create_rejected_without_verified_trust(client, resident_token, monkeypatch):
    async def unverified(_wallet):
        return {
            "state": "manual_review",
            "eligible": False,
            "reason": "Verification is still under manual review.",
        }

    monkeypatch.setattr("app.trust.fetch_trust_snapshot", unverified)

    response = client.post(
        "/api/challenges",
        headers={
            "Authorization": f"Bearer {resident_token}",
            "X-Wallet-Address": "ReviewWallet111111111111111111111111",
        },
        json={"transaction_id": 1, "reason": "Suspicious amount"},
    )
    assert response.status_code == 403
