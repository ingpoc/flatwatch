# Authentication router for FlatWatch
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from ..auth import (
    Token,
    LoginRequest,
    SignupRequest,
    User,
    create_access_token,
    authenticate_user,
    create_user,
    get_current_user,
    invalidate_token,
)
from ..audit import AuditAction, log_action

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, req: Request):
    """
    Login endpoint for the demo bearer-token flow.
    """
    user = authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )

    # Audit log
    log_action(
        AuditAction.LOGIN,
        user.id,
        f"User logged in: {user.email}",
        ip_address=req.client.host if req.client else None,
    )

    return Token(access_token=access_token, user=user)


@router.post("/signup", response_model=Token)
async def signup(request: SignupRequest, req: Request):
    """
    Signup endpoint for the demo bearer-token flow.
    """
    from ..auth import _find_user_by_email
    if _find_user_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    user = create_user(request.email, request.name, request.flat_number, request.password)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )

    # Audit log
    log_action(
        AuditAction.SIGNUP,
        user.id,
        f"New user signed up: {user.email}",
        ip_address=req.client.host if req.client else None,
    )

    return Token(access_token=access_token, user=user)


@router.get("/me", response_model=User)
async def get_me(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Get current user from token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return user


@router.api_route("/verify", methods=["GET", "POST"])
async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Verify an existing demo bearer token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return {"valid": True, "user": user}


@router.post("/logout")
async def logout(
    req: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Invalidate the current bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    invalidate_token(credentials.credentials, user.id)
    log_action(
        AuditAction.LOGOUT,
        user.id,
        f"User logged out: {user.email}",
        ip_address=req.client.host if req.client else None,
    )
    return {"message": "Logged out"}
