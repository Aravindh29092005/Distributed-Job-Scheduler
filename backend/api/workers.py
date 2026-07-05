"""Workers router — list active workers and their status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db, get_current_user
from backend.core.security import TokenClaims
from backend.models.worker import Worker

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.get("", summary="List workers")
async def list_workers(
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """List all registered workers and their current status."""
    result = await db.execute(
        select(Worker).order_by(Worker.created_at.desc())
    )
    workers = result.scalars().all()
    return [
        {
            "id": str(w.id),
            "hostname": w.hostname,
            "status": w.status,
            "concurrency_limit": w.concurrency_limit,
            "created_at": w.created_at.isoformat(),
            "updated_at": w.updated_at.isoformat(),
        }
        for w in workers
    ]


@router.get("/{worker_id}", summary="Get worker detail")
async def get_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Get a single worker by ID."""
    import uuid
    result = await db.execute(
        select(Worker).where(Worker.id == uuid.UUID(worker_id))
    )
    worker = result.scalar_one_or_none()
    if not worker:
        from backend.core.errors import NotFoundError
        raise NotFoundError("Worker", worker_id)
    return {
        "id": str(worker.id),
        "hostname": worker.hostname,
        "status": worker.status,
        "concurrency_limit": worker.concurrency_limit,
        "created_at": worker.created_at.isoformat(),
        "updated_at": worker.updated_at.isoformat(),
    }
