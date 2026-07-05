"""Queue, job, and retry policy repositories."""

import uuid as _uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import and_, func, select, update, case
from sqlalchemy.ext.asyncio import AsyncSession


def _uid(value) -> _uuid.UUID:
    """Coerce str/UUID to uuid.UUID for SQLAlchemy Uuid column comparisons."""
    if isinstance(value, _uuid.UUID):
        return value
    return _uuid.UUID(str(value))

from backend.models.queue import Queue
from backend.models.job import Job
from backend.models.execution import JobExecution
from backend.models.retry import RetryPolicy
from backend.models.dlq import DeadLetterQueue
from backend.repositories.base import BaseRepository


class QueueRepository(BaseRepository[Queue]):
    """Queue repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Queue)

    async def list_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> tuple[list[Queue], int]:
        """List queues in project."""
        return await self.list(
            skip=skip,
            limit=limit,
            where=and_(Queue.project_id == _uid(project_id), Queue.archived_at == None),
            order_by=Queue.created_at.desc(),
        )

    async def get_by_name(self, project_id: str, name: str) -> Optional[Queue]:
        """Get queue by project and name."""
        query = select(Queue).where(
            and_(
                Queue.project_id == _uid(project_id),
                Queue.name == name,
                Queue.archived_at == None,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_stats(self, queue_id: str) -> dict:
        """Get queue statistics with accurate lowercase status values."""
        query = select(
            func.sum(case((Job.status.in_(["queued", "retrying"]), 1), else_=0)).label("pending"),
            func.sum(case((Job.status.in_(["claimed", "running"]), 1), else_=0)).label("processing"),
            func.sum(case((Job.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Job.status == "failed", 1), else_=0)).label("failed"),
            func.sum(case((Job.status == "dead_letter_queue", 1), else_=0)).label("dead_letter"),
        ).where(Job.queue_id == _uid(queue_id))

        result = await self.db.execute(query)
        row = result.first()

        return {
            "queue_id": queue_id,
            "pending_count": row.pending or 0,
            "processing_count": row.processing or 0,
            "completed_count": row.completed or 0,
            "failed_count": row.failed or 0,
            "dead_letter_count": row.dead_letter or 0,
        }


class RetryPolicyRepository(BaseRepository[RetryPolicy]):
    """Retry policy repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, RetryPolicy)

    async def list_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> tuple[list[RetryPolicy], int]:
        """List retry policies in project."""
        return await self.list(
            skip=skip,
            limit=limit,
            where=RetryPolicy.project_id == _uid(project_id),
            order_by=RetryPolicy.created_at.desc(),
        )

    async def list_by_org(self, org_id: str, skip: int = 0, limit: int = 100) -> tuple[list[RetryPolicy], int]:
        """Alias kept for backward compat."""
        return await self.list_by_project(org_id, skip=skip, limit=limit)

    async def get_by_name(self, project_id: str, name: str) -> Optional[RetryPolicy]:
        """Get retry policy by project and name."""
        query = select(RetryPolicy).where(
            and_(
                RetryPolicy.project_id == _uid(project_id),
                RetryPolicy.name == name,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


class JobRepository(BaseRepository[Job]):
    """Job repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Job)

    async def claim_job(self, queue_id: str, worker_id: str) -> Optional[Job]:
        """
        Atomic job claim using SELECT FOR UPDATE SKIP LOCKED.
        
        Critical for preventing double-claiming. Only one worker gets each job.
        """
        # Use raw SQL for FOR UPDATE SKIP LOCKED
        from sqlalchemy import text

        query = text("""
            SELECT id FROM jobs 
            WHERE queue_id = :queue_id 
              AND status = 'Queued' 
              AND archived_at IS NULL
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """)

        result = await self.db.execute(
            query,
            {"queue_id": queue_id}
        )
        row = result.first()

        if not row:
            return None

        job_id = row[0]
        job = await self.get_by_id(job_id)

        if job:
            job.status = "Claimed"
            job.worker_id = worker_id
            job.claimed_at = datetime.now(timezone.utc)
            await self.db.flush()

        return job

    async def list_by_queue(self, queue_id: str, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> tuple[list[Job], int]:
        """List jobs in queue."""
        where_clause = and_(Job.queue_id == _uid(queue_id), Job.archived_at == None)
        if status:
            where_clause = and_(where_clause, Job.status == status)

        return await self.list(
            skip=skip,
            limit=limit,
            where=where_clause,
            order_by=Job.created_at.desc(),
        )

    async def list_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> tuple[list[Job], int]:
        """List jobs in project."""
        return await self.list(
            skip=skip,
            limit=limit,
            where=and_(Job.project_id == _uid(project_id), Job.archived_at == None),
            order_by=Job.created_at.desc(),
        )

    async def get_by_idempotency_key(self, key: str) -> Optional[Job]:
        """Get job by idempotency key."""
        query = select(Job).where(Job.idempotency_key == key)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_claimed_by_worker(self, worker_id: str) -> list[Job]:
        """List jobs claimed by worker (not yet completed)."""
        query = select(Job).where(
            and_(
                Job.worker_id == _uid(worker_id),
                Job.status.in_(["Claimed", "Running"]),
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def requeue_claimed_jobs(self, worker_id: str) -> int:
        """Requeue jobs claimed by dead worker back to queued status."""
        from datetime import datetime, timezone
        stmt = (
            update(Job)
            .where(
                and_(
                    Job.worker_id == worker_id,
                    Job.status.in_(["claimed", "running"]),
                )
            )
            .values(
                status="queued",
                worker_id=None,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount


class JobExecutionRepository(BaseRepository[JobExecution]):
    """Job execution repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, JobExecution)

    async def list_by_job(self, job_id: str) -> list[JobExecution]:
        """List executions for job."""
        query = select(JobExecution).where(
            JobExecution.job_id == job_id
        ).order_by(JobExecution.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_latest_execution(self, job_id: str) -> Optional[JobExecution]:
        """Get latest execution for job."""
        query = select(JobExecution).where(
            JobExecution.job_id == job_id
        ).order_by(JobExecution.created_at.desc()).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


class DeadLetterQueueRepository(BaseRepository[DeadLetterQueue]):
    """Dead letter queue repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, DeadLetterQueue)

    async def list_by_queue(self, queue_id: str, skip: int = 0, limit: int = 100) -> tuple[list[DeadLetterQueue], int]:
        """List DLQ entries in queue."""
        return await self.list(
            skip=skip,
            limit=limit,
            where=DeadLetterQueue.queue_id == _uid(queue_id),
            order_by=DeadLetterQueue.created_at.desc(),
        )

    async def get_by_job_id(self, job_id: str) -> Optional[DeadLetterQueue]:
        """Get DLQ entry by job ID."""
        query = select(DeadLetterQueue).where(DeadLetterQueue.job_id == _uid(job_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
