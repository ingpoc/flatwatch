# Admin router for FlatWatch
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..rbac import require_admin, require_super_admin
from ..auth import User
from ..audit import AuditAction, log_action
from ..database import get_db_connection

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class SocietyProfileRequest(BaseModel):
    name: str
    registration_number: str | None = None
    address: str | None = None


class ResidentImportRequest(BaseModel):
    residents: list[dict]


@router.get("/stats")
async def get_admin_stats(current_user: User = Depends(require_admin)):
    """Get admin statistics (admin+ only)."""
    conn = get_db_connection()
    user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
    challenge_count = conn.execute(
        "SELECT COUNT(*) as count FROM challenges WHERE status = 'pending'"
    ).fetchone()["count"]
    conn.close()
    return {
        "message": "Admin statistics",
        "user": current_user.email,
        "role": current_user.role,
        "stats": {
            "total_users": user_count,
            "active_challenges": challenge_count,
            "pending_verifications": 0,
        },
    }


@router.get("/users")
async def list_all_users(current_user: User = Depends(require_admin)):
    """List all users (admin+ only)."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, firebase_uid, email, name, role, flat_number FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return {
        "users": [dict(row) for row in rows],
    }


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(require_super_admin)):
    """Delete a user (super_admin only)."""
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    log_action(
        AuditAction.USER_ROLE_CHANGE,
        current_user.id,
        f"User {user_id} deleted",
        target_id=user_id,
        target_type="user",
    )
    return {
        "message": f"User {user_id} deleted",
        "deleted_by": current_user.email,
    }


@router.post("/roles/{user_id}")
async def update_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(require_super_admin)
):
    """Update user role (super_admin only)."""
    if new_role not in {"resident", "admin", "super_admin"}:
        raise HTTPException(status_code=400, detail="Unsupported role")
    conn = get_db_connection()
    cursor = conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    log_action(
        AuditAction.USER_ROLE_CHANGE,
        current_user.id,
        f"User {user_id} role updated to {new_role}",
        target_id=user_id,
        target_type="user",
    )
    return {
        "message": f"User {user_id} role updated to {new_role}",
        "updated_by": current_user.email,
    }


@router.post("/onboarding/society")
async def update_society_profile(
    profile: SocietyProfileRequest,
    current_user: User = Depends(require_super_admin),
):
    """Create or update the one-society pilot profile."""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO society_profile (id, name, registration_number, address, updated_at)
        VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            registration_number = excluded.registration_number,
            address = excluded.address,
            updated_at = CURRENT_TIMESTAMP
        """,
        (profile.name, profile.registration_number, profile.address),
    )
    conn.commit()
    conn.close()
    log_action(
        AuditAction.CONFIG_UPDATE,
        current_user.id,
        f"Society profile updated: {profile.name}",
        target_type="society_profile",
    )
    return {"message": "Society profile updated", "profile": profile.model_dump()}


@router.post("/onboarding/residents/import")
async def import_residents(
    body: ResidentImportRequest,
    current_user: User = Depends(require_admin),
):
    """Import flat/resident records for a pilot society."""
    from ..auth import create_user

    imported = []
    for resident in body.residents:
        email = resident.get("email")
        if not email:
            continue
        try:
            user = create_user(
                email,
                resident.get("name"),
                resident.get("flat_number"),
                resident.get("password") or "change-this-password",
            )
            imported.append(user.model_dump())
        except Exception:
            continue
    log_action(
        AuditAction.USER_ROLE_CHANGE,
        current_user.id,
        f"Imported {len(imported)} residents",
        target_type="resident_import",
    )
    return {"imported": imported, "imported_count": len(imported)}


@router.get("/export/audit")
async def export_audit(current_user: User = Depends(require_admin)):
    """Export pilot audit data without receipt bytes or private resident messages."""
    conn = get_db_connection()
    summary = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM transactions) as transactions,
            (SELECT COUNT(*) FROM challenges) as challenges,
            (SELECT COUNT(*) FROM receipts WHERE deleted_at IS NULL) as receipts,
            (SELECT COUNT(*) FROM audit_logs) as audit_events
        """
    ).fetchone()
    conn.close()
    log_action(
        AuditAction.CONFIG_UPDATE,
        current_user.id,
        "Audit export generated",
        target_type="audit_export",
    )
    return dict(summary)
