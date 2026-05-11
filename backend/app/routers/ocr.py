# OCR router for FlatWatch
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from ..rbac import require_resident
from ..auth import User
from ..ocr import process_receipt_with_ocr
from ..database import get_db_connection
from ..audit import AuditAction, log_action

router = APIRouter(prefix="/api/ocr", tags=["OCR"])


@router.post("/process/{receipt_filename}")
async def process_receipt(
    receipt_filename: str,
    current_user: User = Depends(require_resident),
):
    """
    Process receipt with OCR to extract and match data.
    """
    if Path(receipt_filename).name != receipt_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid receipt filename",
        )

    # Get existing transactions for matching
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 20"
    )
    transactions = [dict(row) for row in cursor.fetchall()]

    # Process receipt
    file_path = f"uploads/receipts/{receipt_filename}"
    result = await process_receipt_with_ocr(file_path, current_user.id, transactions)
    matched = result.get("matched_transaction")
    audit_receipt_id = log_action(
        AuditAction.RECEIPT_MATCH,
        current_user.id,
        (
            f"OCR processed {receipt_filename}; match_score={result['match_score']}; "
            f"manual_review={result['needs_manual_review']}"
        ),
        target_id=matched.get("id") if matched else None,
        target_type="receipt",
    )
    conn.execute(
        """
        INSERT INTO receipt_extractions (
            receipt_filename, transaction_id, amount, vendor, receipt_date, confidence,
            extraction_method, source_hash, match_score, matching_rule,
            needs_manual_review, audit_receipt_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            receipt_filename,
            matched.get("id") if matched else None,
            result["extracted"].get("amount"),
            result["extracted"].get("vendor"),
            result["extracted"].get("date"),
            result["extracted"].get("confidence", 0),
            result["extracted"].get("extraction_method", "unknown"),
            result["extracted"].get("source_hash", ""),
            result["match_score"],
            result["matching_rule"],
            result["needs_manual_review"],
            audit_receipt_id,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "message": "Receipt processed",
        "receipt": receipt_filename,
        "audit_receipt_id": audit_receipt_id,
        **result,
    }


@router.get("/match-suggestions")
async def get_match_suggestions(
    amount: float,
    current_user: User = Depends(require_resident),
):
    """
    Get transaction match suggestions for a receipt amount.
    """
    conn = get_db_connection()
    cursor = conn.execute(
        """
        SELECT * FROM transactions
        WHERE ABS(amount - ?) < 100
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (amount,),
    )
    matches = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"matches": matches}
