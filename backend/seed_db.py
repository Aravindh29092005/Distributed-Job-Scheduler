import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

sys.path.insert(0, ".")

from backend.db.session import AsyncSessionLocal
from backend.models.user import User
from backend.models.org import Organization, OrganizationMember
from backend.models.project import Project, ProjectMember
from backend.models.queue import Queue
from backend.models.retry import RetryPolicy
from backend.models.worker import Worker, WorkerHeartbeat
from backend.models.job import Job
from backend.models.execution import JobExecution, JobLog
from backend.models.dlq import DeadLetterQueue
from backend.core.security import hash_password

async def seed():
    print("Connecting to DB and starting seed process...")
    async with AsyncSessionLocal() as session:
        # 1. User
        email = "aravindh3@gmail.com"
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"Creating user {email}...")
            user = User(
                email=email,
                full_name="Aravindh Kumar",
                hashed_password=hash_password("password123"),
                is_active=True,
                is_superuser=False
            )
            session.add(user)
            await session.flush()
        else:
            print(f"User {email} already exists.")

        # 2. Org
        org_name = "Codity Global"
        result = await session.execute(select(Organization).where(Organization.name == org_name))
        org = result.scalar_one_or_none()
        if not org:
            print(f"Creating organization {org_name}...")
            org = Organization(name=org_name)
            session.add(org)
            await session.flush()
        else:
            print(f"Organization {org_name} already exists.")

        # 3. Org membership
        result = await session.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org.id)
            .where(OrganizationMember.user_id == user.id)
        )
        org_member = result.scalar_one_or_none()
        if not org_member:
            print(f"Adding user {email} to org {org_name} as admin...")
            org_member = OrganizationMember(
                organization_id=org.id,
                user_id=user.id,
                role="admin"
            )
            session.add(org_member)
            await session.flush()

        # 4. Project
        proj_name = "Production Workflows"
        result = await session.execute(
            select(Project)
            .where(Project.organization_id == org.id)
            .where(Project.name == proj_name)
        )
        project = result.scalar_one_or_none()
        if not project:
            print(f"Creating project {proj_name}...")
            project = Project(
                organization_id=org.id,
                name=proj_name
            )
            session.add(project)
            await session.flush()
        else:
            print(f"Project {proj_name} already exists.")

        # 5. Project membership
        result = await session.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project.id)
            .where(ProjectMember.user_id == user.id)
        )
        proj_member = result.scalar_one_or_none()
        if not proj_member:
            print(f"Adding user {email} to project {proj_name} as admin...")
            proj_member = ProjectMember(
                project_id=project.id,
                user_id=user.id,
                role="admin"
            )
            session.add(proj_member)
            await session.flush()

        # 6. Retry Policy
        rp_name = "Exponential Backoff Policy"
        result = await session.execute(
            select(RetryPolicy)
            .where(RetryPolicy.project_id == project.id)
            .where(RetryPolicy.name == rp_name)
        )
        retry_policy = result.scalar_one_or_none()
        if not retry_policy:
            print(f"Creating retry policy {rp_name}...")
            retry_policy = RetryPolicy(
                project_id=project.id,
                name=rp_name,
                strategy="exponential_jitter",
                max_retries=3,
                base_delay_seconds=5,
                max_delay_seconds=60
            )
            session.add(retry_policy)
            await session.flush()

        # 7. Queues
        q1_name = "high-priority"
        result = await session.execute(
            select(Queue)
            .where(Queue.project_id == project.id)
            .where(Queue.name == q1_name)
        )
        q_high = result.scalar_one_or_none()
        if not q_high:
            print(f"Creating queue {q1_name}...")
            q_high = Queue(
                project_id=project.id,
                name=q1_name,
                description="Immediate critical pipelines",
                priority=10,
                max_concurrent=10,
                paused=False
            )
            session.add(q_high)
            await session.flush()

        q2_name = "background-jobs"
        result = await session.execute(
            select(Queue)
            .where(Queue.project_id == project.id)
            .where(Queue.name == q2_name)
        )
        q_bg = result.scalar_one_or_none()
        if not q_bg:
            print(f"Creating queue {q2_name}...")
            q_bg = Queue(
                project_id=project.id,
                name=q2_name,
                description="Long-running, asynchronous processing workloads",
                priority=5,
                max_concurrent=5,
                paused=False
            )
            session.add(q_bg)
            await session.flush()

        # 8. Workers
        w1_host = "worker-node-alpha"
        result = await session.execute(select(Worker).where(Worker.hostname == w1_host))
        worker_alpha = result.scalar_one_or_none()
        if not worker_alpha:
            print(f"Creating worker {w1_host}...")
            worker_alpha = Worker(
                hostname=w1_host,
                status="active",
                concurrency_limit=10
            )
            session.add(worker_alpha)
            await session.flush()

            # Heartbeat
            hb = WorkerHeartbeat(
                worker_id=worker_alpha.id,
                last_seen=datetime.now(timezone.utc),
                cpu_usage=14.2,
                memory_usage=51.8
            )
            session.add(hb)

        w2_host = "worker-node-beta"
        result = await session.execute(select(Worker).where(Worker.hostname == w2_host))
        worker_beta = result.scalar_one_or_none()
        if not worker_beta:
            print(f"Creating worker {w2_host}...")
            worker_beta = Worker(
                hostname=w2_host,
                status="active",
                concurrency_limit=5
            )
            session.add(worker_beta)
            await session.flush()

            # Heartbeat
            hb = WorkerHeartbeat(
                worker_id=worker_beta.id,
                last_seen=datetime.now(timezone.utc),
                cpu_usage=8.5,
                memory_usage=32.1
            )
            session.add(hb)

        # 9. Jobs
        # Let's clean up existing jobs to start fresh
        print("Cleaning up old jobs to seed clean metrics...")
        await session.execute(text("DELETE FROM dead_letter_queue"))
        await session.execute(text("DELETE FROM job_logs"))
        await session.execute(text("DELETE FROM job_executions"))
        await session.execute(text("DELETE FROM jobs"))
        await session.flush()

        # Job 1: Completed immediate job
        now = datetime.now(timezone.utc)
        job1 = Job(
            queue_id=q_high.id,
            project_id=project.id,
            retry_policy_id=retry_policy.id,
            status="Completed",
            priority=8,
            run_at=now - timedelta(minutes=15),
            timeout_seconds=60,
            payload={"user_id": "u_9921", "amount": 1500.0, "invoice_id": "inv_8821a"},
            idempotency_key="stripe-charge-inv_8821a",
            max_retries=3,
            current_attempt=1
        )
        session.add(job1)
        await session.flush()

        exec1 = JobExecution(
            job_id=job1.id,
            worker_id=worker_alpha.id,
            attempt=1,
            status="Completed",
            started_at=now - timedelta(minutes=15),
            finished_at=now - timedelta(minutes=14, seconds=45),
            duration_seconds=15.0
        )
        session.add(exec1)
        await session.flush()

        log1 = JobLog(
            job_execution_id=exec1.id,
            log_level="INFO",
            message="Payment transaction sync initiated for inv_8821a"
        )
        log2 = JobLog(
            job_execution_id=exec1.id,
            log_level="INFO",
            message="Stripe API response code 200 OK. Transaction ID: ch_77ab23c"
        )
        log3 = JobLog(
            job_execution_id=exec1.id,
            log_level="INFO",
            message="Job execution completed successfully in 15s"
        )
        session.add_all([log1, log2, log3])

        # Job 2: Another Completed Job
        job2 = Job(
            queue_id=q_bg.id,
            project_id=project.id,
            retry_policy_id=retry_policy.id,
            status="Completed",
            priority=2,
            run_at=now - timedelta(hours=1),
            timeout_seconds=300,
            payload={"s3_bucket": "codity-assets", "prefix": "users/avatars/"},
            idempotency_key="s3-sync-avatars",
            max_retries=3,
            current_attempt=1
        )
        session.add(job2)
        await session.flush()

        exec2 = JobExecution(
            job_id=job2.id,
            worker_id=worker_beta.id,
            attempt=1,
            status="Completed",
            started_at=now - timedelta(hours=1),
            finished_at=now - timedelta(minutes=58),
            duration_seconds=120.0
        )
        session.add(exec2)
        await session.flush()

        # Job 3: Queued Job
        job3 = Job(
            queue_id=q_high.id,
            project_id=project.id,
            retry_policy_id=retry_policy.id,
            status="Queued",
            priority=9,
            run_at=now + timedelta(seconds=30),
            timeout_seconds=90,
            payload={"email": "customer@gmail.com", "template": "welcome_verification"},
            idempotency_key="welcome-verification-customer",
            max_retries=3,
            current_attempt=0
        )
        session.add(job3)

        # Job 4: Queued Job
        job4 = Job(
            queue_id=q_bg.id,
            project_id=project.id,
            retry_policy_id=retry_policy.id,
            status="Queued",
            priority=3,
            run_at=now + timedelta(minutes=5),
            timeout_seconds=600,
            payload={"report_type": "quarterly_earnings", "format": "pdf"},
            idempotency_key="quarterly-pdf-q2",
            max_retries=3,
            current_attempt=0
        )
        session.add(job4)

        # Job 5: Running Job
        job5 = Job(
            queue_id=q_bg.id,
            project_id=project.id,
            retry_policy_id=retry_policy.id,
            status="Running",
            priority=5,
            run_at=now - timedelta(minutes=3),
            timeout_seconds=300,
            payload={"target_db": "production_replica", "compress": True},
            idempotency_key="db-backup-daily",
            worker_id=worker_alpha.id,
            max_retries=3,
            current_attempt=1
        )
        session.add(job5)
        await session.flush()

        exec5 = JobExecution(
            job_id=job5.id,
            worker_id=worker_alpha.id,
            attempt=1,
            status="Running",
            started_at=now - timedelta(minutes=3)
        )
        session.add(exec5)
        await session.flush()

        log5_1 = JobLog(
            job_execution_id=exec5.id,
            log_level="INFO",
            message="Database replica snapshot acquired successfully."
        )
        log5_2 = JobLog(
            job_execution_id=exec5.id,
            log_level="INFO",
            message="Writing compressed tarball to cloud storage: codity-backups/daily/2026-07-05.tar.gz (45% done)"
        )
        session.add_all([log5_1, log5_2])

        # Job 6: Failed (with pending retry)
        job6 = Job(
            queue_id=q_high.id,
            project_id=project.id,
            retry_policy_id=retry_policy.id,
            status="Failed",
            priority=7,
            run_at=now - timedelta(minutes=2),
            timeout_seconds=60,
            payload={"api_url": "https://api.exchangerates.io/latest", "symbols": ["USD", "EUR"]},
            idempotency_key="currency-rates-fetch",
            max_retries=3,
            current_attempt=1
        )
        session.add(job6)
        await session.flush()

        exec6 = JobExecution(
            job_id=job6.id,
            worker_id=worker_alpha.id,
            attempt=1,
            status="Failed",
            started_at=now - timedelta(minutes=2),
            finished_at=now - timedelta(minutes=1, seconds=55),
            duration_seconds=5.0,
            error_message="HTTPConnectionError: Connection pool exhausted. Target host unreachable."
        )
        session.add(exec6)
        await session.flush()

        log6_1 = JobLog(
            job_execution_id=exec6.id,
            log_level="WARNING",
            message="HTTP Connection Timeout connecting to exchange rates API..."
        )
        log6_2 = JobLog(
            job_execution_id=exec6.id,
            log_level="ERROR",
            message="Job failed on attempt 1. Exception details: Connection pool exhausted."
        )
        session.add_all([log6_1, log6_2])

        # Job 7: Dead Letter Queue (max retries exhausted)
        job7 = Job(
            queue_id=q_bg.id,
            project_id=project.id,
            retry_policy_id=retry_policy.id,
            status="DeadLetterQueue",
            priority=1,
            run_at=now - timedelta(hours=2),
            timeout_seconds=120,
            payload={"legacy_id": "legacy_usr_8831", "target_table": "users_migrated"},
            idempotency_key="legacy-user-migration-usr_8831",
            max_retries=2,
            current_attempt=2
        )
        session.add(job7)
        await session.flush()

        # Attempt 1: Failed
        exec7_1 = JobExecution(
            job_id=job7.id,
            worker_id=worker_beta.id,
            attempt=1,
            status="Failed",
            started_at=now - timedelta(hours=2),
            finished_at=now - timedelta(hours=1, minutes=59),
            duration_seconds=60.0,
            error_message="DataValidationError: Expected non-null field 'username'."
        )
        session.add(exec7_1)

        # Attempt 2: Failed (Final attempt)
        exec7_2 = JobExecution(
            job_id=job7.id,
            worker_id=worker_beta.id,
            attempt=2,
            status="Failed",
            started_at=now - timedelta(hours=1, minutes=30),
            finished_at=now - timedelta(hours=1, minutes=29),
            duration_seconds=60.0,
            error_message="DataValidationError: Expected non-null field 'username'."
        )
        session.add(exec7_2)
        await session.flush()

        log7_1 = JobLog(
            job_execution_id=exec7_2.id,
            log_level="ERROR",
            message="JSON mapping error: field 'username' is missing in payload record legacy_usr_8831."
        )
        session.add(log7_1)

        # DLQ record
        dlq_item = DeadLetterQueue(
            job_id=job7.id,
            queue_id=q_bg.id,
            project_id=project.id,
            payload=job7.payload,
            reason="DataValidationError: Expected non-null field 'username'. Max retries (2) exhausted.",
            failed_at=now - timedelta(hours=1, minutes=29)
        )
        session.add(dlq_item)

        await session.commit()
        print("Database seeded successfully with beautiful job logs, histories, queues, and workers!")

if __name__ == "__main__":
    from sqlalchemy import text
    asyncio.run(seed())
