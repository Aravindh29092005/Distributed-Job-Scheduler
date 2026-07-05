"""Organization and OrganizationMember models."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.project import Project
    from backend.app.models.user import User


# ---------------------------------------------------------------------------
# OrganizationMember  (defined first — referenced by Organization.members)
# ---------------------------------------------------------------------------

class OrganizationMember(Base, UUIDMixin, TimestampMixin):
    """
    Junction table — user ↔ organization with a named role.

    ON DELETE CASCADE from both sides: if the org or user is removed the
    membership record has no meaning and is pure child data.
    """

    __tablename__ = "organization_members"

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
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
        default="member",  # admin | member
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="members",
    )
    user: Mapped[User] = relationship("User")

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_user"),
    )


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class Organization(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Top-level tenant boundary.

    ON DELETE: soft-deleted only — hard deletes cascade to projects/members
    but are disallowed at the application layer once any jobs exist.
    """

    __tablename__ = "organizations"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    members: Mapped[list[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
