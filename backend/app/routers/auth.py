# Authentication router for FlatWatch
from fastapi import APIRouter, HTTPException, Depends, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from ..auth import (
    Token,
    LoginRequest,
    SignupRequest,
    User,
    SSOValidationResponse,
    create_access_token,
    authenticate_user,
    create_user,
    get_current_user,
    validate_sso_session,
)
from ..audit import AuditAction, log_action

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, req: Request):
    """
    Login endpoint (POC mock).
    In production, this will verify Firebase ID tokens.
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
    Signup endpoint (POC mock).
    In production, this will create Firebase user.
    """
    # Check if user exists
    from ..auth import MOCK_USERS
    if request.email in MOCK_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    user = create_user(request.email, request.name, request.flat_number)
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
    Verify Firebase token (POC stub).
    In production, this will call Firebase Admin SDK.
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


@router.get("/validate", response_model=SSOValidationResponse)
async def validate_sso(
    request: Request,
    cookie: Optional[str] = Header(None, alias="Cookie"),
):
    """
    SSO session validation endpoint (proxy to identity provider).

    Validates SSO session by forwarding cookies to the identity provider.
    Used by frontend to check if user is authenticated via SSO.

    Args:
        request: FastAPI request object
        cookie: Raw Cookie header from client

    Returns:
        SSOValidationResponse with user data if session is valid
    """
    if not cookie:
        return SSOValidationResponse(valid=False)

    # Forward the entire cookie string to the SSO provider
    result = await validate_sso_session(cookie)

    if result.valid:
        # Audit log successful validation
        # (Note: user.id is from SSO provider, may differ from local DB)
        from ..audit import log_action, AuditAction
        log_action(
            AuditAction.LOGIN,
            int(result.user.id) if result.user.id.isdigit() else 0,
            f"SSO session validated: {result.user.email}",
            ip_address=request.client.host if request.client else None,
        )

    return result
