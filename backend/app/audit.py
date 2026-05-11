# Audit logging service for FlatWatch
# Immutable audit trails - no delete function
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from .database import get_db_connection


class AuditAction(str, Enum):
    """Types of auditable actions."""
    # Auth actions
    LOGIN = "login"
    LOGOUT = "logout"
    SIGNUP = "signup"

    # Transaction actions
    TRANSACTION_SYNC = "transaction_sync"
    TRANSACTION_VERIFY = "transaction_verify"
    TRANSACTION_CREATE = "transaction_create"

    # Receipt actions
    RECEIPT_UPLOAD = "receipt_upload"
    RECEIPT_MATCH = "receipt_match"
    RECEIPT_ACCESS = "receipt_access"
    RECEIPT_DELETE = "receipt_delete"

    # Challenge actions
    CHALLENGE_CREATE = "challenge_create"
    CHALLENGE_RESOLVE = "challenge_resolve"
    CHALLENGE_REJECT = "challenge_reject"

    # Admin actions
    USER_ROLE_CHANGE = "user_role_change"
    CONFIG_UPDATE = "config_update"


def log_action(
    action: AuditAction,
    user_id: int,
    details: str,
    ip_address: Optional[str] = None,
    target_id: Optional[int] = None,
    target_type: Optional[str] = None,
) -> int:
    """
    Log an action to the audit trail.

    Returns the audit log entry ID.
    """
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO audit_logs (
            action, user_id, details, ip_address, target_id, target_type, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action.value,
            user_id,
            details,
            ip_address,
            target_id,
            target_type,
            datetime.now(timezone.utc),
        ),
    )
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id


def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[AuditAction] = None,
    target_id: Optional[int] = None,
    limit: int = 100,
) -> list[dict]:
    """
    Retrieve audit logs with optional filters.

    Args:
        user_id: Filter by user who performed action
        action: Filter by action type
        target_id: Filter by target entity ID
        limit: Max results to return

    Returns:
        List of audit log entries
    """
    conn = get_db_connection()
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)

    if action is not None:
        query += " AND action = ?"
        params.append(action.value)

    if target_id is not None:
        query += " AND target_id = ?"
        params.append(target_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    logs = []
    for row in cursor.fetchall():
        row_dict = dict(row)
        logs.append({
            "id": row_dict["id"],
            "action": row_dict["action"],
            "user_id": row_dict["user_id"],
            "details": row_dict["details"],
            "ip_address": row_dict.get("ip_address"),
            "target_id": row_dict.get("target_id"),
            "target_type": row_dict.get("target_type"),
            "timestamp": row_dict["timestamp"],
        })
    conn.close()
    return logs


def get_audit_stats() -> dict:
    """Get audit log statistics."""
    conn = get_db_connection()

    # Total actions
    cursor = conn.execute("SELECT COUNT(*) as count FROM audit_logs")
    total = cursor.fetchone()["count"]

    # By action type
    cursor = conn.execute(
        "SELECT action, COUNT(*) as count FROM audit_logs GROUP BY action"
    )
    by_action = {row["action"]: row["count"] for row in cursor.fetchall()}

    # By user
    cursor = conn.execute(
        "SELECT user_id, COUNT(*) as count FROM audit_logs GROUP BY user_id"
    )
    by_user = {row["user_id"]: row["count"] for row in cursor.fetchall()}

    conn.close()

    return {
        "total": total,
        "by_action": by_action,
        "by_user": by_user,
    }


def init_audit_tables():
    """Initialize audit log tables (called from database.py)."""
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            details TEXT NOT NULL,
            ip_address TEXT,
            target_id INTEGER,
            target_type TEXT,
            timestamp TEXT NOT NULL
        )
        """
    )
    # Create indexes for common queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_logs(target_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
    conn.commit()
    conn.close()
