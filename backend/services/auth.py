"""Authentication service for Stage 2."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
    TokenResponse,
)
from backend.core.errors import (
    AuthenticationError,
    EmailAlreadyExistsError,
    InvalidTokenError,
    UserNotFoundError,
)
from backend.core.logging import get_logger, set_correlation_id, generate_correlation_id
from backend.models.user import User
from backend.repositories.user_org import UserRepository


logger = get_logger(__name__)


class AuthService:
    """Authentication service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, email: str, password: str, full_name: Optional[str] = None) -> tuple[User, TokenResponse]:
        """
        Register new user.
        
        Args:
            email: User email
            password: Plain password (will be hashed)
            full_name: Optional full name
        
        Returns:
            Tuple of (User object, TokenResponse)
        
        Raises:
            EmailAlreadyExistsError: If email already registered
        """
        # Check if email exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            logger.warning("register_attempt_duplicate_email", email=email)
            raise EmailAlreadyExistsError(email)

        # Create user
        hashed_pwd = hash_password(password)
        user_data = {
            "email": email,
            "hashed_password": hashed_pwd,
            "full_name": full_name,
            "is_active": True,
        }
        user = await self.user_repo.create(user_data)
        await self.db.commit()

        logger.info("user_registered", user_id=user.id, email=email)

        # Generate tokens
        tokens = self._generate_tokens(user)
        return user, tokens

    async def login(self, email: str, password: str) -> tuple[User, TokenResponse]:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email
            password: Plain password
        
        Returns:
            Tuple of (User, TokenResponse)
        
        Raises:
            AuthenticationError: If credentials invalid
        """
        # Find user
        user = await self.user_repo.get_by_email_active(email)
        if not user:
            logger.warning("login_attempt_user_not_found", email=email)
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.warning("login_attempt_invalid_password", user_id=user.id, email=email)
            raise AuthenticationError("Invalid email or password")

        logger.info("user_login", user_id=user.id, email=email)

        # Generate tokens
        tokens = self._generate_tokens(user)
        return user, tokens

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from client
        
        Returns:
            TokenResponse with new access token
        
        Raises:
            InvalidTokenError: If token invalid or expired
        """
        # Decode refresh token
        payload = decode_refresh_token(refresh_token)
        if not payload:
            logger.warning("refresh_token_invalid_or_expired")
            raise InvalidTokenError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning("refresh_token_user_not_found", user_id=user_id)
            raise UserNotFoundError(user_id)

        # Create new access token, keep refresh token
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role="member",  # Default role, would be fetched from org membership in real app
        )

        logger.info("access_token_refreshed", user_id=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,  # 1 hour
        )

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> None:
        """
        Change user password.
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
        
        Raises:
            UserNotFoundError: If user not found
            AuthenticationError: If old password incorrect
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            logger.warning("change_password_invalid_current", user_id=user_id)
            raise AuthenticationError("Current password is incorrect")

        # Update password
        user.hashed_password = hash_password(new_password)
        await self.db.flush()
        await self.db.commit()

        logger.info("user_password_changed", user_id=user_id)

    def _generate_tokens(self, user: User) -> TokenResponse:
        """Generate access and refresh tokens for user."""
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role="member",  # Would fetch from org membership in real app
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            email=user.email,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,  # 1 hour
        )
