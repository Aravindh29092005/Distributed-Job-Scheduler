"""Worker and WorkerHeartbeat models — cluster node registry."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


# ---------------------------------------------------------------------------
# WorkerHeartbeat  (defined first — referenced by Worker.heartbeats)
# ---------------------------------------------------------------------------

class WorkerHeartbeat(Base, UUIDMixin, TimestampMixin):
    """
    Periodic liveness signal written by each worker on its heartbeat interval.

    The dead-worker reaper queries:
        SELECT worker_id, MAX(last_seen) FROM worker_heartbeats
        WHERE last_seen < now() - REAP_THRESHOLD_SECONDS
        GROUP BY worker_id
    ix_worker_heartbeats_detect covers this query exactly.

    ON DELETE CASCADE from worker_id — heartbeats are pure operational data
    with no independent audit value.
    """

    __tablename__ = "worker_heartbeats"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_usage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    worker: Mapped[Worker] = relationship("Worker", back_populates="heartbeats")

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # ix_worker_heartbeats_detect — serves the dead-worker reaper query:
        #   SELECT worker_id, MAX(last_seen) FROM worker_heartbeats
        #   GROUP BY worker_id HAVING MAX(last_seen) < now() - interval
        Index("ix_worker_heartbeats_detect", "worker_id", "last_seen"),
    )


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

class Worker(Base, UUIDMixin, TimestampMixin):
    """
    Represents a single running worker process.

    Workers self-register on startup and write periodic heartbeats.
    The reaper marks a worker 'offline' when its heartbeat exceeds the
    configured REAP_THRESHOLD_SECONDS.
    """

    __tablename__ = "workers"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",  # active | idle | offline
    )
    concurrency_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    heartbeats: Mapped[list[WorkerHeartbeat]] = relationship(
        "WorkerHeartbeat",
        back_populates="worker",
        cascade="all, delete-orphan",
    )
