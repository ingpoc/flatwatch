# OCR router for FlatWatch
from fastapi import APIRouter, Depends

from ..rbac import require_resident
from ..auth import User
from ..ocr import process_receipt_with_ocr
from ..database import get_db_connection

router = APIRouter(prefix="/api/ocr", tags=["OCR"])


@router.post("/process/{receipt_filename}")
async def process_receipt(
    receipt_filename: str,
    current_user: User = Depends(require_resident),
):
    """
    Process receipt with OCR to extract and match data.
    """
    # Get existing transactions for matching
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 20"
    )
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Process receipt
    file_path = f"uploads/receipts/{receipt_filename}"
    result = await process_receipt_with_ocr(file_path, current_user.id, transactions)

    return {
        "message": "Receipt processed",
        "receipt": receipt_filename,
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
