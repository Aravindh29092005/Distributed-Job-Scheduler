"""Shared SQLAlchemy base class and column mixins."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, func, text
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------

class UUIDMixin:
    """UUID primary key, generated client-side (uuid4) or server-side."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )


class TimestampMixin:
    """Timezone-aware created_at / updated_at audit columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """
    Soft-delete support via an archived_at timestamp.

    Records with archived_at IS NOT NULL are considered logically deleted.
    Hard deletes are intentionally avoided on entities with audit value.
    """

    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_archived(self) -> bool:
        """Return True when this record has been soft-deleted."""
        return self.archived_at is not None
