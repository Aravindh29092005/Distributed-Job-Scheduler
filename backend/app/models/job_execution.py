"""JobExecution and JobLog models — immutable attempt history."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.job import Job
    from backend.app.models.worker import Worker


# ---------------------------------------------------------------------------
# JobLog  (defined first — referenced by JobExecution.logs)
# ---------------------------------------------------------------------------

class JobLog(Base, UUIDMixin, TimestampMixin):
    """
    Granular log line emitted during a JobExecution.

    ON DELETE CASCADE from job_execution_id — logs are pure child data with
    no independent audit value beyond the execution record itself.
    """

    __tablename__ = "job_logs"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    job_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("job_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    log_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="INFO",  # DEBUG | INFO | WARNING | ERROR
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    execution: Mapped[JobExecution] = relationship(
        "JobExecution",
        back_populates="logs",
    )


# ---------------------------------------------------------------------------
# JobExecution
# ---------------------------------------------------------------------------

class JobExecution(Base, UUIDMixin, TimestampMixin):
    """
    Immutable record of a single execution attempt for a Job.

    A new row is inserted for each attempt — previous attempts are never
    overwritten (audit requirement). duration_seconds is computed from
    started_at / finished_at and stored for quick aggregation.

    ON DELETE:
    - job_id    → RESTRICT  : execution history is part of the audit trail
    - worker_id → SET NULL  : ephemeral workers may be deregistered; history stays
    """

    __tablename__ = "job_executions"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Attempt metadata
    # ------------------------------------------------------------------
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # running | completed | failed
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    job: Mapped[Job] = relationship("Job", back_populates="executions")
    worker: Mapped[Optional[Worker]] = relationship("Worker")
    logs: Mapped[list[JobLog]] = relationship(
        "JobLog",
        back_populates="execution",
        cascade="all, delete-orphan",
    )
