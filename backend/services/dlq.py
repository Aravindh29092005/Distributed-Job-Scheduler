"""Dead Letter Queue service — atomic DLQ moves and manual resubmission."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional


def _uid(value) -> uuid.UUID:
    """Coerce str or uuid.UUID → uuid.UUID safely."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import NotFoundError, ValidationError
from backend.core.logging import get_logger
from backend.models.dlq import DeadLetterQueue
from backend.models.job import Job
from backend.state_machine import JobStateMachine, JobStatus

logger = get_logger(__name__)


class DLQService:
    """Manages the Dead Letter Queue.

    KEY DESIGN: The move to DLQ is ATOMIC — the final failure status update
    and the DLQ INSERT happen in the same database transaction. There is no
    window where a job is neither retryable nor in the DLQ.

    Transaction order:
      1. UPDATE jobs SET status='dead_letter_queue' WHERE id=? (state machine)
      2. INSERT INTO dead_letter_queue (job_id, ...) VALUES (...)
      3. COMMIT
    If either fails the whole transaction rolls back.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def move_to_dlq(
        self,
        job: Job,
        reason: str,
    ) -> DeadLetterQueue:
        """Atomically transition job to DLQ status and create DLQ record.

        This method expects the caller to pass an in-session Job object.
        The session is NOT committed here — the caller controls the transaction
        boundary so they can include additional writes (e.g., execution record).

        Args:
            job:    ORM Job instance (already loaded in this session).
            reason: Human-readable failure description.

        Returns:
            The newly created DeadLetterQueue record (not yet committed).

        Raises:
            InvalidTransitionError: if the job is in a status that cannot
                                    transition to dead_letter_queue.
        """
        # Transition through state machine — raises InvalidTransitionError on bad moves
        JobStateMachine.transition(job, JobStatus.DEAD_LETTER_QUEUE)

        entry = DeadLetterQueue(
            job_id=job.id,
            queue_id=job.queue_id,
            project_id=job.project_id,
            payload=job.payload,
            reason=reason,
            failed_at=datetime.now(timezone.utc),
        )
        self._db.add(entry)

        logger.warning(
            "job_moved_to_dlq",
            job_id=str(job.id),
            reason=reason,
            attempt=job.current_attempt,
        )
        return entry

    async def list(
        self,
        project_id: Optional[str] = None,
        queue_id: Optional[str] = None,
        resolved: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[DeadLetterQueue], int]:
        """List DLQ entries with optional filters."""
        from sqlalchemy import func, and_

        filters = []
        if project_id:
            filters.append(DeadLetterQueue.project_id == _uid(project_id))
        if queue_id:
            filters.append(DeadLetterQueue.queue_id == _uid(queue_id))
        if resolved is True:
            filters.append(DeadLetterQueue.resolved_at.isnot(None))
        elif resolved is False:
            filters.append(DeadLetterQueue.resolved_at.is_(None))

        count_query = select(func.count(DeadLetterQueue.id))
        query = select(DeadLetterQueue)

        if filters:
            where_clause = and_(*filters)
            count_query = count_query.where(where_clause)
            query = query.where(where_clause)

        count = await self._db.scalar(count_query)
        result = await self._db.execute(
            query.order_by(DeadLetterQueue.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), (count or 0)

    async def resubmit(self, dlq_id: str, user_id: str) -> Job:
        """Manually resubmit a DLQ entry back to the queue.

        Atomically:
          1. Transition job: dead_letter_queue → queued
          2. Mark DLQ entry as resolved
          3. Commit
        """
        # Load DLQ entry
        result = await self._db.execute(
            select(DeadLetterQueue).where(DeadLetterQueue.id == _uid(dlq_id))
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise NotFoundError("DeadLetterQueue entry", dlq_id)

        if entry.resolved_at is not None:
            raise ValidationError("This DLQ entry has already been resolved")

        # Load the original job
        job_result = await self._db.execute(
            select(Job).where(Job.id == entry.job_id)
        )
        job = job_result.scalar_one_or_none()
        if not job:
            raise NotFoundError("Job", str(entry.job_id))

        # Transition job back to queued (state machine allows: dlq → queued)
        JobStateMachine.transition(job, JobStatus.QUEUED)
        job.current_attempt = 0
        job.run_at = datetime.now(timezone.utc)

        # Mark DLQ entry as resolved
        entry.resolved_at = datetime.now(timezone.utc)
        entry.resolved_by = _uid(user_id)

        await self._db.commit()

        logger.info(
            "dlq_entry_resubmitted",
            dlq_id=dlq_id,
            job_id=str(job.id),
            resubmitted_by=user_id,
        )
        return job
