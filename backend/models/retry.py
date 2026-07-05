"""RetryPolicy model — configures backoff strategy per queue/job."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.project import Project


class RetryPolicy(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Named retry configuration attached to a project.

    strategy choices: fixed | linear | exponential | exponential_jitter

    ON DELETE RESTRICT on project_id — a policy cannot be removed while
    jobs still reference it (audit trail / reproducibility requirement).
    """

    __tablename__ = "retry_policies"

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
    strategy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="fixed",  # fixed | linear | exponential | exponential_jitter
    )
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    base_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project: Mapped[Project] = relationship("Project", back_populates="retry_policies")
