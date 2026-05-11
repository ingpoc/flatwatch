# Audit log router for FlatWatch
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from ..rbac import require_admin
from ..auth import User
from ..audit import AuditAction, log_action, get_audit_logs, get_audit_stats


class AuditLogResponse(BaseModel):
    id: int
    action: str
    user_id: int
    details: str
    ip_address: Optional[str] = None
    target_id: Optional[int] = None
    target_type: Optional[str] = None
    timestamp: str


class AuditStatsResponse(BaseModel):
    total: int
    by_action: dict
    by_user: dict


router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    target_id: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(require_admin),
):
    """
    List audit logs with optional filters.
    Admin only - ensures only admins can view audit trail.
    """
    try:
        audit_action = AuditAction(action) if action else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audit action filter: {action}",
        ) from exc
    return get_audit_logs(user_id, audit_action, target_id, limit)


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_statistics(current_user: User = Depends(require_admin)):
    """
    Get audit log statistics.
    Admin only.
    """
    return get_audit_stats()


# Note: No DELETE endpoint - audit logs are immutable
