# Authentication service for FlatWatch.
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import hmac
import os
import secrets
import uuid

import jwt
from pydantic import BaseModel

from .config import SECRET_KEY, get_runtime_mode

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
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    flat_number: Optional[str] = None


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


def hash_password(password: str, *, salt: Optional[str] = None) -> str:
    if not password:
        raise ValueError("Password is required")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 210_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash or "$" not in stored_hash:
        return False
    algorithm, salt, expected = stored_hash.split("$", 2)
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hash_password(password, salt=salt)
    return hmac.compare_digest(candidate, stored_hash)


def _row_to_user(row) -> User:
    return User(
        id=row["id"],
        firebase_uid=row["firebase_uid"],
        email=row["email"],
        name=row["name"],
        role=row["role"],
        flat_number=row["flat_number"],
    )


def _find_user_by_email(email: str):
    from .database import get_db_connection

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def _find_user_by_id(user_id: int):
    from .database import get_db_connection

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with a token-version session guard."""
    user_id = data.get("id")
    token_version = 0
    if user_id is not None:
        row = _find_user_by_id(int(user_id))
        if row:
            token_version = row["token_version"] or 0

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=8))
    to_encode = data.copy()
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4()), "token_version": token_version})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

    user_id = payload.get("id")
    token_id = payload.get("jti")
    if user_id is None or not token_id:
        return None

    from .database import get_db_connection

    conn = get_db_connection()
    user = conn.execute("SELECT token_version FROM users WHERE id = ?", (user_id,)).fetchone()
    invalidated = conn.execute(
        "SELECT token_id FROM invalidated_tokens WHERE token_id = ?",
        (token_id,),
    ).fetchone()
    conn.close()
    if not user or invalidated:
        return None
    if int(payload.get("token_version", -1)) != int(user["token_version"] or 0):
        return None
    return payload


def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate against DB users; demo mode keeps seeded any-password compatibility."""
    row = _find_user_by_email(email)
    if not row:
        return None
    if get_runtime_mode() == "demo" and email in MOCK_USERS:
        return _row_to_user(row)
    if verify_password(password, row["password_hash"]):
        return _row_to_user(row)
    return None


def create_user(email: str, name: Optional[str], flat_number: Optional[str], password: str = "") -> User:
    """Create a resident user with a password hash."""
    from .database import get_db_connection

    password_hash = hash_password(password or secrets.token_urlsafe(24))
    firebase_uid = f"user_{uuid.uuid4().hex}"
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO users (firebase_uid, email, name, role, flat_number, password_hash)
        VALUES (?, ?, ?, 'resident', ?, ?)
        """,
        (firebase_uid, email, name, flat_number, password_hash),
    )
    conn.commit()
    user_id = cursor.lastrowid
    if user_id is None:
        row = conn.execute("SELECT * FROM users WHERE firebase_uid = ?", (firebase_uid,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _row_to_user(row)


def invalidate_token(token: str, user_id: int) -> None:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    token_id = payload.get("jti")
    if not token_id:
        return

    from .database import get_db_connection

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO invalidated_tokens (token_id, user_id) VALUES (?, ?)",
        (token_id, user_id),
    )
    conn.commit()
    conn.close()


def get_current_user(token: str) -> Optional[User]:
    """Get current user from token."""
    payload = verify_token(token)
    if payload is None:
        return None
    row = _find_user_by_email(payload.get("sub"))
    return _row_to_user(row) if row else None


def require_role(user: User, required_roles: list[str]) -> bool:
    """Check if user has required role."""
    return user.role in required_roles
