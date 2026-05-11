# Tests for receipts endpoints
import pytest
import os
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.routers.receipts import UPLOAD_DIR
from app.database import init_db, get_db_path


@pytest.fixture(autouse=True)
def setup_upload_dir():
    """Ensure upload directory exists and database initialized."""
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Clean up uploaded files
    for file in UPLOAD_DIR.iterdir():
        if file.is_file():
            file.unlink()
    # Clean up database
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


def test_upload_receipt(client, auth_token):
    """Test uploading a receipt file."""
    from io import BytesIO

    file_content = b"test receipt content"
    response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("test_receipt.pdf", BytesIO(file_content), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "filename" in data
    assert data["original_filename"] == "test_receipt.pdf"
    assert data["size"] == len(file_content)
    assert "path" not in data
    assert len(data["content_hash"]) == 64
    assert "retained_until" in data


def test_upload_rejects_disallowed_mime_type(client, auth_token):
    """Test receipt uploads enforce MIME and extension allowlist."""
    from io import BytesIO

    response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("script.sh", BytesIO(b"echo unsafe"), "text/x-shellscript")},
    )
    assert response.status_code == 415


def test_upload_rejects_mismatched_extension_and_mime_type(client, auth_token):
    """Test upload extension must match MIME type."""
    from io import BytesIO

    response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("receipt.pdf", BytesIO(b"not an image"), "image/png")},
    )
    assert response.status_code == 415


def test_upload_rejects_large_receipt(client, auth_token, monkeypatch):
    """Test receipt uploads enforce size limits."""
    from io import BytesIO

    monkeypatch.setattr(
        "app.routers.receipts.MAX_RECEIPT_UPLOAD_BYTES",
        4,
    )

    response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("receipt.pdf", BytesIO(b"too large"), "application/pdf")},
    )
    assert response.status_code == 413


def test_upload_rejects_malware_signature(client, auth_token):
    """Test receipt uploads run a basic content scan."""
    from io import BytesIO

    response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={
            "file": (
                "receipt.pdf",
                BytesIO(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 400


def test_upload_without_auth(client):
    """Test upload requires authentication."""
    from io import BytesIO

    response = client.post(
        "/api/receipts/upload",
        files={"file": ("test.pdf", BytesIO(b"content"), "application/pdf")},
    )
    assert response.status_code == 401


def test_list_receipts(client, auth_token):
    """Test listing receipts."""
    response = client.get(
        "/api/receipts/list",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "files" in data


def test_get_receipt(client, auth_token):
    """Test getting receipt info."""
    # First upload a file
    from io import BytesIO

    upload_response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("test.pdf", BytesIO(b"content"), "application/pdf")},
    )
    filename = upload_response.json()["filename"]

    # Get file info
    response = client.get(
        f"/api/receipts/{filename}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == filename
    assert "path" not in data
    assert len(data["content_hash"]) == 64


def test_get_receipt_signed_download_url(client, auth_token):
    """Test receipt access uses signed URLs instead of filesystem paths."""
    from io import BytesIO

    upload_response = client.post(
        "/api/receipts/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        files={"file": ("test.pdf", BytesIO(b"content"), "application/pdf")},
    )
    filename = upload_response.json()["filename"]

    response = client.get(
        f"/api/receipts/{filename}/download-url",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == filename
    assert data["signed_url"].startswith(f"/api/receipts/{filename}/download?")
    assert "path" not in data


def test_get_receipt_rejects_path_traversal(client, auth_token):
    """Test receipt lookup rejects path traversal."""
    response = client.get(
        "/api/receipts/../flatwatch.db",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code in {400, 404}
