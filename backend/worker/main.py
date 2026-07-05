"""Worker main process — atomic claiming, concurrent execution, heartbeats.

CONCURRENCY MODEL:
  Three concurrent asyncio tasks run for the lifetime of the worker:
    1. _poll_loop:      Finds claimable jobs and launches execution tasks.
    2. _heartbeat_loop: Writes WorkerHeartbeat rows on a fixed interval.
                        INTENTIONALLY SEPARATE from job execution so that a
                        stuck job cannot block heartbeats and cause false
                        dead-worker detection.
    3. _reaper_loop:   Finds stale workers and requeues their orphaned jobs.

ATOMIC CLAIMING (SELECT FOR UPDATE SKIP LOCKED):
  claim_job() runs a single UPDATE...WHERE id=(SELECT...FOR UPDATE SKIP LOCKED)
  RETURNING * — one SQL statement that both finds AND transitions the job.
  Why this prevents double-claiming:
    - FOR UPDATE acquires a row-level exclusive lock on the selected row.
    - SKIP LOCKED means a second concurrent SELECT that hits the same row
      immediately skips it (no waiting, no re-reading stale data).
    - The UPDATE and the lock release happen atomically at commit.
  There is no window between "read the job" and "mark it claimed" where
  another worker could steal it.

GRACEFUL SHUTDOWN:
  On SIGTERM / SIGINT:
    1. Set self.running = False (stops _poll_loop from launching new tasks).
    2. Wait up to GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS for active jobs.
    3. Any jobs that don't finish in time are requeued by setting their
       status back to 'queued' so another worker can pick them up.

DEAD-WORKER REAPER:
  _reaper_loop queries workers whose last heartbeat is older than
  REAP_THRESHOLD_SECONDS and requeues all jobs they claimed.
  It excludes self.worker_id to avoid racing with its own heartbeat.
"""
from __future__ import annotations

import asyncio
import os
import signal
import socket
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.logging import configure_logging, generate_correlation_id, get_logger
from backend.db.session import AsyncSessionLocal
from backend.models.execution import JobExecution
from backend.models.job import Job
from backend.models.worker import Worker, WorkerHeartbeat
from backend.retry import get_strategy
from backend.services.dlq import DLQService
from backend.state_machine import InvalidTransitionError, JobStateMachine, JobStatus

logger = get_logger(__name__)


class JobWorker:
    """Standalone async worker process that claims and executes jobs."""

    def __init__(
        self,
        hostname: Optional[str] = None,
        max_concurrent: int = 10,
    ) -> None:
        self.hostname = hostname or socket.gethostname()
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.running = False
        self.worker_id: Optional[str] = None
        self._active_tasks: set[asyncio.Task] = set()

    # ─────────────────────────────────────────────────────────────────────
    # Entry point
    # ─────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Register with the DB and run all background loops concurrently."""
        configure_logging(level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)
        logger.info("worker_starting", hostname=self.hostname, max_concurrent=self.max_concurrent)

        await self._register()
        self.running = True

        try:
            await asyncio.gather(
                self._poll_loop(),
                self._heartbeat_loop(),
                self._reaper_loop(),
                return_exceptions=True,
            )
        finally:
            await self._shutdown()

    # ─────────────────────────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────────────────────────

    async def _register(self) -> None:
        """Register or re-register this worker in the workers table.

        Uses a parameterised query (never f-strings with user-controlled
        input) to prevent SQL injection.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Worker).where(Worker.hostname == self.hostname)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.status = "active"
                self.worker_id = str(existing.id)
                await db.commit()
                logger.info("worker_re_registered", worker_id=str(self.worker_id))
            else:
                worker = Worker(
                    hostname=self.hostname,
                    status="active",
                    concurrency_limit=self.max_concurrent,
                )
                db.add(worker)
                await db.flush()
                self.worker_id = str(worker.id)
                await db.commit()
                logger.info("worker_registered", worker_id=str(self.worker_id))

    # ─────────────────────────────────────────────────────────────────────
    # Poll loop
    # ─────────────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Continuously claim jobs from all active queues."""
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    # Fetch all non-paused queues
                    from backend.models.queue import Queue
                    queues_result = await db.execute(
                        select(Queue).where(
                            Queue.paused.is_(False),
                            Queue.archived_at.is_(None),
                        ).order_by(Queue.priority.desc())
                    )
                    queues = queues_result.scalars().all()

                    for queue in queues:
                        # Only claim if we're under the semaphore limit
                        if self.semaphore._value == 0:
                            break

                        job = await self._claim_job(db, queue_id=str(queue.id))
                        if job:
                            task = asyncio.create_task(
                                self._execute_job(str(job.id), str(queue.id))
                            )
                            self._active_tasks.add(task)
                            task.add_done_callback(self._active_tasks.discard)

            except Exception as exc:
                logger.error("poll_loop_error", error=str(exc), exc_info=exc)

            await asyncio.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)

    async def _claim_job(self, db: AsyncSession, *, queue_id: str) -> Optional[Job]:
        """Atomically claim the next eligible job via a single SQL statement.

        WHY UPDATE...WHERE id=(SELECT...FOR UPDATE SKIP LOCKED):
          A two-step approach (SELECT first, UPDATE second) has a TOCTOU race —
          two workers could both SELECT the same row before either UPDATEs it.
          Using a subquery UPDATE with RETURNING collapses the lock-acquisition
          and the status change into ONE atomic operation. The row is locked for
          the duration of the transaction; SKIP LOCKED ensures a concurrent
          worker's SELECT simply skips locked rows instead of waiting or seeing
          stale data.
        """
        # Check dialect
        bind = db.bind
        is_sqlite = bind is not None and bind.dialect.name == "sqlite"

        from sqlalchemy import text
        if is_sqlite:
            stmt = text("""
                UPDATE jobs
                SET status = :new_status,
                    worker_id = :worker_id,
                    updated_at = :now
                WHERE id = (
                    SELECT id FROM jobs
                    WHERE queue_id   = :queue_id
                      AND status     IN ('queued', 'retrying')
                      AND run_at     <= :now
                      AND archived_at IS NULL
                    ORDER BY priority DESC, run_at ASC
                    LIMIT 1
                )
                RETURNING id
            """)
            import uuid
            result = await db.execute(
                stmt,
                {
                    "new_status": JobStatus.CLAIMED.value,
                    "worker_id": uuid.UUID(str(self.worker_id)).hex,
                    "queue_id": uuid.UUID(str(queue_id)).hex,
                    "now": datetime.now(timezone.utc),
                },
            )
        else:
            stmt = text("""
                UPDATE jobs
                SET status = :new_status,
                    worker_id = :worker_id,
                    updated_at = now()
                WHERE id = (
                    SELECT id FROM jobs
                    WHERE queue_id   = :queue_id
                      AND status     IN ('queued', 'retrying')
                      AND run_at     <= now()
                      AND archived_at IS NULL
                    ORDER BY priority DESC, run_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id
            """)
            result = await db.execute(
                stmt,
                {
                    "new_status": JobStatus.CLAIMED.value,
                    "worker_id": self.worker_id,
                    "queue_id": queue_id,
                },
            )
        row = result.fetchone()
        if not row:
            return None

        await db.commit()

        # Load the job object for the execution phase
        import uuid
        job_uuid = uuid.UUID(str(row[0])) if not isinstance(row[0], uuid.UUID) else row[0]
        job_result = await db.execute(select(Job).where(Job.id == job_uuid))
        return job_result.scalar_one_or_none()

    # ─────────────────────────────────────────────────────────────────────
    # Job execution
    # ─────────────────────────────────────────────────────────────────────

    async def _execute_job(self, job_id: str, queue_id: str) -> None:
        """Execute a single job inside the semaphore's concurrency limit.

        All state transitions go through JobStateMachine.transition(), ensuring
        no bare `job.status = "..."` assignments anywhere in this flow.
        """
        async with self.semaphore:
            correlation_id = generate_correlation_id()
            started_at = datetime.now(timezone.utc)

            logger.info(
                "job_execution_started",
                job_id=job_id,
                queue_id=queue_id,
                correlation_id=correlation_id,
            )

            async with AsyncSessionLocal() as db:
                import uuid
                job_uuid = uuid.UUID(str(job_id)) if not isinstance(job_id, uuid.UUID) else job_id
                result = await db.execute(select(Job).where(Job.id == job_uuid))
                job = result.scalar_one_or_none()
                if not job:
                    logger.error("job_not_found_at_execution", job_id=job_id)
                    return

                # Create execution record
                execution = JobExecution(
                    job_id=job.id,
                    worker_id=self.worker_id,
                    attempt=job.current_attempt + 1,
                    status="running",
                    started_at=started_at,
                )
                db.add(execution)

                # Transition: claimed → running
                try:
                    JobStateMachine.transition(job, JobStatus.RUNNING)
                    job.current_attempt += 1
                    await db.flush()
                except InvalidTransitionError as e:
                    logger.error("invalid_transition_at_execution", error=str(e), job_id=job_id)
                    return

                try:
                    # ── Execute the job payload ──────────────────────────
                    # In production this would dispatch to a handler registry
                    # keyed by job.job_type or a field in job.payload.
                    result_data = await self._dispatch(job)

                    # Transition: running → completed
                    finished_at = datetime.now(timezone.utc)
                    JobStateMachine.transition(job, JobStatus.COMPLETED)
                    execution.status = "completed"
                    execution.finished_at = finished_at
                    execution.duration_seconds = (finished_at - started_at).total_seconds()

                    logger.info(
                        "job_execution_completed",
                        job_id=job_id,
                        attempt=job.current_attempt,
                        duration_seconds=execution.duration_seconds,
                    )
                    await db.commit()

                except Exception as exc:
                    finished_at = datetime.now(timezone.utc)
                    execution.status = "failed"
                    execution.finished_at = finished_at
                    execution.duration_seconds = (finished_at - started_at).total_seconds()
                    execution.error_message = str(exc)

                    logger.warning(
                        "job_execution_failed",
                        job_id=job_id,
                        attempt=job.current_attempt,
                        error=str(exc),
                    )

                    await self._handle_failure(db, job, execution, str(exc))

    async def _dispatch(self, job: Job) -> dict:
        """Dispatch a job to its handler.

        This is a simulation — replace with a real handler registry in
        production (e.g., a dict[str, Callable] keyed by job.job_type
        or a field in job.payload like payload["handler_name"]).
        """
        # Simulate async work; real implementations would call actual handlers
        await asyncio.sleep(0)
        return {"status": "ok"}

    async def _handle_failure(
        self, db: AsyncSession, job: Job, execution: JobExecution, error: str
    ) -> None:
        """Handle job failure: retry or move to DLQ atomically."""
        has_retries = job.current_attempt < job.max_retries

        if has_retries:
            # Compute retry delay via strategy pattern
            delay_ms = self._compute_retry_delay(job)
            retry_at = datetime.now(timezone.utc) + timedelta(milliseconds=delay_ms)

            # running → failed → retrying (two transitions)
            JobStateMachine.transition(job, JobStatus.FAILED)
            JobStateMachine.transition(job, JobStatus.RETRYING)
            job.run_at = retry_at

            logger.info(
                "job_retry_scheduled",
                job_id=str(job.id),
                attempt=job.current_attempt,
                retry_at=retry_at.isoformat(),
                delay_ms=delay_ms,
            )
        else:
            # Max retries exceeded — move to DLQ atomically in this transaction
            # running → failed → dead_letter_queue
            JobStateMachine.transition(job, JobStatus.FAILED)
            dlq_service = DLQService(db)
            await dlq_service.move_to_dlq(job, reason=error)

            logger.warning(
                "job_dead_lettered",
                job_id=str(job.id),
                total_attempts=job.current_attempt,
            )

        await db.commit()

    def _compute_retry_delay(self, job: Job) -> int:
        """Compute next retry delay via the job's retry policy strategy."""
        from backend.models.retry import RetryPolicy
        # In production: load policy from job.retry_policy_id
        # For now use defaults matching ExponentialBackoffWithJitter
        strategy = get_strategy("exponential_jitter")
        return strategy.next_delay_ms(
            attempt=job.current_attempt,
            initial_delay_ms=1000,
            max_delay_ms=60000,
            multiplier=2.0,
            jitter_factor=0.1,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Heartbeat loop — intentionally independent of job execution
    # ─────────────────────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Write heartbeats on a fixed interval regardless of job activity.

        Running as a separate asyncio task (not inline with job execution)
        means a hung or long-running job will NOT suppress heartbeats, so
        the reaper won't incorrectly declare this worker dead.
        """
        while self.running:
            await asyncio.sleep(settings.WORKER_HEARTBEAT_INTERVAL_SECONDS)
            try:
                async with AsyncSessionLocal() as db:
                    import uuid
                    worker_uuid = uuid.UUID(self.worker_id) if self.worker_id else None
                    # Write a heartbeat record
                    heartbeat = WorkerHeartbeat(
                        worker_id=worker_uuid,
                        last_seen=datetime.now(timezone.utc),
                    )
                    db.add(heartbeat)

                    # Update the worker's denormalised last_heartbeat for fast reaper queries
                    await db.execute(
                        update(Worker)
                        .where(Worker.id == worker_uuid)
                        .values(updated_at=datetime.now(timezone.utc))
                    )
                    await db.commit()

                logger.debug(
                    "heartbeat_sent",
                    worker_id=self.worker_id,
                    active_tasks=len(self._active_tasks),
                )
            except Exception as exc:
                logger.error("heartbeat_error", error=str(exc), exc_info=exc)

    # ─────────────────────────────────────────────────────────────────────
    # Dead-worker reaper
    # ─────────────────────────────────────────────────────────────────────

    async def _reaper_loop(self) -> None:
        """Detect stale workers and requeue their orphaned jobs.

        A worker is considered stale if its last heartbeat (WorkerHeartbeat.last_seen)
        is older than WORKER_REAPER_STALE_THRESHOLD_SECONDS.

        The self-exclusion (WHERE worker_id != self.worker_id) prevents a race
        where this worker requeues its own in-flight jobs while its heartbeat
        is briefly delayed.
        """
        while self.running:
            await asyncio.sleep(settings.WORKER_REAPER_INTERVAL_SECONDS)
            try:
                stale_threshold = datetime.now(timezone.utc) - timedelta(
                    seconds=settings.WORKER_REAPER_STALE_THRESHOLD_SECONDS
                )
                async with AsyncSessionLocal() as db:
                    # Find workers with stale heartbeats, excluding self
                    import uuid
                    self_worker_uuid = uuid.UUID(self.worker_id) if self.worker_id else None
                    stale_result = await db.execute(
                        select(Worker).where(
                            Worker.updated_at < stale_threshold,
                            Worker.status == "active",
                            Worker.id != self_worker_uuid,
                        )
                    )
                    stale_workers = stale_result.scalars().all()

                    for stale in stale_workers:
                        # Requeue all jobs claimed by this dead worker
                        requeue_result = await db.execute(
                            update(Job)
                            .where(
                                Job.worker_id == stale.id,
                                Job.status.in_([JobStatus.CLAIMED.value, JobStatus.RUNNING.value]),
                            )
                            .values(
                                status=JobStatus.QUEUED.value,
                                worker_id=None,
                                updated_at=datetime.now(timezone.utc),
                                run_at=datetime.now(timezone.utc),
                            )
                        )
                        requeued = requeue_result.rowcount

                        stale.status = "offline"
                        logger.warning(
                            "dead_worker_reaped",
                            worker_id=str(stale.id),
                            hostname=stale.hostname,
                            requeued_jobs=requeued,
                        )

                    if stale_workers:
                        await db.commit()

            except Exception as exc:
                logger.error("reaper_error", error=str(exc), exc_info=exc)

    # ─────────────────────────────────────────────────────────────────────
    # Graceful shutdown
    # ─────────────────────────────────────────────────────────────────────

    async def _shutdown(self) -> None:
        """Stop polling and wait for in-flight jobs to complete."""
        self.running = False
        logger.info(
            "worker_shutdown_initiated",
            active_tasks=len(self._active_tasks),
            timeout_seconds=settings.WORKER_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
        )

        if self._active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=settings.WORKER_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
                )
                logger.info("worker_shutdown_clean")
            except asyncio.TimeoutError:
                logger.warning(
                    "worker_shutdown_timeout",
                    remaining=len(self._active_tasks),
                )
                # Requeue jobs that didn't finish
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Job)
                        .where(
                            Job.worker_id == self.worker_id,
                            Job.status.in_([
                                JobStatus.CLAIMED.value,
                                JobStatus.RUNNING.value,
                            ]),
                        )
                        .values(
                            status=JobStatus.QUEUED.value,
                            worker_id=None,
                            updated_at=datetime.now(timezone.utc),
                        )
                    )
                    await db.execute(
                        update(Worker)
                        .where(Worker.id == self.worker_id)
                        .values(status="offline")
                    )
                    await db.commit()

        logger.info("worker_shutdown_complete")


# ─────────────────────────────────────────────────────────────────────────────
# Signal handling & entrypoint
# ─────────────────────────────────────────────────────────────────────────────

_worker: Optional[JobWorker] = None


def _handle_shutdown(signum, frame) -> None:
    """Signal handler — sets running=False, the gather() will clean up."""
    if _worker:
        logger.info("shutdown_signal_received", signal=signum)
        _worker.running = False


async def main() -> None:
    """Async entrypoint invoked by `python -m worker.main`."""
    global _worker
    _worker = JobWorker(
        hostname=settings.WORKER_NAME or socket.gethostname(),
        max_concurrent=settings.WORKER_MAX_CONCURRENT,
    )

    # Register OS signal handlers (best-effort on Windows)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_shutdown)
        except (OSError, ValueError):
            pass  # Windows may not support all signals

    await _worker.start()


if __name__ == "__main__":
    asyncio.run(main())
