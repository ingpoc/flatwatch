# Challenges router for FlatWatch
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone, timedelta

from ..rbac import require_resident, require_admin
from ..auth import User
from ..database import get_db_connection


class ChallengeCreate(BaseModel):
    transaction_id: int
    reason: str


class ChallengeResponse(BaseModel):
    id: int
    transaction_id: int
    user_id: int
    reason: str
    status: str
    created_at: str
    resolved_at: str | None


router = APIRouter(prefix="/api/challenges", tags=["Challenges"])


@router.post("", response_model=ChallengeResponse)
async def create_challenge(
    challenge: ChallengeCreate,
    current_user: User = Depends(require_resident),
):
    """Create a new challenge (dispute)."""
    # Verify transaction exists
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT id FROM transactions WHERE id = ?",
        (challenge.transaction_id,),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Create challenge
    now = datetime.now(timezone.utc)
    cursor = conn.execute(
        """
        INSERT INTO challenges (transaction_id, user_id, reason, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (challenge.transaction_id, current_user.id, challenge.reason, now),
    )
    conn.commit()

    # Fetch created challenge
    cursor = conn.execute("SELECT * FROM challenges WHERE id = ?", (cursor.lastrowid,))
    result = cursor.fetchone()
    conn.close()

    return {
        "id": result["id"],
        "transaction_id": result["transaction_id"],
        "user_id": result["user_id"],
        "reason": result["reason"],
        "status": result["status"],
        "created_at": result["created_at"],
        "resolved_at": result.get("resolved_at"),
    }


@router.get("", response_model=List[ChallengeResponse])
async def list_challenges(
    status: str = None,
    current_user: User = Depends(require_resident),
):
    """List challenges with optional status filter."""
    conn = get_db_connection()

    query = "SELECT * FROM challenges"
    params = []

    if status:
        query += " WHERE status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC"

    cursor = conn.execute(query, params)
    challenges = []
    for row in cursor.fetchall():
        row_dict = dict(row)
        # Convert datetime to string
        challenges.append({
            "id": row_dict["id"],
            "transaction_id": row_dict["transaction_id"],
            "user_id": row_dict["user_id"],
            "reason": row_dict["reason"],
            "status": row_dict["status"],
            "created_at": row_dict["created_at"],
            "resolved_at": row_dict.get("resolved_at"),
        })
    conn.close()

    return challenges


@router.put("/{challenge_id}/resolve")
async def resolve_challenge(
    challenge_id: int,
    evidence: str = None,
    current_user: User = Depends(require_admin),
):
    """
    Resolve a challenge with evidence.
    Admin only - marks challenge as resolved.
    """
    conn = get_db_connection()
    cursor = conn.execute(
        """
        UPDATE challenges
        SET status = 'resolved', resolved_at = ?
        WHERE id = ?
        """,
        (datetime.now(timezone.utc), challenge_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Challenge not found")

    return {
        "message": "Challenge resolved",
        "challenge_id": challenge_id,
        "evidence": evidence,
        "resolved_by": current_user.email,
    }


@router.put("/{challenge_id}/reject")
async def reject_challenge(
    challenge_id: int,
    reason: str,
    current_user: User = Depends(require_admin),
):
    """
    Reject a challenge (no valid evidence).
    Admin only.
    """
    conn = get_db_connection()
    cursor = conn.execute(
        "UPDATE challenges SET status = 'rejected' WHERE id = ?",
        (challenge_id,),
    )
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Challenge not found")

    return {
        "message": "Challenge rejected",
        "reason": reason,
        "rejected_by": current_user.email,
    }


@router.get("/pending/count")
async def get_pending_count(current_user: User = Depends(require_resident)):
    """Get count of pending challenges older than 48h."""
    conn = get_db_connection()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    cursor = conn.execute(
        """
        SELECT COUNT(*) as count
        FROM challenges
        WHERE status = 'pending' AND created_at < ?
        """,
        (cutoff.isoformat(),),
    )
    count = cursor.fetchone()["count"]
    conn.close()

    return {"pending_over_48h": count}


@router.get("/stats")
async def get_challenge_stats(current_user: User = Depends(require_resident)):
    """Get challenge statistics."""
    conn = get_db_connection()

    # Total challenges
    cursor = conn.execute("SELECT COUNT(*) as count FROM challenges")
    total = cursor.fetchone()["count"]

    # By status
    cursor = conn.execute(
        "SELECT status, COUNT(*) as count FROM challenges GROUP BY status"
    )
    by_status = {row["status"]: row["count"] for row in cursor.fetchall()}

    conn.close()

    return {
        "total": total,
        "by_status": by_status,
    }
