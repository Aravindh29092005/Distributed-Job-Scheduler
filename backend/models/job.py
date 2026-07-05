"""Job model — core scheduling unit with full state-machine lifecycle."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy import Uuid as UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.execution import JobExecution
    from backend.models.project import Project
    from backend.models.queue import Queue
    from backend.models.retry import RetryPolicy


class Job(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    A unit of work submitted to a queue for execution by a worker.

    Status lifecycle (enforced by JobStateMachine):
        queued → scheduled → claimed → running → completed
                                          ↓
                                       failed → retrying → claimed → …
                                          ↓
                                      dead_letter_queue

    ON DELETE RESTRICT on queue/project/retry_policy — jobs preserve
    execution history and must never be orphaned.
    Soft-deleted via archived_at once auditing is no longer needed.
    """

    __tablename__ = "jobs"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retry_policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("retry_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        default=uuid.uuid4,
        nullable=False,
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

    # ------------------------------------------------------------------
    # Scheduling columns
    # ------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="queued",
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="job")
    job_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="immediate"
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # ------------------------------------------------------------------
    # Payload & metadata
    # ------------------------------------------------------------------
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID, nullable=True, index=True
    )

    # ------------------------------------------------------------------
    # Retry tracking
    # ------------------------------------------------------------------
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    current_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    queue: Mapped[Queue] = relationship("Queue", back_populates="jobs")
    project: Mapped[Project] = relationship("Project")
    retry_policy: Mapped[Optional[RetryPolicy]] = relationship("RetryPolicy")
    executions: Mapped[list[JobExecution]] = relationship(
        "JobExecution",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Indexes & constraints
    # ------------------------------------------------------------------
    __table_args__ = (
        # Enforces idempotency at the DB level — app catches IntegrityError
        UniqueConstraint("project_id", "idempotency_key", name="uq_project_idempotency"),
        # ix_jobs_poll_claim — serves the worker polling query:
        #   SELECT ... FROM jobs WHERE queue_id=? AND status IN ('queued','retrying')
        #   AND run_at <= now() ORDER BY priority DESC, run_at ASC FOR UPDATE SKIP LOCKED
        Index(
            "ix_jobs_poll_claim",
            "queue_id",
            "status",
            "run_at",
            postgresql_where="status = 'queued' OR status = 'retrying'",
        ),
        # ix_jobs_project_created — serves the dashboard list/filter view:
        #   SELECT ... FROM jobs WHERE project_id=? ORDER BY created_at DESC
        Index("ix_jobs_project_created", "project_id", "created_at"),
    )
