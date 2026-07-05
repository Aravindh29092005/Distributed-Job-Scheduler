"""Queue and RetryPolicy services."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional


def _uid(value) -> uuid.UUID:
    """Coerce str or uuid.UUID → uuid.UUID safely."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from backend.core.logging import get_logger
from backend.models.job import Job
from backend.models.queue import Queue
from backend.models.retry import RetryPolicy
from backend.repositories.job_queue import (
    QueueRepository,
    RetryPolicyRepository,
)
from backend.repositories.user_org import OrganizationMemberRepository

logger = get_logger(__name__)


class QueueService:
    """Business logic for queue management.

    Invariants enforced here (not in routers):
    - A paused queue cannot accept new jobs (enforced in JobService).
    - Queue names must be unique within a project.
    - Only org members can create/manage queues.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._queue_repo = QueueRepository(db)
        self._member_repo = OrganizationMemberRepository(db)

    async def create(
        self,
        project_id: str,
        org_id: str,
        name: str,
        description: Optional[str],
        priority: int,
        max_concurrent: int,
        user_id: str,
    ) -> Queue:
        """Create a queue in the given project."""
        await self._require_membership(org_id, user_id)

        # Name uniqueness is enforced by DB constraint; create handles it
        queue = Queue(
            project_id=_uid(project_id),
            name=name,
            description=description,
            priority=priority,
            max_concurrent=max_concurrent,
        )
        self._db.add(queue)
        await self._db.commit()

        logger.info("queue_created", queue_id=str(queue.id), name=name, project_id=project_id)
        return queue

    async def get(self, queue_id: str) -> Queue:
        """Get a queue by ID."""
        result = await self._db.execute(
            select(Queue).where(Queue.id == _uid(queue_id))
        )
        queue = result.scalar_one_or_none()
        if not queue or queue.archived_at is not None:
            raise NotFoundError("Queue", queue_id)
        return queue

    async def list_by_project(
        self, project_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[Queue], int]:
        """List queues in a project."""
        return await self._queue_repo.list_by_project(project_id, skip=skip, limit=limit)

    async def pause(self, queue_id: str, user_id: str, org_id: str) -> Queue:
        """Pause a queue — workers will stop claiming from it."""
        await self._require_membership(org_id, user_id)
        queue = await self.get(queue_id)
        queue.paused = True
        queue.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        logger.info("queue_paused", queue_id=queue_id)
        return queue

    async def resume(self, queue_id: str, user_id: str, org_id: str) -> Queue:
        """Resume a paused queue."""
        await self._require_membership(org_id, user_id)
        queue = await self.get(queue_id)
        queue.paused = False
        queue.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        logger.info("queue_resumed", queue_id=queue_id)
        return queue

    async def get_stats(self, queue_id: str) -> dict:
        """Return job count breakdown by status for a queue."""
        return await self._queue_repo.get_stats(queue_id)

    async def _require_membership(self, org_id: str, user_id: str) -> None:
        if not await self._member_repo.exists(org_id, user_id):
            raise AuthorizationError("You are not a member of this organization")

    async def archive(self, queue_id: str, org_id: str, user_id: str) -> Queue:
        """Soft-delete the queue."""
        await self._require_membership(org_id, user_id)
        queue = await self.get(queue_id)

        # Business rule: cannot archive a queue that still has active jobs
        active_count_result = await self._db.execute(
            select(func.count(Job.id)).where(
                Job.queue_id == queue.id,
                Job.status.in_(["queued", "claimed", "running", "retrying"]),
            )
        )
        active_count = active_count_result.scalar() or 0
        if active_count > 0:
            raise ValidationError(
                f"Cannot archive queue with {active_count} active job(s). "
                "Drain or cancel them first."
            )

        queue.archived_at = datetime.now(timezone.utc)
        await self._db.commit()
        logger.info("queue_archived", queue_id=queue_id)
        return queue


class RetryPolicyService:
    """Business logic for retry policy management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._policy_repo = RetryPolicyRepository(db)

    async def create(
        self,
        project_id: str,
        name: str,
        max_retries: int,
        strategy: str,
        base_delay_seconds: int,
        max_delay_seconds: int,
        user_id: str,
    ) -> RetryPolicy:
        """Create a retry policy owned by a project."""
        from backend.retry import get_strategy
        get_strategy(strategy)  # Raises KeyError on invalid name

        policy = RetryPolicy(
            project_id=_uid(project_id),
            name=name,
            max_retries=max_retries,
            strategy=strategy,
            base_delay_seconds=base_delay_seconds,
            max_delay_seconds=max_delay_seconds,
        )
        self._db.add(policy)
        await self._db.commit()

        logger.info("retry_policy_created", policy_id=str(policy.id), strategy=strategy)
        return policy

    async def get(self, policy_id: str) -> RetryPolicy:
        """Get a retry policy."""
        result = await self._db.execute(
            select(RetryPolicy).where(RetryPolicy.id == _uid(policy_id))
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise NotFoundError("RetryPolicy", policy_id)
        return policy

    async def list_by_project(
        self, project_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[RetryPolicy], int]:
        """List retry policies for a project."""
        return await self._policy_repo.list_by_project(project_id, skip=skip, limit=limit)

    async def list_by_org(
        self, org_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[RetryPolicy], int]:
        """Alias kept for backward compatibility — delegates to list_by_project."""
        return await self._policy_repo.list_by_project(org_id, skip=skip, limit=limit)
