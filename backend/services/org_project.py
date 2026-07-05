"""Organization and Project services."""
from __future__ import annotations

import uuid as _uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import (
    AuthorizationError,
    NotFoundError,
)
from backend.core.logging import get_logger
from backend.models.org import Organization, OrganizationMember
from backend.models.project import Project, ProjectMember
from backend.repositories.user_org import (
    OrganizationRepository,
    OrganizationMemberRepository,
    UserRepository,
)

logger = get_logger(__name__)


def _uid(value) -> _uuid.UUID:
    """Coerce str/UUID → uuid.UUID so SQLAlchemy's Uuid column is happy."""
    if isinstance(value, _uuid.UUID):
        return value
    return _uuid.UUID(str(value))


class OrganizationService:
    """Business logic for organization management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._org_repo = OrganizationRepository(db)
        self._member_repo = OrganizationMemberRepository(db)
        self._user_repo = UserRepository(db)

    async def create(self, name: str, owner_user_id: str) -> Organization:
        """Create a new organization and assign the creator as admin."""
        org = await self._org_repo.create({"name": name})
        await self._db.flush()

        # Make creator an admin member
        await self._member_repo.create({
            "organization_id": org.id,          # already uuid.UUID from ORM
            "user_id": _uid(owner_user_id),     # coerce to UUID
            "role": "admin",
        })
        await self._db.commit()

        logger.info("organization_created", org_id=str(org.id), owner=str(owner_user_id))
        return org

    async def get(self, org_id: str, user_id) -> Organization:
        """Get organization, enforcing membership check."""
        org = await self._org_repo.get_by_id(org_id)
        if not org or org.archived_at is not None:
            raise NotFoundError("Organization", str(org_id))

        if not await self._member_repo.exists(org_id, user_id):
            raise AuthorizationError("You are not a member of this organization")
        return org

    async def list_for_user(
        self, user_id, skip: int = 0, limit: int = 100
    ) -> tuple[list[Organization], int]:
        """List organizations the user belongs to."""
        return await self._org_repo.list_by_user(user_id, skip=skip, limit=limit)

    async def add_member(
        self, org_id: str, target_user_id: str, role: str, requester_id
    ) -> OrganizationMember:
        """Add a user to an organization (admin only)."""
        await self._require_admin(org_id, requester_id)

        # Ensure target user exists
        user = await self._user_repo.get_by_id(target_user_id)
        if not user:
            raise NotFoundError("User", target_user_id)

        member = await self._member_repo.create({
            "organization_id": _uid(org_id),
            "user_id": _uid(target_user_id),
            "role": role,
        })
        await self._db.commit()

        logger.info("org_member_added", org_id=org_id, user_id=target_user_id, role=role)
        return member

    async def _require_admin(self, org_id, user_id) -> None:
        """Raise AuthorizationError unless user is org admin."""
        member = await self._member_repo.get_member(org_id, user_id)
        if not member or member.role != "admin":
            raise AuthorizationError("Only organization admins can perform this action")

    async def archive(self, org_id: str, requester_id) -> Organization:
        """Soft-delete the organization."""
        await self._require_admin(org_id, requester_id)
        from datetime import datetime, timezone
        org = await self._org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organization", str(org_id))
        org.archived_at = datetime.now(timezone.utc)
        await self._db.commit()
        logger.info("organization_archived", org_id=org_id)
        return org


class ProjectService:
    """Business logic for project management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._org_repo = OrganizationRepository(db)
        self._org_member_repo = OrganizationMemberRepository(db)

    async def create(
        self, org_id: str, name: str, description: Optional[str], user_id
    ) -> Project:
        """Create a project inside an organization."""
        # Verify org exists and user is a member
        org = await self._org_repo.get_by_id(org_id)
        if not org or org.archived_at is not None:
            raise NotFoundError("Organization", str(org_id))
        if not await self._org_member_repo.exists(org_id, user_id):
            raise AuthorizationError("You are not a member of this organization")

        project = Project(
            organization_id=_uid(org_id),
            name=name,
            description=description,
        )
        self._db.add(project)
        await self._db.flush()

        # Add creator as project admin
        member = ProjectMember(
            project_id=project.id,
            user_id=_uid(user_id),   # safe whether str or UUID
            role="admin",
        )
        self._db.add(member)
        await self._db.commit()

        logger.info(
            "project_created",
            project_id=str(project.id),
            org_id=str(org_id),
            user_id=str(user_id),
        )
        return project

    async def get(self, project_id: str, user_id) -> Project:
        """Get project — user must be a member of the org."""
        from sqlalchemy import select
        result = await self._db.execute(
            select(Project).where(Project.id == _uid(project_id))
        )
        project = result.scalar_one_or_none()
        if not project or project.archived_at is not None:
            raise NotFoundError("Project", str(project_id))

        if not await self._org_member_repo.exists(str(project.organization_id), user_id):
            raise AuthorizationError("Access denied")
        return project

    async def list_by_org(
        self, org_id: str, user_id, skip: int = 0, limit: int = 100
    ) -> tuple[list[Project], int]:
        """List projects in an org."""
        if not await self._org_member_repo.exists(org_id, user_id):
            raise AuthorizationError("You are not a member of this organization")

        from sqlalchemy import select, func, and_
        q = (
            select(Project)
            .where(
                and_(
                    Project.organization_id == _uid(org_id),
                    Project.archived_at.is_(None),
                )
            )
            .order_by(Project.created_at.desc())
        )
        count_q = select(func.count()).select_from(q.subquery())
        total = await self._db.scalar(count_q)
        items_result = await self._db.execute(q.offset(skip).limit(limit))
        return list(items_result.scalars().all()), (total or 0)
