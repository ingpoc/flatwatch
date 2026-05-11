# Receipt upload router for FlatWatch
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import Optional

from ..rbac import require_resident
from ..auth import User

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

    return file_ext


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

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    upload_dir = ensure_upload_dir()
    file_path = upload_dir / unique_filename

    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    return {
        "message": "File uploaded successfully",
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": len(content),
        "transaction_id": transaction_id,
    }


@router.get("/list")
async def list_receipts(current_user: User = Depends(require_resident)):
    """List all uploaded receipts."""
    upload_dir = ensure_upload_dir()
    files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "uploaded_at": file_path.stat().st_mtime,
            })
    return {"files": files}


@router.get("/{filename}")
async def get_receipt(filename: str, current_user: User = Depends(require_resident)):
    """Get receipt by filename."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid receipt filename")

    file_path = ensure_upload_dir() / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "filename": filename,
        "size": file_path.stat().st_size,
        "uploaded_at": file_path.stat().st_mtime,
    }
