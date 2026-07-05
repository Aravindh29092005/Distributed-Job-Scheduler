"""Domain entities — pure Python dataclasses, no ORM or framework imports."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class OrganizationEntity:
    """Domain representation of an Organization."""
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.archived_at is None


@dataclass
class ProjectEntity:
    """Domain representation of a Project."""
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.archived_at is None


@dataclass
class QueueEntity:
    """Domain representation of a Queue."""
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    priority: int
    max_concurrent: int
    paused: bool
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.archived_at is None and not self.paused


@dataclass
class JobEntity:
    """Domain representation of a Job.

    Status is a plain string here; the authoritative validation lives in
    JobStateMachine. The domain entity is a value object that carries data.
    """
    id: uuid.UUID
    queue_id: uuid.UUID
    project_id: uuid.UUID
    status: str
    job_type: str
    priority: int
    payload: dict[str, Any]
    run_at: datetime
    timeout_seconds: int
    current_attempt: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    retry_policy_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    idempotency_key: Optional[str] = None
    worker_id: Optional[uuid.UUID] = None
    archived_at: Optional[datetime] = None

    @property
    def has_retries_remaining(self) -> bool:
        return self.current_attempt < self.max_retries

    @property
    def is_terminal(self) -> bool:
        return self.status in {"completed", "cancelled", "dead_letter_queue"}


@dataclass
class WorkerEntity:
    """Domain representation of a Worker node."""
    id: uuid.UUID
    hostname: str
    status: str
    concurrency_limit: int
    created_at: datetime
    updated_at: datetime
    last_heartbeat: Optional[datetime] = None

    @property
    def is_alive(self) -> bool:
        return self.status == "active"


@dataclass
class DLQEntry:
    """Domain representation of a Dead Letter Queue entry."""
    id: uuid.UUID
    job_id: uuid.UUID
    queue_id: uuid.UUID
    project_id: uuid.UUID
    payload: dict[str, Any]
    reason: str
    failed_at: datetime
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[uuid.UUID] = None

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None
