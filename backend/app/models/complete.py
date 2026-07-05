"""
SQLAlchemy ORM Models - Complete Schema

Includes:
- All table definitions with proper relationships
- Composite indexes with query justification
- Constraints and cascade behaviors
- Soft-delete support (archived_at)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    DateTime, String, Text, Integer, Float, Boolean, JSON, UUID,
    ForeignKey, Index, UniqueConstraint, CheckConstraint, func, text,
    Column, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID as PG_UUID

from backend.app.models.base import Base, UUIDMixin, TimestampMixin


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════

class JobType(str, Enum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    BATCH = "batch"


class JobStatus(str, Enum):
    QUEUED = "Queued"
    SCHEDULED = "Scheduled"
    CLAIMED = "Claimed"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    RETRYING = "Retrying"
    DEAD_LETTER_QUEUE = "DeadLetterQueue"
    CANCELLED = "Cancelled"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RetryStrategy(str, Enum):
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear"
    EXPONENTIAL_BACKOFF = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ═══════════════════════════════════════════════════════════════════════════
# USERS & AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════

class User(Base, UUIDMixin, TimestampMixin):
    """User account (authentication)."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    organization_memberships: Mapped[List[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    project_memberships: Mapped[List[ProjectMember]] = relationship(
        "ProjectMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("email ~ '^[^@]+@[^@]+$'", name="ck_user_email_format"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# ORGANIZATIONS & MULTI-TENANCY
# ═══════════════════════════════════════════════════════════════════════════

class Organization(Base, UUIDMixin, TimestampMixin):
    """Organization (tenant)."""
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    members: Mapped[List[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    projects: Mapped[List[Project]] = relationship(
        "Project",
        back_populates="organization",
    )
    retry_policies: Mapped[List[RetryPolicy]] = relationship(
        "RetryPolicy",
        back_populates="organization",
    )


class OrganizationMember(Base, UUIDMixin, TimestampMixin):
    """User role within an organization."""
    __tablename__ = "organization_members"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.MEMBER,
        nullable=False,
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="members",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="organization_memberships",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# PROJECTS
# ═══════════════════════════════════════════════════════════════════════════

class Project(Base, UUIDMixin, TimestampMixin):
    """Project (logical grouping of queues/jobs)."""
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="projects",
    )
    members: Mapped[List[ProjectMember]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    queues: Mapped[List[Queue]] = relationship(
        "Queue",
        back_populates="project",
    )
    jobs: Mapped[List[Job]] = relationship(
        "Job",
        back_populates="project",
    )
    scheduled_jobs: Mapped[List[ScheduledJob]] = relationship(
        "ScheduledJob",
        back_populates="project",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_project_name"),
        Index("idx_project_org_created", "organization_id", "created_at"),
    )


class ProjectMember(Base, UUIDMixin, TimestampMixin):
    """User role within a project."""
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.MEMBER,
        nullable=False,
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="members",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="project_memberships",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# QUEUES & RETRY POLICIES
# ═══════════════════════════════════════════════════════════════════════════

class Queue(Base, UUIDMixin, TimestampMixin):
    """Job queue with concurrency limits and priority."""
    __tablename__ = "queues"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_concurrent: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )
    paused: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="queues")
    jobs: Mapped[List[Job]] = relationship("Job", back_populates="queue")

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_queue_name"),
        CheckConstraint("max_concurrent >= 1", name="ck_queue_max_concurrent"),
        CheckConstraint("priority >= 0", name="ck_queue_priority"),
        Index("idx_queue_project_created", "project_id", "created_at"),
    )


class RetryPolicy(Base, UUIDMixin, TimestampMixin):
    """Retry strategy configuration."""
    __tablename__ = "retry_policies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    strategy: Mapped[RetryStrategy] = mapped_column(
        SQLEnum(RetryStrategy),
        default=RetryStrategy.EXPONENTIAL_JITTER,
        nullable=False,
    )
    initial_delay_ms: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
    )
    max_delay_ms: Mapped[int] = mapped_column(
        Integer,
        default=60000,
        nullable=False,
    )
    multiplier: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    jitter_factor: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="retry_policies",
    )
    jobs: Mapped[List[Job]] = relationship("Job", back_populates="retry_policy")

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_retry_policy_name"),
        CheckConstraint("max_retries >= 0", name="ck_retry_max"),
        CheckConstraint("initial_delay_ms >= 0", name="ck_retry_initial_delay"),
        CheckConstraint("max_delay_ms >= initial_delay_ms", name="ck_retry_max_delay"),
        CheckConstraint("multiplier > 1.0", name="ck_retry_multiplier"),
        CheckConstraint("jitter_factor >= 0.0 AND jitter_factor <= 1.0", name="ck_retry_jitter"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# JOBS & EXECUTIONS
# ═══════════════════════════════════════════════════════════════════════════

class Job(Base, UUIDMixin, TimestampMixin):
    """Work unit in the system."""
    __tablename__ = "jobs"

    queue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    retry_policy_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("retry_policies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID,
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID,
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType),
        default=JobType.IMMEDIATE,
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )

    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,
        nullable=False,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        default=uuid.uuid4,
        nullable=False,
        index=True,
    )

    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    queue: Mapped[Queue] = relationship("Queue", back_populates="jobs")
    project: Mapped[Project] = relationship("Project", back_populates="jobs")
    retry_policy: Mapped[RetryPolicy] = relationship("RetryPolicy", back_populates="jobs")
    worker: Mapped[Optional[Worker]] = relationship("Worker", back_populates="claimed_jobs")
    executions: Mapped[List[JobExecution]] = relationship(
        "JobExecution",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # CRITICAL: Job claim query - find oldest queued job in queue
        Index(
            "idx_job_claim",
            "queue_id",
            "status",
            "created_at",
            postgresql_where="status = 'Queued' AND archived_at IS NULL",
        ),
        # Job list by project (dashboard)
        Index(
            "idx_job_project_created",
            "project_id",
            "created_at",
            postgresql_where="archived_at IS NULL",
        ),
        # Batch job tracking
        Index(
            "idx_job_batch_status",
            "batch_id",
            "status",
            postgresql_where="batch_id IS NOT NULL",
        ),
        CheckConstraint("timeout_seconds > 0", name="ck_job_timeout"),
        CheckConstraint("priority >= 0 AND priority <= 10", name="ck_job_priority"),
    )


class ScheduledJob(Base, UUIDMixin, TimestampMixin):
    """Recurring job template (cron)."""
    __tablename__ = "scheduled_jobs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    retry_policy_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("retry_policies.id", ondelete="RESTRICT"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_template: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="scheduled_jobs")
    queue: Mapped[Queue] = relationship("Queue")
    retry_policy: Mapped[RetryPolicy] = relationship("RetryPolicy")


class JobExecution(Base, UUIDMixin):
    """Single execution attempt of a job."""
    __tablename__ = "job_executions"

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID,
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus),
        default=ExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="executions")
    worker: Mapped[Optional[Worker]] = relationship("Worker")
    logs: Mapped[List[JobLog]] = relationship(
        "JobLog",
        back_populates="execution",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Execution history lookup
        Index("idx_execution_job_created", "job_id", "created_at"),
        CheckConstraint("attempt_number > 0", name="ck_execution_attempt"),
    )


class JobLog(Base, UUIDMixin):
    """Structured log from job execution."""
    __tablename__ = "job_logs"

    job_execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("job_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[LogLevel] = mapped_column(
        SQLEnum(LogLevel),
        default=LogLevel.INFO,
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    execution: Mapped[JobExecution] = relationship(
        "JobExecution",
        back_populates="logs",
    )

    __table_args__ = (
        # Log streaming for a job execution
        Index("idx_log_execution_created", "job_execution_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# WORKERS
# ═══════════════════════════════════════════════════════════════════════════

class Worker(Base, UUIDMixin, TimestampMixin):
    """Worker process registration."""
    __tablename__ = "workers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    claimed_jobs: Mapped[List[Job]] = relationship(
        "Job",
        back_populates="worker",
    )
    heartbeats: Mapped[List[WorkerHeartbeat]] = relationship(
        "WorkerHeartbeat",
        back_populates="worker",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("host", "port", name="uq_worker_addr"),
        # Dead-worker detection: find stale heartbeats
        Index(
            "idx_worker_heartbeat",
            "last_heartbeat",
            postgresql_where="archived_at IS NULL",
        ),
    )


class WorkerHeartbeat(Base, UUIDMixin):
    """Periodic "still alive" signal from worker."""
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    worker: Mapped[Worker] = relationship(
        "Worker",
        back_populates="heartbeats",
    )

    __table_args__ = (
        Index("idx_heartbeat_worker_created", "worker_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# DEAD LETTER QUEUE
# ═══════════════════════════════════════════════════════════════════════════

class DeadLetterQueue(Base, UUIDMixin, TimestampMixin):
    """Jobs that failed permanently and need manual intervention."""
    __tablename__ = "dead_letter_queue"

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID,
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    final_attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    final_error: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    job: Mapped[Job] = relationship("Job")
    queue: Mapped[Queue] = relationship("Queue")
