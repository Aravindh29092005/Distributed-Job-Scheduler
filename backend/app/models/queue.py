"""Queue model — job-routing container scoped to a project."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.job import Job
    from backend.app.models.project import Project


class Queue(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    A named job queue belonging to a project.

    Soft-deleted only — RESTRICT on project_id prevents removal while
    jobs still reference this queue, preserving execution history.
    """

    __tablename__ = "queues"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(
        String(1000), nullable=True, default=""
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    max_concurrent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )
    paused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped[Project] = relationship("Project", back_populates="queues")
    jobs: Mapped[list[Job]] = relationship("Job", back_populates="queue")
