"""Pydantic schemas for jobs, queues, and retry policies."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ═════════════════════════════════════════════════════════════════════════
# QUEUES
# ═════════════════════════════════════════════════════════════════════════


class QueueCreate(BaseModel):
    """Create queue request."""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    priority: int = Field(default=0, ge=0)
    max_concurrent: int = Field(default=10, ge=1)


class QueueUpdate(BaseModel):
    """Update queue request."""
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    max_concurrent: Optional[int] = None
    paused: Optional[bool] = None


class QueueResponse(BaseModel):
    """Queue response."""
    id: str
    project_id: str
    name: str
    description: Optional[str]
    priority: int
    max_concurrent: int
    paused: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class QueueStatsResponse(BaseModel):
    """Queue statistics."""
    id: str
    name: str
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int
    total_processed: int


# ═════════════════════════════════════════════════════════════════════════
# RETRY POLICIES
# ═════════════════════════════════════════════════════════════════════════


class RetryPolicyCreate(BaseModel):
    """Create retry policy request."""
    name: str = Field(min_length=1, max_length=255)
    max_retries: int = Field(default=3, ge=0, le=100)
    strategy: str = Field(default="exponential_jitter", regex="^(fixed_delay|linear|exponential|exponential_jitter)$")
    initial_delay_ms: int = Field(default=1000, ge=0)
    max_delay_ms: int = Field(default=60000, ge=0)
    multiplier: float = Field(default=2.0, gt=1.0)
    jitter_factor: float = Field(default=0.1, ge=0.0, le=1.0)


class RetryPolicyUpdate(BaseModel):
    """Update retry policy request."""
    name: Optional[str] = None
    max_retries: Optional[int] = None
    strategy: Optional[str] = None
    initial_delay_ms: Optional[int] = None
    max_delay_ms: Optional[int] = None
    multiplier: Optional[float] = None
    jitter_factor: Optional[float] = None


class RetryPolicyResponse(BaseModel):
    """Retry policy response."""
    id: str
    organization_id: str
    name: str
    max_retries: int
    strategy: str
    initial_delay_ms: int
    max_delay_ms: int
    multiplier: float
    jitter_factor: float
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════════════════════════════════
# JOBS
# ═════════════════════════════════════════════════════════════════════════


class JobCreate(BaseModel):
    """Create job request."""
    name: str = Field(min_length=1, max_length=255)
    queue_id: str
    job_type: str = Field(default="immediate", regex="^(immediate|delayed|scheduled|recurring|batch)$")
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=10)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    run_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    retry_policy_id: Optional[str] = None
    batch_id: Optional[str] = None


class JobUpdate(BaseModel):
    """Update job request (limited fields)."""
    priority: Optional[int] = None
    run_at: Optional[datetime] = None


class JobResponse(BaseModel):
    """Job response."""
    id: str
    queue_id: str
    project_id: str
    name: str
    job_type: str
    status: str
    payload: Dict[str, Any]
    priority: int
    timeout_seconds: int
    correlation_id: str
    claimed_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    """Job detail with execution history."""
    execution_history: List["ExecutionResponse"] = []
    worker_name: Optional[str] = None
    retry_policy: Optional[RetryPolicyResponse] = None


class JobListResponse(BaseModel):
    """Job list response."""
    total: int
    page: int
    size: int
    items: List[JobResponse]


# ═════════════════════════════════════════════════════════════════════════
# JOB EXECUTIONS
# ═════════════════════════════════════════════════════════════════════════


class ExecutionResponse(BaseModel):
    """Job execution response."""
    id: str
    job_id: str
    attempt_number: int
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════════════════════════════════
# JOB LOGS
# ═════════════════════════════════════════════════════════════════════════


class JobLogResponse(BaseModel):
    """Job log entry response."""
    id: str
    job_execution_id: str
    level: str
    message: str
    context: Optional[Dict[str, Any]]
    correlation_id: str
    created_at: str

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════════════════════════════════
# DEAD LETTER QUEUE
# ═════════════════════════════════════════════════════════════════════════


class DLQResponse(BaseModel):
    """Dead letter queue entry response."""
    id: str
    job_id: str
    queue_id: str
    job_name: str
    final_attempt_number: int
    final_error: str
    payload: Dict[str, Any]
    created_at: str


class DLQListResponse(BaseModel):
    """DLQ list response."""
    total: int
    page: int
    size: int
    items: List[DLQResponse]


class ManualRetryRequest(BaseModel):
    """Manually retry DLQ entry request."""
    dlq_id: str
