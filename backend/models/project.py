"""Project and ProjectMember models."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.org import Organization
    from backend.models.queue import Queue
    from backend.models.retry import RetryPolicy
    from backend.models.user import User


# ---------------------------------------------------------------------------
# ProjectMember  (defined first — referenced by Project.members)
# ---------------------------------------------------------------------------

class ProjectMember(Base, UUIDMixin, TimestampMixin):
    """
    Junction table — user ↔ project with a named role.

    ON DELETE CASCADE from both sides: membership is pure child data.
    """

    __tablename__ = "project_members"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="member",  # admin | member | viewer
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped[Project] = relationship("Project", back_populates="members")
    user: Mapped[User] = relationship("User")

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class Project(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Logical grouping of queues, retry policies, and jobs within an org.

    ON DELETE CASCADE from organization — a project belongs entirely to its
    org and has no meaning without it. Queues / jobs within a project use
    RESTRICT to prevent accidental data loss.
    """

    __tablename__ = "projects"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="projects",
    )
    members: Mapped[list[ProjectMember]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    queues: Mapped[list[Queue]] = relationship(
        "Queue",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    retry_policies: Mapped[list[RetryPolicy]] = relationship(
        "RetryPolicy",
        back_populates="project",
        cascade="all, delete-orphan",
    )
