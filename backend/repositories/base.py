"""Base repository with common CRUD operations."""

import uuid as _uuid
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


def _coerce_uuid(value: Any) -> Any:
    """Convert str / UUID to uuid.UUID so SQLAlchemy's Uuid column type
    can call .hex without raising AttributeError on SQLite.

    Returns the value unchanged if it is not a str or UUID (e.g. int PK).
    """
    if isinstance(value, _uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return _uuid.UUID(value)
        except (ValueError, AttributeError):
            pass
    return value


class BaseRepository(Generic[T]):
    """Base repository for common CRUD operations."""

    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model = model

    async def create(self, obj_in: dict) -> T:
        """Create new entity."""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_by_id(self, id: Any) -> Optional[T]:
        """Get entity by ID.  Coerces str IDs to uuid.UUID automatically."""
        return await self.db.get(self.model, _coerce_uuid(id))

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        where=None,
        order_by=None,
    ) -> tuple[List[T], int]:
        """List entities with pagination."""
        # Build query
        query = select(self.model)
        if where is not None:
            query = query.where(where)

        # Count total
        count_query = select(func.count()).select_from(self.model)
        if where is not None:
            count_query = count_query.where(where)
        total = await self.db.scalar(count_query)

        # Add order and pagination
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        items = result.scalars().all()
        return items, total

    async def update(self, id: str, obj_in: dict) -> Optional[T]:
        """Update entity."""
        obj = await self.get_by_id(id)
        if not obj:
            return None

        for key, value in obj_in.items():
            setattr(obj, key, value)

        await self.db.flush()
        return obj

    async def delete(self, id: str) -> bool:
        """Delete entity."""
        obj = await self.get_by_id(id)
        if not obj:
            return False

        await self.db.delete(obj)
        await self.db.flush()
        return True

    async def soft_delete(self, id: str) -> Optional[T]:
        """Soft delete (archive) entity with archived_at timestamp."""
        from datetime import datetime, timezone

        obj = await self.get_by_id(id)
        if not obj:
            return None

        if hasattr(obj, "archived_at"):
            obj.archived_at = datetime.now(timezone.utc)
            await self.db.flush()

        return obj
