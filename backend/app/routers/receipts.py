# Receipt upload router for FlatWatch
import os
import uuid
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import Optional

from ..rbac import require_resident
from ..auth import User
from ..audit import AuditAction, log_action
from ..config import SECRET_KEY
from ..database import get_db_connection

router = APIRouter(prefix="/api/receipts", tags=["Receipts"])

MAX_RECEIPT_UPLOAD_BYTES = int(os.getenv("FLATWATCH_MAX_RECEIPT_UPLOAD_BYTES", str(10 * 1024 * 1024)))
ALLOWED_RECEIPT_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "text/csv": ".csv",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}
ALLOWED_RECEIPT_EXTENSIONS = set(ALLOWED_RECEIPT_MIME_TYPES.values()) | {".jpeg"}

# Upload directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "receipts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def validate_receipt_upload(file: UploadFile, content: bytes) -> str:
    original_name = file.filename or ""
    file_ext = os.path.splitext(original_name)[1].lower()
    content_type = (file.content_type or "").lower()

    if not file_ext or file_ext not in ALLOWED_RECEIPT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Receipt uploads must be PDF, PNG, JPG, CSV, XLS, or XLSX files.",
        )

    if content_type not in ALLOWED_RECEIPT_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Receipt upload MIME type is not allowed.",
        )

    expected_ext = ALLOWED_RECEIPT_MIME_TYPES[content_type]
    if expected_ext != file_ext and not (expected_ext == ".jpg" and file_ext == ".jpeg"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Receipt upload extension does not match the MIME type.",
        )

    if len(content) > MAX_RECEIPT_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Receipt upload exceeds the configured size limit.",
        )

    scan_receipt_content(content)
    return file_ext


def scan_receipt_content(content: bytes) -> None:
    signatures = [b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE", b"<script", b"javascript:"]
    lowered = content.lower()
    if any(signature.lower() in lowered for signature in signatures):
        raise HTTPException(status_code=400, detail="Receipt upload failed malware/content scan.")


def _signed_download_token(filename: str, user_id: int, expires_at: int) -> str:
    body = f"{filename}:{user_id}:{expires_at}".encode()
    return hmac.new(SECRET_KEY.encode(), body, hashlib.sha256).hexdigest()


@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    transaction_id: Optional[int] = Form(None),
    current_user: User = Depends(require_resident),
):
    """
    Upload receipt document.
    Supports: PDF, images (PNG, JPG), Excel, CSV
    """
    content = await file.read()
    file_ext = validate_receipt_upload(file, content)
    content_hash = hashlib.sha256(content).hexdigest()

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    upload_dir = ensure_upload_dir()
    file_path = upload_dir / unique_filename

    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    retained_until = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO receipts (
            filename, original_filename, storage_key, content_hash, content_type,
            size_bytes, uploaded_by, transaction_id, retained_until
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            unique_filename,
            file.filename,
            unique_filename,
            content_hash,
            file.content_type,
            len(content),
            current_user.id,
            transaction_id,
            retained_until,
        ),
    )
    conn.commit()
    conn.close()
    log_action(
        AuditAction.RECEIPT_UPLOAD,
        current_user.id,
        f"Receipt uploaded with content hash {content_hash}",
        target_type="receipt",
    )

    return {
        "message": "File uploaded successfully",
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": len(content),
        "content_hash": content_hash,
        "retained_until": retained_until,
        "transaction_id": transaction_id,
    }


@router.get("/list")
async def list_receipts(current_user: User = Depends(require_resident)):
    """List all uploaded receipts."""
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT filename, original_filename, size_bytes, content_hash, retained_until, created_at
        FROM receipts
        WHERE deleted_at IS NULL
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()
    files = [
        {
            "filename": row["filename"],
            "original_filename": row["original_filename"],
            "size": row["size_bytes"],
            "content_hash": row["content_hash"],
            "retained_until": row["retained_until"],
            "uploaded_at": row["created_at"],
        }
        for row in rows
    ]
    return {"files": files}


@router.get("/{filename}")
async def get_receipt(filename: str, current_user: User = Depends(require_resident)):
    """Get receipt by filename."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid receipt filename")

    file_path = ensure_upload_dir() / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM receipts WHERE filename = ?", (filename,)).fetchone()
    conn.close()
    log_action(
        AuditAction.RECEIPT_ACCESS,
        current_user.id,
        f"Receipt metadata accessed: {filename}",
        target_type="receipt",
    )
    return {
        "filename": filename,
        "size": row["size_bytes"] if row else file_path.stat().st_size,
        "content_hash": row["content_hash"] if row else None,
        "retained_until": row["retained_until"] if row else None,
        "uploaded_at": row["created_at"] if row else file_path.stat().st_mtime,
    }


@router.get("/{filename}/download-url")
async def get_receipt_download_url(filename: str, current_user: User = Depends(require_resident)):
    """Return a short-lived signed local retrieval URL instead of exposing a filesystem path."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid receipt filename")
    if not (ensure_upload_dir() / filename).exists():
        raise HTTPException(status_code=404, detail="File not found")
    expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp())
    token = _signed_download_token(filename, current_user.id, expires_at)
    log_action(
        AuditAction.RECEIPT_ACCESS,
        current_user.id,
        f"Signed receipt download URL issued: {filename}",
        target_type="receipt",
    )
    return {
        "filename": filename,
        "signed_url": f"/api/receipts/{filename}/download?expires={expires_at}&token={token}",
        "expires_at": expires_at,
    }
