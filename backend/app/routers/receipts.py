# Receipt upload router for FlatWatch
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Optional

from ..rbac import require_resident
from ..auth import User

router = APIRouter(prefix="/api/receipts", tags=["Receipts"])

# Upload directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "receipts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


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
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    upload_dir = ensure_upload_dir()
    file_path = upload_dir / unique_filename

    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {
        "message": "File uploaded successfully",
        "filename": unique_filename,
        "original_filename": file.filename,
        "path": str(file_path),
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
    file_path = ensure_upload_dir() / filename
    if not file_path.exists():
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="File not found")
    return {"filename": filename, "path": str(file_path)}
