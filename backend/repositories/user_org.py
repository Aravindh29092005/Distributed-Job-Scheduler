"""User and organization repositories."""

import uuid
from typing import Optional
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.user import User
from backend.models.org import Organization, OrganizationMember
from backend.repositories.base import BaseRepository


def _to_uuid(value) -> uuid.UUID:
    """Coerce str or UUID to uuid.UUID so SQLAlchemy's Uuid column type
    can call .hex on it without raising AttributeError on SQLite."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


class UserRepository(BaseRepository[User]):
    """User repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email_active(self, email: str) -> Optional[User]:
        """Get active user by email."""
        query = select(User).where(
            and_(User.email == email, User.is_active == True, User.archived_at == None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_active(self, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
        """List active (non-archived) users."""
        return await self.list(
            skip=skip,
            limit=limit,
            where=and_(User.is_active == True, User.archived_at == None),
            order_by=User.created_at.desc(),
        )


class OrganizationRepository(BaseRepository[Organization]):
    """Organization repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Organization)

    async def list_active(self, skip: int = 0, limit: int = 100) -> tuple[list[Organization], int]:
        """List active organizations."""
        return await self.list(
            skip=skip,
            limit=limit,
            where=Organization.archived_at == None,
            order_by=Organization.created_at.desc(),
        )

    async def list_by_user(self, user_id, skip: int = 0, limit: int = 100) -> tuple[list[Organization], int]:
        """List organizations where user is a member."""
        uid = _to_uuid(user_id)

        # Join through OrganizationMember
        query = select(Organization).join(
            OrganizationMember,
            Organization.id == OrganizationMember.organization_id,
        ).where(
            and_(
                OrganizationMember.user_id == uid,
                Organization.archived_at == None,
            )
        ).order_by(Organization.created_at.desc())

        # Count
        count_query = select(func.count()).select_from(Organization).join(
            OrganizationMember,
            Organization.id == OrganizationMember.organization_id,
        ).where(
            and_(
                OrganizationMember.user_id == uid,
                Organization.archived_at == None,
            )
        )
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total


class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    """Organization member repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, OrganizationMember)

    async def get_member(self, org_id, user_id) -> Optional[OrganizationMember]:
        """Get organization member by org_id and user_id."""
        query = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == _to_uuid(org_id),
                OrganizationMember.user_id == _to_uuid(user_id),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_org_members(self, org_id, skip: int = 0, limit: int = 100) -> tuple[list[OrganizationMember], int]:
        """List members of organization."""
        return await self.list(
            skip=skip,
            limit=limit,
            where=OrganizationMember.organization_id == _to_uuid(org_id),
            order_by=OrganizationMember.created_at.desc(),
        )

    async def exists(self, org_id, user_id) -> bool:
        """Check if user is organization member."""
        query = select(func.count()).select_from(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == _to_uuid(org_id),
                OrganizationMember.user_id == _to_uuid(user_id),
            )
        )
        count = await self.db.scalar(query)
        return count > 0
