"""Authentication API router - Stage 2."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user, get_db
from backend.core.errors import AppException
from backend.core.logging import get_logger, set_correlation_id
from backend.core.security import TokenClaims
from backend.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ChangePasswordRequest,
    UserCreate,
    UserResponse,
)
from backend.services.auth import AuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register new user account."""
    try:
        service = AuthService(db)
        user, tokens = await service.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )

        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            user=UserResponse.model_validate(user),
        )
    except AppException as e:
        logger.error("register_failed", error=str(e), status_code=e.status_code)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("register_unexpected_error", error=str(e))
        raise HTTPException(status_code=500, detail="Registration failed due to an internal error.")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user's profile."""
    import uuid
    from backend.repositories.user_org import UserRepository
    user_repo = UserRepository(db)
    try:
        user_id = uuid.UUID(current_user.sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login and get tokens."""
    try:
        service = AuthService(db)
        user, tokens = await service.login(
            email=request.email,
            password=request.password,
        )

        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            user=UserResponse.model_validate(user),
        )
    except AppException as e:
        logger.error("login_failed", error=str(e), status_code=e.status_code)
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token."""
    try:
        service = AuthService(db)
        tokens = await service.refresh_access_token(request.refresh_token)
        return tokens
    except AppException as e:
        logger.error("refresh_failed", error=str(e), status_code=e.status_code)
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user = Depends(),  # TODO: Add current user dependency
    db: AsyncSession = Depends(get_db),
):
    """Change current user password."""
    try:
        service = AuthService(db)
        await service.change_password(
            user_id=current_user.id,
            old_password=request.old_password,
            new_password=request.new_password,
        )
        return {"message": "Password changed successfully"}
    except AppException as e:
        logger.error("change_password_failed", error=str(e), status_code=e.status_code)
        raise HTTPException(status_code=e.status_code, detail=e.message)
