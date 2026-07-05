"""Jobs router — create all 5 job types, list, detail, cancel, retry."""
from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db, get_current_user
from backend.core.security import TokenClaims
from backend.services.job import JobService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ─────────────────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    """Create a job of any of the 5 supported types.

    - immediate:  Runs as soon as a worker claims it (run_at = now).
    - delayed:    Runs at run_at timestamp.
    - scheduled:  Alias for delayed; intended for one-shot future jobs.
    - recurring:  Managed by the cron scheduler via ScheduledJob; submitted
                  jobs of this type are instances spawned by the scheduler.
    - batch:      Part of a batch group; provide batch_id to correlate.
    """
    queue_id: str
    project_id: str
    name: str = Field(min_length=1, max_length=255)
    job_type: str = Field(
        default="immediate",
        pattern="^(immediate|delayed|scheduled|recurring|batch)$",
    )
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=10)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    run_at: Optional[datetime] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=255)
    retry_policy_id: Optional[str] = None
    batch_id: Optional[str] = None
    max_retries: int = Field(default=3, ge=0, le=100)

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "queue_id": "550e8400-e29b-41d4-a716-446655440000",
                "project_id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "send-welcome-email",
                "job_type": "immediate",
                "payload": {"user_id": "u_123", "template": "welcome"},
                "priority": 5,
                "idempotency_key": "welcome-email-u_123",
            }]
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionResponse(BaseModel):
    id: str
    attempt: int
    status: str
    error_message: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    duration_seconds: Optional[float]
    created_at: str


class JobResponse(BaseModel):
    id: str
    queue_id: str
    project_id: str
    name: str
    job_type: str
    status: str
    payload: dict[str, Any]
    priority: int
    timeout_seconds: int
    current_attempt: int
    max_retries: int
    run_at: str
    created_at: str
    updated_at: str
    idempotency_key: Optional[str] = None
    batch_id: Optional[str] = None
    retry_policy_id: Optional[str] = None


class JobDetailResponse(JobResponse):
    executions: list[ExecutionResponse] = []


class JobListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[JobResponse]


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a job (all 5 types)")
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Submit a new job. Idempotency is enforced at the DB level on idempotency_key."""
    service = JobService(db)
    job = await service.create_job(
        queue_id=body.queue_id,
        project_id=body.project_id,
        name=body.name,
        job_type=body.job_type,
        payload=body.payload,
        priority=body.priority,
        timeout_seconds=body.timeout_seconds,
        run_at=body.run_at,
        idempotency_key=body.idempotency_key,
        retry_policy_id=body.retry_policy_id,
        batch_id=body.batch_id,
        max_retries=body.max_retries,
    )
    return _job_response(job)


@router.get("", response_model=JobListResponse, summary="List jobs")
async def list_jobs(
    queue_id: Optional[str] = None,
    project_id: Optional[str] = None,
    job_status: Optional[str] = Query(default=None, alias="status"),
    skip: int = 0,
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """List jobs with pagination. Filter by queue_id or project_id."""
    service = JobService(db)
    if queue_id:
        jobs, total = await service.list_by_queue(
            queue_id, skip=skip, limit=limit, status=job_status
        )
    elif project_id:
        jobs, total = await service.list_by_project(project_id, skip=skip, limit=limit)
    else:
        jobs, total = [], 0

    page = (skip // limit) + 1 if limit else 1
    return {
        "total": total,
        "page": page,
        "size": limit,
        "items": [_job_response(j) for j in jobs],
    }


@router.get("/{job_id}", response_model=JobDetailResponse, summary="Job detail with history")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Get a job with its full execution history and retry log."""
    service = JobService(db)
    job = await service.get(job_id)
    executions = await service.get_executions(job_id)
    result = _job_response(job)
    result["executions"] = [_exec_response(e) for e in executions]
    return result


@router.post("/{job_id}/cancel", summary="Cancel a job")
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Cancel a queued or scheduled job. Running jobs cannot be cancelled."""
    service = JobService(db)
    job = await service.cancel(job_id)
    return _job_response(job)


@router.post("/{job_id}/retry", summary="Manually retry a failed job")
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Manually retry a failed job by resetting it to queued status."""
    service = JobService(db)
    job = await service.manual_retry(job_id)
    return _job_response(job)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _job_response(job) -> dict:
    return {
        "id": str(job.id),
        "queue_id": str(job.queue_id),
        "project_id": str(job.project_id),
        "name": job.name,
        "job_type": job.job_type,
        "status": job.status,
        "payload": job.payload,
        "priority": job.priority,
        "timeout_seconds": job.timeout_seconds,
        "current_attempt": job.current_attempt,
        "max_retries": job.max_retries,
        "run_at": job.run_at.isoformat(),
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "idempotency_key": job.idempotency_key,
        "batch_id": str(job.batch_id) if job.batch_id else None,
        "retry_policy_id": str(job.retry_policy_id) if job.retry_policy_id else None,
    }


def _exec_response(e) -> dict:
    return {
        "id": str(e.id),
        "attempt": e.attempt,
        "status": e.status,
        "error_message": e.error_message,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        "duration_seconds": e.duration_seconds,
        "created_at": e.created_at.isoformat(),
    }
