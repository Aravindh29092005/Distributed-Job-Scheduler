"""Queues and RetryPolicies routers."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db, get_current_user
from backend.core.security import TokenClaims
from backend.services.queue_retry import QueueService, RetryPolicyService

# ─────────────────────────────────────────────────────────────────────────────
# Queue Router
# ─────────────────────────────────────────────────────────────────────────────

queue_router = APIRouter(prefix="/api/queues", tags=["queues"])


class QueueCreate(BaseModel):
    project_id: str
    organization_id: str
    name: str = Field(min_length=1, max_length=255, examples=["high-priority-jobs"])
    description: Optional[str] = None
    priority: int = Field(default=0, ge=0, examples=[0])
    max_concurrent: int = Field(default=10, ge=1, examples=[10])


class QueueResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str]
    priority: int
    max_concurrent: int
    paused: bool
    created_at: str
    updated_at: str


@queue_router.post("", response_model=QueueResponse, status_code=status.HTTP_201_CREATED,
                   summary="Create queue",
                   openapi_extra={"requestBody": {"content": {"application/json": {
                       "examples": {"basic": {"value": {
                           "project_id": "uuid-here",
                           "organization_id": "uuid-here",
                           "name": "email-jobs",
                           "priority": 5,
                           "max_concurrent": 20,
                       }}}}}}})
async def create_queue(
    body: QueueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Create a queue inside a project."""
    service = QueueService(db)
    queue = await service.create(
        project_id=body.project_id,
        org_id=body.organization_id,
        name=body.name,
        description=body.description,
        priority=body.priority,
        max_concurrent=body.max_concurrent,
        user_id=current_user.sub,
    )
    return _queue_response(queue)


@queue_router.get("/{queue_id}", response_model=QueueResponse, summary="Get queue")
async def get_queue(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = QueueService(db)
    queue = await service.get(queue_id)
    return _queue_response(queue)


@queue_router.get("", response_model=list[QueueResponse], summary="List queues in project")
async def list_queues(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = QueueService(db)
    queues, _ = await service.list_by_project(project_id, skip=skip, limit=limit)
    return [_queue_response(q) for q in queues]


@queue_router.post("/{queue_id}/pause", summary="Pause queue")
async def pause_queue(
    queue_id: str,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Stop workers from claiming jobs from this queue."""
    service = QueueService(db)
    queue = await service.pause(queue_id, current_user.sub, org_id)
    return _queue_response(queue)


@queue_router.post("/{queue_id}/resume", summary="Resume queue")
async def resume_queue(
    queue_id: str,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Allow workers to resume claiming from this queue."""
    service = QueueService(db)
    queue = await service.resume(queue_id, current_user.sub, org_id)
    return _queue_response(queue)


@queue_router.get("/{queue_id}/stats", summary="Queue statistics")
async def queue_stats(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Return job count breakdown by status."""
    service = QueueService(db)
    return await service.get_stats(queue_id)


@queue_router.delete("/{queue_id}", status_code=status.HTTP_204_NO_CONTENT,
                     summary="Archive queue")
async def archive_queue(
    queue_id: str,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = QueueService(db)
    await service.archive(queue_id, org_id, current_user.sub)


def _queue_response(q) -> dict:
    return {
        "id": str(q.id),
        "project_id": str(q.project_id),
        "name": q.name,
        "description": q.description,
        "priority": q.priority,
        "max_concurrent": q.max_concurrent,
        "paused": q.paused,
        "created_at": q.created_at.isoformat(),
        "updated_at": q.updated_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# RetryPolicy Router
# ─────────────────────────────────────────────────────────────────────────────

retry_router = APIRouter(prefix="/api/retry-policies", tags=["retry-policies"])


class RetryPolicyCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=255, examples=["standard-backoff"])
    max_retries: int = Field(default=3, ge=0, le=100, examples=[3])
    strategy: str = Field(
        default="exponential",
        pattern="^(fixed|linear|exponential|exponential_jitter)$",
        examples=["exponential"],
    )
    base_delay_seconds: int = Field(default=5, ge=0, examples=[5])
    max_delay_seconds: int = Field(default=60, ge=0, examples=[60])


class RetryPolicyResponse(BaseModel):
    id: str
    project_id: str
    name: str
    max_retries: int
    strategy: str
    base_delay_seconds: int
    max_delay_seconds: int
    created_at: str
    updated_at: str


@retry_router.post("", response_model=RetryPolicyResponse, status_code=status.HTTP_201_CREATED,
                   summary="Create retry policy")
async def create_retry_policy(
    body: RetryPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = RetryPolicyService(db)
    policy = await service.create(
        project_id=body.project_id,
        name=body.name,
        max_retries=body.max_retries,
        strategy=body.strategy,
        base_delay_seconds=body.base_delay_seconds,
        max_delay_seconds=body.max_delay_seconds,
        user_id=current_user.sub,
    )
    return _policy_response(policy)


@retry_router.get("/{policy_id}", response_model=RetryPolicyResponse, summary="Get retry policy")
async def get_retry_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = RetryPolicyService(db)
    policy = await service.get(policy_id)
    return _policy_response(policy)


@retry_router.get("", response_model=list[RetryPolicyResponse],
                  summary="List retry policies in project")
async def list_retry_policies(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = RetryPolicyService(db)
    policies, _ = await service.list_by_project(project_id, skip=skip, limit=limit)
    return [_policy_response(p) for p in policies]


def _policy_response(p) -> dict:
    return {
        "id": str(p.id),
        "project_id": str(p.project_id),
        "name": p.name,
        "max_retries": p.max_retries,
        "strategy": p.strategy,
        "base_delay_seconds": p.base_delay_seconds,
        "max_delay_seconds": p.max_delay_seconds,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }
