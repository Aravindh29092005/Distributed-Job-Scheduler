"""Dead Letter Queue model — stores jobs that exhausted all retry attempts."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy import Uuid as UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

# ---------------------------------------------------------------------------
# Forward references (import only for type-checking, avoids circular imports)
# ---------------------------------------------------------------------------
if TYPE_CHECKING:
    from backend.app.models.job import Job
    from backend.app.models.project import Project
    from backend.app.models.queue import Queue
    from backend.app.models.user import User


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class DeadLetterQueue(Base, UUIDMixin, TimestampMixin):
    """
    Stores jobs that have exhausted all retry attempts.

    ON DELETE behaviour:
    - job_id      → RESTRICT  : audit trail must be preserved
    - queue_id    → RESTRICT  : audit trail must be preserved
    - project_id  → RESTRICT  : audit trail must be preserved
    - resolved_by → SET NULL  : user may be deleted but entry stays
    """

    __tablename__ = "dead_letter_queue"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Original job that failed all retries",
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("queues.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Queue the job belonged to",
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Project the job belonged to",
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who manually resolved / requeued this entry",
    )

    # ------------------------------------------------------------------
    # Data columns
    # ------------------------------------------------------------------
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Job payload snapshot at time of final failure",
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable description of why the job was dead-lettered",
    )

    # ------------------------------------------------------------------
    # Lifecycle timestamps
    # ------------------------------------------------------------------
    failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the final failure occurred",
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the entry was manually resolved (NULL = unresolved)",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    job: Mapped[Job] = relationship("Job")
    queue: Mapped[Queue] = relationship("Queue")
    project: Mapped[Project] = relationship("Project")
    resolver: Mapped[Optional[User]] = relationship("User", foreign_keys=[resolved_by])
