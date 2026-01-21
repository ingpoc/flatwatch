# Transactions router for FlatWatch
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from ..models import Transaction, TransactionCreate
from ..rbac import require_resident, require_admin
from ..auth import User
from ..database import get_db_connection
from ..razorpay import sync_transactions

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=List[Transaction])
async def list_transactions(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    txn_type: Optional[str] = Query(None, pattern="^(inflow|outflow)$"),
    current_user: User = Depends(require_resident),
):
    """List transactions with optional filtering and attribution."""
    conn = get_db_connection()

    # Query with user attribution joins
    query = """
        SELECT
            t.*,
            u1.name as entered_by_name,
            u1.role as entered_by_role,
            u2.name as approved_by_name,
            u2.role as approved_by_role
        FROM transactions t
        LEFT JOIN users u1 ON t.entered_by = u1.id
        LEFT JOIN users u2 ON t.approved_by = u2.id
    """
    params = []

    if txn_type:
        query += " WHERE t.transaction_type = ?"
        params.append(txn_type)

    query += " ORDER BY t.timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@router.post("/sync")
async def trigger_sync(current_user: User = Depends(require_resident)):
    """
    Trigger manual sync from Razorpay.
    In production, this is called by cron every 5 minutes.
    """
    result = await sync_transactions()
    return {
        "message": "Sync completed",
        **result,
    }


@router.get("/summary")
async def get_summary(current_user: User = Depends(require_resident)):
    """Get financial summary."""
    conn = get_db_connection()

    # Get inflow total
    cursor = conn.execute(
        "SELECT SUM(amount) as total FROM transactions WHERE transaction_type = 'inflow'"
    )
    inflow = cursor.fetchone()["total"] or 0

    # Get outflow total
    cursor = conn.execute(
        "SELECT SUM(amount) as total FROM transactions WHERE transaction_type = 'outflow'"
    )
    outflow = cursor.fetchone()["total"] or 0

    # Get unmatched count
    cursor = conn.execute(
        "SELECT COUNT(*) as count FROM transactions WHERE verified = 0"
    )
    unmatched = cursor.fetchone()["count"]

    # Get recent transactions count
    cursor = conn.execute(
        "SELECT COUNT(*) as count FROM transactions WHERE datetime(timestamp) > datetime('now', '-24 hours')"
    )
    recent = cursor.fetchone()["count"]

    conn.close()

    balance = inflow - outflow

    return {
        "balance": balance,
        "total_inflow": inflow,
        "total_outflow": outflow,
        "unmatched_transactions": unmatched,
        "recent_transactions_24h": recent,
    }


@router.post("", response_model=Transaction)
async def create_transaction(
    txn: TransactionCreate,
    current_user: User = Depends(require_resident),
):
    """Create a new transaction (manual entry)."""
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO transactions (amount, transaction_type, description, vpa, entered_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (txn.amount, txn.transaction_type, txn.description, txn.vpa, current_user.id),
    )
    conn.commit()

    # Fetch the created transaction with attribution
    cursor = conn.execute(
        """
        SELECT
            t.*,
            u1.name as entered_by_name,
            u1.role as entered_by_role
        FROM transactions t
        LEFT JOIN users u1 ON t.entered_by = u1.id
        WHERE t.id = ?
        """,
        (cursor.lastrowid,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row)


@router.put("/{txn_id}/verify")
async def verify_transaction(
    txn_id: int,
    current_user: User = Depends(require_admin),
):
    """Verify a transaction (admin+ only)."""
    from datetime import datetime, timezone

    conn = get_db_connection()
    cursor = conn.execute(
        """
        UPDATE transactions
        SET verified = 1, approved_by = ?, approved_at = ?
        WHERE id = ?
        """,
        (current_user.id, datetime.now(timezone.utc), txn_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise ValueError("Transaction not found")

    # Fetch updated transaction with attribution
    cursor = conn.execute(
        """
        SELECT
            t.*,
            u1.name as entered_by_name,
            u1.role as entered_by_role,
            u2.name as approved_by_name,
            u2.role as approved_by_role
        FROM transactions t
        LEFT JOIN users u1 ON t.entered_by = u1.id
        LEFT JOIN users u2 ON t.approved_by = u2.id
        WHERE t.id = ?
        """,
        (txn_id,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row)
