from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, Field


# ═════════════════════════════════════════════════════════════════════════
# AUTH REQUEST/RESPONSE
# ═════════════════════════════════════════════════════════════════════════


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response."""
    access_token: str
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    old_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8, max_length=255)


# ═════════════════════════════════════════════════════════════════════════
# USER
# ═════════════════════════════════════════════════════════════════════════


class UserCreate(BaseModel):
    """User creation request."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    """User update request."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """User response."""
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CurrentUser(UserResponse):
    """Current authenticated user context."""
    pass


# ═════════════════════════════════════════════════════════════════════════
# TOKEN CLAIMS
# ═════════════════════════════════════════════════════════════════════════


class TokenData(BaseModel):
    """Token data extracted from JWT."""
    user_id: str
    email: str
    role: str
    org_id: Optional[str] = None
