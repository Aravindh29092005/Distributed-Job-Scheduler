"""Dead Letter Queue router — list entries and manual resubmission."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_db, get_current_user
from backend.app.core.security import TokenClaims
from backend.app.services.dead_letter_service import DLQService

router = APIRouter(prefix="/api/dlq", tags=["dead-letter-queue"])


@router.get("", summary="List DLQ entries")
async def list_dlq(
    project_id: Optional[str] = None,
    queue_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """List dead-lettered jobs. Filter by project, queue, or resolution status."""
    service = DLQService(db)
    entries, total = await service.list(
        project_id=project_id,
        queue_id=queue_id,
        resolved=resolved,
        skip=skip,
        limit=limit,
    )
    return {
        "total": total,
        "page": (skip // limit) + 1 if limit else 1,
        "size": limit,
        "items": [_entry_response(e) for e in entries],
    }


@router.post("/{dlq_id}/resubmit", summary="Resubmit DLQ entry")
async def resubmit_dlq_entry(
    dlq_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Manually resubmit a DLQ entry back to its original queue.

    Atomically transitions job back to 'queued' and marks the DLQ entry
    as resolved. The job will be picked up by the next available worker.
    """
    service = DLQService(db)
    job = await service.resubmit(dlq_id, current_user.sub)
    return {
        "message": "Job resubmitted successfully",
        "job_id": str(job.id),
        "status": job.status,
    }


def _entry_response(e) -> dict:
    return {
        "id": str(e.id),
        "job_id": str(e.job_id),
        "queue_id": str(e.queue_id),
        "project_id": str(e.project_id),
        "payload": e.payload,
        "reason": e.reason,
        "failed_at": e.failed_at.isoformat(),
        "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
        "resolved_by": str(e.resolved_by) if e.resolved_by else None,
        "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
    }
