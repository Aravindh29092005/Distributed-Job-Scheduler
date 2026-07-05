"""Security utilities: JWT, password hashing, role-based access."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ═════════════════════════════════════════════════════════════════════════
# PASSWORD HASHING
# ═════════════════════════════════════════════════════════════════════════


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


# ═════════════════════════════════════════════════════════════════════════
# JWT TOKEN MODELS
# ═════════════════════════════════════════════════════════════════════════


class TokenClaims(BaseModel):
    """JWT token payload schema."""
    sub: str  # user_id
    email: str
    role: str  # admin, member, viewer
    org_id: Optional[str] = None  # organization_id if scoped
    exp: int  # expiration timestamp
    iat: int  # issued at


class TokenResponse(BaseModel):
    """Token response for login/refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


# ═════════════════════════════════════════════════════════════════════════
# JWT ENCODING/DECODING
# ═════════════════════════════════════════════════════════════════════════


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    org_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token.
    
    Args:
        user_id: User UUID
        email: User email
        role: User role (admin, member, viewer)
        org_id: Organization UUID (optional, for scoped tokens)
        expires_delta: Custom expiration time
    
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    claims = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "org_id": str(org_id) if org_id else None,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    
    encoded_jwt = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token (longer lifetime, minimal claims).
    
    Args:
        user_id: User UUID
        email: User email
        expires_delta: Custom expiration time
    
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    claims = {
        "sub": str(user_id),
        "email": email,
        "type": "refresh",  # Mark as refresh token
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    
    encoded_jwt = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenClaims]:
    """
    Decode and validate JWT token.
    
    Args:
        token: Encoded JWT token
    
    Returns:
        TokenClaims if valid, None if expired or invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenClaims(**payload)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """
    Decode refresh token (must contain type='refresh').
    
    Args:
        token: Refresh token
    
    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ═════════════════════════════════════════════════════════════════════════
# ROLE-BASED ACCESS CONTROL
# ═════════════════════════════════════════════════════════════════════════

ROLE_HIERARCHY = {
    "admin": 100,
    "member": 50,
    "viewer": 10,
}


def has_role(user_role: str, required_role: str) -> bool:
    """Check if user role has required privilege."""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


def is_admin(role: str) -> bool:
    """Check if role is admin."""
    return role == "admin"


def is_member_or_higher(role: str) -> bool:
    """Check if role is member or admin."""
    return role in ("admin", "member")
