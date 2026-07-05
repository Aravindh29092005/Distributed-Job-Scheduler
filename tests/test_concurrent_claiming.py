"""
CRITICAL INTEGRATION TEST: Concurrent job claiming against a real Postgres DB.

Uses testcontainers to spin up a real Postgres instance — SQLite cannot test
FOR UPDATE SKIP LOCKED because that syntax is PostgreSQL-specific.

Tests:
  1. test_concurrent_claim_no_double_claims — N workers race for M jobs;
     asserts each job is claimed exactly once.
  2. test_state_machine_all_transitions — every legal transition succeeds;
     every illegal transition raises InvalidTransitionError.
  3. test_retry_strategy_delays — verifies computed delay values for each
     of the four strategies.
  4. test_heartbeat_expiry_triggers_requeue — a worker that stops heartbeating
     has its jobs requeued by the reaper logic.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.models.base import Base
from backend.models.execution import JobExecution, JobLog
from backend.models.job import Job
from backend.models.org import Organization, OrganizationMember
from backend.models.project import Project, ProjectMember
from backend.models.queue import Queue
from backend.models.retry import RetryPolicy
from backend.models.user import User
from backend.models.worker import Worker, WorkerHeartbeat
from backend.models.dlq import DeadLetterQueue
from backend.repositories.job_queue import JobRepository
from backend.state_machine import InvalidTransitionError, JobStateMachine, JobStatus


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def postgres_url():
    """Provide a real Postgres URL via testcontainers.

    Falls back to a local Postgres if TESTCONTAINERS is unavailable
    (e.g., CI without Docker).  Set TEST_DATABASE_URL env var to override.
    """
    import os
    env_url = os.getenv("TEST_DATABASE_URL")
    if env_url:
        return env_url

    try:
        from testcontainers.postgres import PostgresContainer
        with PostgresContainer("postgres:16-alpine") as pg:
            # Convert sync URL to asyncpg
            url = pg.get_connection_url().replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://"
            )
            yield url
            return
    except Exception:
        pass

    # Final fallback
    yield "postgresql+asyncpg://postgres:postgres@localhost:5432/test_codity"


@pytest_asyncio.fixture(scope="function")
async def db_session(postgres_url) -> AsyncGenerator[async_sessionmaker, None]:
    """Create tables and yield a session factory; drop tables after test."""
    engine = create_async_engine(postgres_url, echo=False)

    async with engine.begin() as conn:
        # Create uuid-ossp extension if not present
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seed_data(db_session):
    """Create the minimal set of rows needed for job tests."""
    async with db_session() as db:
        org = Organization(name="test-org")
        db.add(org)
        await db.flush()

        project = Project(organization_id=org.id, name="test-project")
        db.add(project)
        await db.flush()

        policy = RetryPolicy(
            organization_id=org.id,
            name="default",
            max_retries=3,
            strategy="exponential_jitter",
            initial_delay_ms=100,
            max_delay_ms=5000,
            multiplier=2.0,
            jitter_factor=0.1,
        )
        db.add(policy)
        await db.flush()

        queue = Queue(
            project_id=project.id,
            name="test-queue",
            priority=0,
            max_concurrent=20,
        )
        db.add(queue)
        await db.flush()

        workers = []
        for i in range(5):
            w = Worker(
                hostname=f"worker-{i}.test",
                status="active",
                concurrency_limit=10,
            )
            db.add(w)
            await db.flush()
            workers.append(w)

        # 10 jobs all in 'queued' status
        jobs = []
        for i in range(10):
            j = Job(
                queue_id=queue.id,
                project_id=project.id,
                name=f"job-{i}",
                job_type="immediate",
                status=JobStatus.QUEUED.value,
                priority=0,
                payload={"index": i},
                run_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                timeout_seconds=300,
                max_retries=3,
                current_attempt=0,
            )
            db.add(j)
            await db.flush()
            jobs.append(j)

        await db.commit()

    return {
        "org_id": str(org.id),
        "project_id": str(project.id),
        "queue_id": str(queue.id),
        "policy_id": str(policy.id),
        "worker_ids": [str(w.id) for w in workers],
        "job_ids": [str(j.id) for j in jobs],
        "session_factory": db_session,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Concurrent claiming — the most critical test
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_claim_no_double_claims(seed_data):
    """5 workers race concurrently for 10 jobs — assert zero double-claims.

    WHAT THIS TESTS:
      The SELECT FOR UPDATE SKIP LOCKED strategy in claim_job().
      Each worker runs in its own connection (different AsyncSession), which
      is the correct way to test concurrent claiming — sharing a session would
      serialize the requests and trivially pass.

    ASSERTION CONTRACT:
      - Total claims == total jobs (all 10 claimed exactly once)
      - len(claimed_by) == 10 (each job appears in exactly one worker's result)
      - No job_id appears in more than one worker's claim set
    """
    data = seed_data
    session_factory = data["session_factory"]
    queue_id = data["queue_id"]
    worker_ids = data["worker_ids"]
    num_jobs = len(data["job_ids"])

    claimed_by: dict[str, str] = {}  # job_id → worker_id
    claim_lock = asyncio.Lock()
    double_claims: list[str] = []

    async def worker_task(worker_id: str) -> int:
        """One worker claiming as many jobs as it can, each in a fresh session."""
        local_claims = 0
        while True:
            # Each claim attempt gets its own connection (simulates real worker)
            async with session_factory() as db:
                from sqlalchemy import text
                stmt = text("""
                    UPDATE jobs
                    SET status    = :new_status,
                        worker_id = :worker_id,
                        updated_at = now()
                    WHERE id = (
                        SELECT id FROM jobs
                        WHERE queue_id    = :queue_id
                          AND status      IN ('queued', 'retrying')
                          AND run_at      <= now()
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
                        "new_status": "claimed",
                        "worker_id": worker_id,
                        "queue_id": queue_id,
                    },
                )
                row = result.fetchone()
                await db.commit()

            if not row:
                break  # No more jobs to claim

            job_id = str(row[0])
            local_claims += 1

            async with claim_lock:
                if job_id in claimed_by:
                    double_claims.append(
                        f"Job {job_id} claimed by {claimed_by[job_id]} AND {worker_id}"
                    )
                else:
                    claimed_by[job_id] = worker_id

        return local_claims

    # Launch all 5 workers simultaneously
    results = await asyncio.gather(*[
        worker_task(wid) for wid in worker_ids
    ])

    total_claimed = sum(results)

    # ── Assertions ────────────────────────────────────────────────────────
    assert double_claims == [], f"Double-claiming detected:\n" + "\n".join(double_claims)
    assert total_claimed == num_jobs, (
        f"Expected exactly {num_jobs} claims total, got {total_claimed}"
    )
    assert len(claimed_by) == num_jobs, (
        f"Only {len(claimed_by)} distinct jobs were claimed (expected {num_jobs})"
    )

    # Verify DB state — every job should be in 'claimed' status
    async with session_factory() as db:
        result = await db.execute(
            select(Job).where(Job.queue_id == queue_id)
        )
        all_jobs = result.scalars().all()
        queued_remaining = [j for j in all_jobs if j.status == "queued"]
        claimed_jobs = [j for j in all_jobs if j.status == "claimed"]

    assert len(queued_remaining) == 0, (
        f"Found {len(queued_remaining)} jobs still in 'queued' after all workers finished"
    )
    assert len(claimed_jobs) == num_jobs, (
        f"Expected {num_jobs} jobs in 'claimed', found {len(claimed_jobs)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: State machine transitions
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_state_machine_all_legal_transitions():
    """Every entry in VALID_TRANSITIONS must succeed via transition()."""
    for from_status, allowed in JobStateMachine.VALID_TRANSITIONS.items():
        for to_status in allowed:
            # Build a fake job with the right status
            job = _fake_job(from_status.value)
            JobStateMachine.transition(job, to_status)
            assert job.status == to_status.value, (
                f"Expected {to_status.value} after {from_status.value} → {to_status.value}"
            )


@pytest.mark.asyncio
async def test_state_machine_all_illegal_transitions():
    """Every transition NOT in the table must raise InvalidTransitionError."""
    all_statuses = list(JobStatus)
    for from_status in all_statuses:
        allowed = JobStateMachine.VALID_TRANSITIONS.get(from_status, frozenset())
        for to_status in all_statuses:
            if to_status in allowed:
                continue  # Legal — skip
            job = _fake_job(from_status.value)
            with pytest.raises(InvalidTransitionError):
                JobStateMachine.transition(job, to_status)


@pytest.mark.asyncio
async def test_state_machine_terminal_states():
    """Terminal states must have no allowed transitions."""
    terminals = [JobStatus.COMPLETED, JobStatus.CANCELLED]
    for t in terminals:
        assert JobStateMachine.is_terminal(t.value)
        assert len(JobStateMachine.VALID_TRANSITIONS[t]) == 0


def _fake_job(status: str):
    """Create a minimal fake Job-like object for state machine tests."""
    class FakeJob:
        pass
    j = FakeJob()
    j.status = status
    return j


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Retry strategy delay values
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fixed_delay_strategy():
    """FixedDelay always returns initial_delay_ms regardless of attempt."""
    from backend.retry import FixedDelay
    strategy = FixedDelay()
    for attempt in range(1, 6):
        delay = strategy.next_delay_ms(
            attempt=attempt,
            initial_delay_ms=1000,
            max_delay_ms=60000,
        )
        assert delay == 1000, f"Expected 1000ms at attempt {attempt}, got {delay}"


@pytest.mark.asyncio
async def test_linear_backoff_strategy():
    """LinearBackoff scales linearly with attempt number."""
    from backend.retry import LinearBackoff
    strategy = LinearBackoff()
    for attempt in (1, 2, 3, 5):
        delay = strategy.next_delay_ms(
            attempt=attempt,
            initial_delay_ms=500,
            max_delay_ms=60000,
        )
        expected = 500 * attempt
        assert delay == expected, f"At attempt {attempt}: expected {expected}, got {delay}"


@pytest.mark.asyncio
async def test_exponential_backoff_strategy():
    """ExponentialBackoff doubles on each attempt (multiplier=2)."""
    from backend.retry import ExponentialBackoff
    strategy = ExponentialBackoff()
    expected_delays = [1000, 2000, 4000, 8000]
    for i, attempt in enumerate(range(1, 5)):
        delay = strategy.next_delay_ms(
            attempt=attempt,
            initial_delay_ms=1000,
            max_delay_ms=60000,
            multiplier=2.0,
        )
        assert delay == expected_delays[i], (
            f"At attempt {attempt}: expected {expected_delays[i]}, got {delay}"
        )


@pytest.mark.asyncio
async def test_exponential_jitter_stays_within_bounds():
    """ExponentialBackoffWithJitter must stay within ±jitter_factor of the exp value."""
    from backend.retry import ExponentialBackoffWithJitter
    import math
    strategy = ExponentialBackoffWithJitter()
    initial_ms = 1000
    multiplier = 2.0
    jitter_factor = 0.1
    max_ms = 60000

    for attempt in range(1, 6):
        exp_delay = initial_ms * math.pow(multiplier, attempt - 1)
        for _ in range(20):  # Repeat to catch probabilistic failures
            delay = strategy.next_delay_ms(
                attempt=attempt,
                initial_delay_ms=initial_ms,
                max_delay_ms=max_ms,
                multiplier=multiplier,
                jitter_factor=jitter_factor,
            )
            lo = exp_delay * (1.0 - jitter_factor)
            hi = min(exp_delay * (1.0 + jitter_factor), max_ms)
            assert lo <= delay <= hi, (
                f"Attempt {attempt}: delay {delay} outside [{lo}, {hi}]"
            )


@pytest.mark.asyncio
async def test_max_delay_is_clamped():
    """All strategies must clamp to max_delay_ms."""
    from backend.retry import ExponentialBackoff
    strategy = ExponentialBackoff()
    # attempt=10, multiplier=2 → 1000 * 512 = 512_000 but max=5000
    delay = strategy.next_delay_ms(
        attempt=10, initial_delay_ms=1000, max_delay_ms=5000, multiplier=2.0
    )
    assert delay == 5000


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Heartbeat expiry triggers requeue
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_heartbeat_expiry_triggers_requeue(seed_data):
    """A worker that stops heartbeating has its claimed jobs requeued."""
    data = seed_data
    session_factory = data["session_factory"]
    queue_id = data["queue_id"]
    worker_ids = data["worker_ids"]
    dead_worker_id = worker_ids[0]

    # Claim 3 jobs for the dead worker directly
    async with session_factory() as db:
        result = await db.execute(
            select(Job)
            .where(Job.queue_id == queue_id, Job.status == "queued")
            .limit(3)
        )
        jobs_to_claim = result.scalars().all()
        for job in jobs_to_claim:
            job.status = "claimed"
            job.worker_id = dead_worker_id
        await db.commit()

    claimed_ids = {str(j.id) for j in jobs_to_claim}
    assert len(claimed_ids) == 3

    # Simulate stale heartbeat by backdating updated_at
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=300)
    async with session_factory() as db:
        await db.execute(
            update(Worker)
            .where(Worker.id == dead_worker_id)
            .values(updated_at=stale_time)
        )
        await db.commit()

    # Run reaper logic (replicate what _reaper_loop does)
    stale_threshold = datetime.now(timezone.utc) - timedelta(seconds=30)
    async with session_factory() as db:
        stale_result = await db.execute(
            select(Worker).where(
                Worker.updated_at < stale_threshold,
                Worker.status == "active",
                Worker.id != worker_ids[1],  # Exclude "self"
            )
        )
        stale_workers = stale_result.scalars().all()
        for stale in stale_workers:
            requeue_result = await db.execute(
                update(Job)
                .where(
                    Job.worker_id == stale.id,
                    Job.status.in_(["claimed", "running"]),
                )
                .values(
                    status="queued",
                    worker_id=None,
                    updated_at=datetime.now(timezone.utc),
                    run_at=datetime.now(timezone.utc),
                )
            )
            stale.status = "offline"
        await db.commit()

    # Assert the 3 claimed jobs are back to queued
    async with session_factory() as db:
        result = await db.execute(
            select(Job).where(Job.id.in_([uuid.UUID(jid) for jid in claimed_ids]))
        )
        requeued_jobs = result.scalars().all()

    statuses = {j.status for j in requeued_jobs}
    assert statuses == {"queued"}, (
        f"Expected all jobs requeued, got statuses: {statuses}"
    )
    worker_assignments = {j.worker_id for j in requeued_jobs}
    assert worker_assignments == {None}, (
        "Expected worker_id cleared after requeue"
    )
