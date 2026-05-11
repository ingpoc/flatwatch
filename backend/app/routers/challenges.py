# Challenges router for FlatWatch
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from ..rbac import require_resident, require_admin
from ..auth import User
from ..database import get_db_connection
from ..audit import AuditAction, log_action


class ChallengeCreate(BaseModel):
    transaction_id: int
    reason: str
    evidence: Optional[str] = None


class ChallengeReject(BaseModel):
    reason: str


class ChallengeResolve(BaseModel):
    evidence: Optional[str] = None
    response: str = "Challenge resolved by admin."
    resolution_reason: str = "Evidence reviewed."


class ChallengeResponse(BaseModel):
    id: int
    transaction_id: int
    user_id: int
    reason: str
    status: str
    created_at: str
    resolved_at: Optional[str]


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
        INSERT INTO challenges (transaction_id, user_id, reason, evidence, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (challenge.transaction_id, current_user.id, challenge.reason, challenge.evidence, now),
    )
    conn.commit()

    # Fetch created challenge
    cursor = conn.execute("SELECT * FROM challenges WHERE id = ?", (cursor.lastrowid,))
    result = dict(cursor.fetchone())
    conn.close()
    log_action(
        AuditAction.CHALLENGE_CREATE,
        current_user.id,
        f"Challenge created for transaction {challenge.transaction_id}: {challenge.reason}",
        target_id=result["id"],
        target_type="challenge",
    )

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


@router.get("/reports/resolution")
async def get_resolution_report(current_user: User = Depends(require_admin)):
    """Admin challenge resolution report with audit-oriented summary fields."""
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT status, COUNT(*) as count
        FROM challenges
        GROUP BY status
        """
    ).fetchall()
    audit_count = conn.execute(
        "SELECT COUNT(*) as count FROM audit_logs WHERE action IN ('challenge_resolve', 'challenge_reject')"
    ).fetchone()["count"]
    conn.close()
    return {
        "by_status": {row["status"]: row["count"] for row in rows},
        "resolution_audit_events": audit_count,
    }


@router.put("/{challenge_id}/resolve")
async def resolve_challenge(
    challenge_id: int,
    body: ChallengeResolve,
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
        SET status = 'resolved',
            resolved_at = ?,
            resolved_by = ?,
            assigned_reviewer_id = ?,
            evidence = ?,
            response = ?,
            resolution_reason = ?
        WHERE id = ?
        """,
        (
            datetime.now(timezone.utc),
            current_user.id,
            current_user.id,
            body.evidence,
            body.response,
            body.resolution_reason,
            challenge_id,
        ),
    )
    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Challenge not found")
    audit_id = log_action(
        AuditAction.CHALLENGE_RESOLVE,
        current_user.id,
        f"Challenge resolved: {body.resolution_reason}",
        target_id=challenge_id,
        target_type="challenge",
    )
    conn.execute("UPDATE challenges SET audit_receipt_id = ? WHERE id = ?", (audit_id, challenge_id))
    conn.commit()
    conn.close()

    return {
        "message": "Challenge resolved",
        "challenge_id": challenge_id,
        "evidence": body.evidence,
        "response": body.response,
        "resolution_reason": body.resolution_reason,
        "audit_receipt_id": audit_id,
        "resolved_by": current_user.email,
    }


@router.put("/{challenge_id}/reject")
async def reject_challenge(
    challenge_id: int,
    body: ChallengeReject,
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
    conn.close()
    log_action(
        AuditAction.CHALLENGE_REJECT,
        current_user.id,
        f"Challenge rejected: {body.reason}",
        target_id=challenge_id,
        target_type="challenge",
    )

    return {
        "message": "Challenge rejected",
        "reason": body.reason,
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
