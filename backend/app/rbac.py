# Role-Based Access Control for FlatWatch
from enum import Enum
from typing import List, Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import User, get_current_user

security = HTTPBearer()


class Role(str, Enum):
    """User roles."""
    RESIDENT = "resident"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Role hierarchy: higher roles include lower role permissions
ROLE_HIERARCHY = {
    Role.RESIDENT: 0,
    Role.ADMIN: 1,
    Role.SUPER_ADMIN: 2,
}


def get_highest_role(role: Role) -> int:
    """Get role level for hierarchy comparison."""
    return ROLE_HIERARCHY.get(role, 0)


def has_required_role(user_role: str, required_roles: List[str]) -> bool:
    """Check if user has any of the required roles."""
    user_level = get_highest_role(Role(user_role))
    for required in required_roles:
        required_level = get_highest_role(Role(required))
        if user_level >= required_level:
            return True
    return False


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get current user if token provided, else None."""
    if credentials is None:
        return None
    return get_current_user(credentials.credentials)


async def require_roles(
    *roles: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Dependency to require specific roles.
    Usage: Depends(partial(require_roles, "admin", "super_admin"))
    """
    user = get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if not has_required_role(user.role, list(roles)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {', '.join(roles)}",
        )

    return user


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Require admin or super_admin role."""
    return await require_roles(Role.ADMIN, Role.SUPER_ADMIN, credentials=credentials)


async def require_super_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Require super_admin role."""
    return await require_roles(Role.SUPER_ADMIN, credentials=credentials)


async def require_resident(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Require any authenticated user (resident or above)."""
    return await require_roles(Role.RESIDENT, Role.ADMIN, Role.SUPER_ADMIN, credentials=credentials)


# Permission definitions
class Permission:
    """Action-based permissions."""

    # Transactions
    VIEW_TRANSACTIONS = "view_transactions"
    CREATE_TRANSACTION = "create_transaction"
    VERIFY_TRANSACTION = "verify_transaction"
    DELETE_TRANSACTION = "delete_transaction"

    # Challenges
    VIEW_CHALLENGES = "view_challenges"
    CREATE_CHALLENGE = "create_challenge"
    RESOLVE_CHALLENGE = "resolve_challenge"

    # Users
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"

    # Dashboard
    VIEW_DASHBOARD = "view_dashboard"
    EXPORT_DATA = "export_data"


ROLE_PERMISSIONS = {
    Role.RESIDENT: [
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_CHALLENGES,
        Permission.CREATE_CHALLENGE,
        Permission.VIEW_DASHBOARD,
    ],
    Role.ADMIN: [
        Permission.VIEW_TRANSACTIONS,
        Permission.CREATE_TRANSACTION,
        Permission.VERIFY_TRANSACTION,
        Permission.VIEW_CHALLENGES,
        Permission.CREATE_CHALLENGE,
        Permission.RESOLVE_CHALLENGE,
        Permission.VIEW_USERS,
        Permission.VIEW_DASHBOARD,
    ],
    Role.SUPER_ADMIN: [
        # All permissions
    ],
}


def has_permission(user_role: str, permission: str) -> bool:
    """Check if user role has specific permission."""
    user_role_enum = Role(user_role)
    if user_role_enum == Role.SUPER_ADMIN:
        return True
    return permission in ROLE_PERMISSIONS.get(user_role_enum, [])


async def require_permission(
    permission: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Dependency to require specific permission."""
    user = get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if not has_permission(user.role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {permission}",
        )

    return user
