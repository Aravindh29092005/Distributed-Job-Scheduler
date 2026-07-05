"""FastAPI dependency injection — DB sessions, current user, etc."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.security import TokenClaims, decode_token
from backend.db.session import AsyncSessionLocal

# ─────────────────────────────────────────────────────────────────────────────
# Database session dependency
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator:
    """Yield an async DB session, rolling back on exception."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────────────────────────────────────
# Authentication dependency
# ─────────────────────────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> TokenClaims:
    """Decode and validate the Bearer JWT; return the token claims.

    Raises HTTP 401 if the token is missing, expired, or invalid.
    """
    claims = decode_token(credentials.credentials)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Authentication token is invalid or expired",
                    "details": {},
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims
