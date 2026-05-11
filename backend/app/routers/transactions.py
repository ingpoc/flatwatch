# Transactions router for FlatWatch
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from typing import List, Optional

from ..models import Transaction, TransactionCreate
from ..rbac import require_resident, require_admin
from ..auth import User
from ..database import get_db_connection
from ..razorpay import sync_transactions

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


def _webhook_secret() -> str:
    return os.getenv("FLATWATCH_RAZORPAY_WEBHOOK_SECRET", "")


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = _webhook_secret()
    if not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


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


@router.post("/webhooks/razorpay")
async def ingest_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header("", alias="X-Razorpay-Signature"),
    idempotency_key: str = Header("", alias="Idempotency-Key"),
):
    """
    Ingest a signed Razorpay-style webhook.
    This is the production-control path for idempotency and immutable source references;
    the current `/sync` route remains the local mock feed.
    """
    body = await request.body()
    if not _verify_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Razorpay webhook signature",
        )
    if not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON webhook payload",
        ) from exc

    source_transaction_id = str(payload.get("source_transaction_id") or payload.get("id") or "").strip()
    if not source_transaction_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_transaction_id is required",
        )

    amount = float(payload.get("amount", 0))
    txn_type = payload.get("transaction_type")
    if amount <= 0 or txn_type not in {"inflow", "outflow"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload requires positive amount and inflow/outflow transaction_type",
        )

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT transaction_id FROM payment_ingestion_events WHERE idempotency_key = ?",
        (idempotency_key,),
    ).fetchone()
    if existing:
        conn.close()
        return {
            "status": "duplicate",
            "transaction_id": existing["transaction_id"],
            "source_transaction_id": source_transaction_id,
        }

    cursor = conn.execute(
        """
        INSERT INTO transactions (amount, transaction_type, description, vpa)
        VALUES (?, ?, ?, ?)
        """,
        (
            amount,
            txn_type,
            payload.get("description"),
            payload.get("vpa"),
        ),
    )
    transaction_id = cursor.lastrowid
    conn.execute(
        """
        INSERT INTO payment_ingestion_events (
            idempotency_key,
            provider,
            source_transaction_id,
            raw_payload,
            transaction_id
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            idempotency_key,
            "razorpay",
            source_transaction_id,
            json.dumps(payload, sort_keys=True),
            transaction_id,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "status": "ingested",
        "transaction_id": transaction_id,
        "source_transaction_id": source_transaction_id,
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
