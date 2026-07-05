"""ScheduledJob model — cron-based recurring job template."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Uuid as UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.project import Project
    from backend.app.models.queue import Queue
    from backend.app.models.retry_policy import RetryPolicy


class ScheduledJob(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Cron-driven template that spawns a new Job on each tick.

    The worker's cron-dispatcher reads active ScheduledJobs where
    next_run_at <= now(), creates a Job row, then advances next_run_at
    using croniter.

    ON DELETE RESTRICT on queue/project/retry_policy — same audit rationale
    as Job. Soft-deleted (archived_at) when deactivated permanently.
    """

    __tablename__ = "scheduled_jobs"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retry_policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("retry_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Schedule definition
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron_expression: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Standard 5-field cron expression, evaluated via croniter",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ------------------------------------------------------------------
    # Job template fields
    # ------------------------------------------------------------------
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # ------------------------------------------------------------------
    # Execution tracking
    # ------------------------------------------------------------------
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped[Project] = relationship("Project")
    queue: Mapped[Queue] = relationship("Queue")
    retry_policy: Mapped[Optional[RetryPolicy]] = relationship("RetryPolicy")
