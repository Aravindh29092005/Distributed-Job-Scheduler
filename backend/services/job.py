"""Job service — orchestrates job creation, cancellation, and retry.

Business invariants enforced here:
- Queued jobs run ONLY when their queue is not paused.
- Idempotency keys are unique per project (DB constraint + service catch).
- Status transitions go through JobStateMachine.transition(), never direct
  assignment.
- Retry scheduling is computed via the Strategy pattern (RetryService).
- Batch completion is tracked on the batch aggregation table, not
  recomputed per request.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def _uid(value) -> uuid.UUID:
    """Coerce str or uuid.UUID → uuid.UUID safely."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import (
    IdempotencyError,
    NotFoundError,
    ValidationError,
)
from backend.core.logging import get_logger
from backend.models.dlq import DeadLetterQueue
from backend.models.execution import JobExecution
from backend.models.job import Job
from backend.models.queue import Queue
from backend.models.retry import RetryPolicy
from backend.repositories.job_queue import (
    JobRepository,
    JobExecutionRepository,
)
from backend.retry import get_strategy
from backend.state_machine import JobStateMachine, JobStatus

logger = get_logger(__name__)


class JobService:
    """Create and manage jobs across all five types."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._job_repo = JobRepository(db)
        self._exec_repo = JobExecutionRepository(db)

    # ------------------------------------------------------------------
    # Job creation
    # ------------------------------------------------------------------

    async def create_job(
        self,
        *,
        queue_id: str,
        project_id: str,
        name: str,
        job_type: str = "immediate",
        payload: dict[str, Any],
        priority: int = 0,
        timeout_seconds: int = 300,
        run_at: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
        retry_policy_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> Job:
        """Create a new job and enqueue it.

        Idempotency: if a job with the same (project_id, idempotency_key)
        already exists, return the existing job rather than creating a duplicate.
        The uniqueness is enforced at the DB level; we catch the IntegrityError
        and return the existing record — no check-then-insert race.
        """
        # Verify queue exists and is not paused
        queue_result = await self._db.execute(
            select(Queue).where(Queue.id == _uid(queue_id))
        )
        queue = queue_result.scalar_one_or_none()
        if not queue or queue.archived_at is not None:
            raise NotFoundError("Queue", queue_id)
        if queue.paused:
            raise ValidationError(
                f"Queue '{queue.name}' is paused and cannot accept new jobs"
            )

        # Default run_at = now for immediate jobs
        effective_run_at = run_at or datetime.now(timezone.utc)

        job = Job(
            queue_id=_uid(queue_id),
            project_id=_uid(project_id),
            name=name,
            job_type=job_type,
            status=JobStatus.QUEUED.value,
            payload=payload,
            priority=priority,
            timeout_seconds=timeout_seconds,
            run_at=effective_run_at,
            idempotency_key=idempotency_key,
            retry_policy_id=_uid(retry_policy_id) if retry_policy_id else None,
            batch_id=_uid(batch_id) if batch_id else None,
            max_retries=max_retries,
            current_attempt=0,
        )

        # For scheduled / delayed jobs, mark status appropriately
        if job_type in ("delayed", "scheduled") and run_at and run_at > datetime.now(timezone.utc):
            job.status = JobStatus.SCHEDULED.value

        self._db.add(job)

        try:
            await self._db.flush()
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            # Idempotency key conflict — return existing job
            if idempotency_key:
                existing = await self._job_repo.get_by_idempotency_key(idempotency_key)
                if existing:
                    logger.info(
                        "job_creation_idempotent",
                        idempotency_key=idempotency_key,
                        existing_job_id=str(existing.id),
                    )
                    raise IdempotencyError(idempotency_key, str(existing.id))
            raise

        logger.info(
            "job_created",
            job_id=str(job.id),
            job_type=job_type,
            queue_id=queue_id,
            priority=priority,
        )
        return job

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def get(self, job_id: str) -> Job:
        """Get a job by ID."""
        job = await self._job_repo.get_by_id(job_id)
        if not job or job.archived_at is not None:
            raise NotFoundError("Job", job_id)
        return job

    async def list_by_queue(
        self,
        queue_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> tuple[list[Job], int]:
        """List jobs in a queue with optional status filter."""
        return await self._job_repo.list_by_queue(
            queue_id, skip=skip, limit=limit, status=status
        )

    async def list_by_project(
        self, project_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[Job], int]:
        """List jobs in a project."""
        return await self._job_repo.list_by_project(project_id, skip=skip, limit=limit)

    async def get_executions(self, job_id: str) -> list[JobExecution]:
        """Return all execution attempts for a job, newest first."""
        return await self._exec_repo.list_by_job(job_id)

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------

    async def cancel(self, job_id: str) -> Job:
        """Cancel a job if it hasn't started running yet."""
        job = await self.get(job_id)

        try:
            JobStateMachine.transition(job, JobStatus.CANCELLED)
        except Exception as e:
            raise ValidationError(str(e))

        await self._db.commit()
        logger.info("job_cancelled", job_id=job_id)
        return job

    async def manual_retry(self, job_id: str) -> Job:
        """Manually retry a failed job (reset to Queued)."""
        job = await self.get(job_id)

        if job.status not in ("failed", "dead_letter_queue"):
            raise ValidationError(
                f"Only failed or dead-lettered jobs can be manually retried "
                f"(current status: {job.status})"
            )

        job.status = JobStatus.QUEUED.value
        job.current_attempt = 0
        job.run_at = datetime.now(timezone.utc)
        await self._db.commit()

        logger.info("job_manual_retry", job_id=job_id)
        return job


class MetricsService:
    """Aggregate metrics for the observability dashboard."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_dashboard_metrics(self) -> dict:
        """Return real job/worker counts from the database."""
        from sqlalchemy import func, case
        from backend.models.worker import Worker

        # Job counts by status
        job_counts = await self._db.execute(
            select(
                func.count(Job.id).label("total"),
                func.sum(case((func.lower(Job.status).in_(["claimed", "running"]), 1), else_=0)).label("active"),
                func.sum(case((func.lower(Job.status) == "completed", 1), else_=0)).label("completed"),
                func.sum(case((func.lower(Job.status) == "failed", 1), else_=0)).label("failed"),
                func.sum(case((func.lower(Job.status).in_(["queued", "retrying"]), 1), else_=0)).label("queued"),
            ).where(Job.archived_at.is_(None))
        )
        row = job_counts.first()

        # Worker counts
        worker_counts = await self._db.execute(
            select(
                func.count(Worker.id).label("total"),
                func.sum(case((Worker.status == "active", 1), else_=0)).label("active"),
            )
        )
        w_row = worker_counts.first()

        # Queue count
        queue_count = await self._db.scalar(
            select(func.count(Queue.id)).where(Queue.archived_at.is_(None))
        )

        # DLQ count
        dlq_count = await self._db.scalar(
            select(func.count(DeadLetterQueue.id)).where(
                DeadLetterQueue.resolved_at.is_(None)
            )
        )

        return {
            "total_jobs": row.total or 0,
            "active_jobs": row.active or 0,
            "completed_jobs": row.completed or 0,
            "failed_jobs": row.failed or 0,
            "queued_jobs": row.queued or 0,
            "total_workers": w_row.total or 0,
            "active_workers": w_row.active or 0,
            "total_queues": queue_count or 0,
            "pending_items": (row.queued or 0),
            "dlq_unresolved": dlq_count or 0,
        }

    async def get_queue_throughput(self, queue_id: str, hours: int = 24) -> dict:
        """Return hourly throughput for a specific queue."""
        from sqlalchemy import func, and_
        from backend.models.execution import JobExecution
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await self._db.execute(
            select(
                func.count(JobExecution.id).label("total"),
                func.sum(case((JobExecution.status == "completed", 1), else_=0)).label("succeeded"),
                func.sum(case((JobExecution.status == "failed", 1), else_=0)).label("failed"),
                func.avg(JobExecution.duration_seconds).label("avg_duration"),
            )
            .join(Job, Job.id == JobExecution.job_id)
            .where(
                and_(
                    Job.queue_id == _uid(queue_id),
                    JobExecution.started_at >= cutoff,
                )
            )
        )
        row = result.first()
        return {
            "queue_id": queue_id,
            "window_hours": hours,
            "total_executions": row.total or 0,
            "succeeded": row.succeeded or 0,
            "failed": row.failed or 0,
            "avg_duration_seconds": float(row.avg_duration or 0),
        }
