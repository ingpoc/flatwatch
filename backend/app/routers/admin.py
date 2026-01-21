# Admin router for FlatWatch
from fastapi import APIRouter, Depends

from ..rbac import require_admin, require_super_admin
from ..auth import User

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/stats")
async def get_admin_stats(current_user: User = Depends(require_admin)):
    """Get admin statistics (admin+ only)."""
    return {
        "message": "Admin statistics",
        "user": current_user.email,
        "role": current_user.role,
        "stats": {
            "total_users": 2,
            "active_challenges": 0,
            "pending_verifications": 0,
        },
    }


@router.get("/users")
async def list_all_users(current_user: User = Depends(require_admin)):
    """List all users (admin+ only)."""
    from ..auth import MOCK_USERS
    return {
        "users": list(MOCK_USERS.values()),
    }


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(require_super_admin)):
    """Delete a user (super_admin only)."""
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
    return {
        "message": f"User {user_id} role updated to {new_role}",
        "updated_by": current_user.email,
    }
