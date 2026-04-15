# Authentication service for FlatWatch
# POC: Demo bearer-token implementation backed by seeded users
# Security: Emails are encrypted at rest using AES-256-GCM (see encryption.py)
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from pydantic import BaseModel

from .encryption import encrypt_email, decrypt_email, hash_sensitive_data

# Secret key for JWT (in production, use environment variable)
SECRET_KEY = "flatwatch-dev-secret-key-change-in-production"
ALGORITHM = "HS256"


class User(BaseModel):
    id: int
    firebase_uid: str
    email: str
    name: Optional[str] = None
    role: str = "resident"
    flat_number: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class LoginRequest(BaseModel):
    email: str
    password: str  # POC only - the demo auth flow accepts seeded credentials


class SignupRequest(BaseModel):
    email: str
    password: str  # POC only
    name: Optional[str] = None
    flat_number: Optional[str] = None


# Mock user database (POC)
MOCK_USERS: dict[str, dict] = {
    "admin@flatwatch.test": {
        "id": 1,
        "firebase_uid": "mock_admin_123",
        "email": "admin@flatwatch.test",
        "name": "Admin User",
        "role": "super_admin",
        "flat_number": "A-001",
    },
    "resident@flatwatch.test": {
        "id": 2,
        "firebase_uid": "mock_resident_456",
        "email": "resident@flatwatch.test",
        "name": "Resident User",
        "role": "resident",
        "flat_number": "B-101",
    },
}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticate user (POC mock implementation).
    The current demo flow accepts any password for seeded users.
    """
    user_data = MOCK_USERS.get(email)
    if user_data:
        # POC: accept any password for mock users
        return User(**user_data)
    return None


def create_user(email: str, name: Optional[str], flat_number: Optional[str]) -> User:
    """Create a new user (POC mock)."""
    new_id = len(MOCK_USERS) + 1
    user_data = {
        "id": new_id,
        "firebase_uid": f"mock_{new_id}",
        "email": email,
        "name": name,
        "role": "resident",
        "flat_number": flat_number,
    }
    MOCK_USERS[email] = user_data
    return User(**user_data)


def get_current_user(token: str) -> Optional[User]:
    """Get current user from token."""
    payload = verify_token(token)
    if payload is None:
        return None

    email = payload.get("sub")
    user_data = MOCK_USERS.get(email)
    if user_data:
        return User(**user_data)
    return None


def require_role(user: User, required_roles: list[str]) -> bool:
    """Check if user has required role."""
    return user.role in required_roles
