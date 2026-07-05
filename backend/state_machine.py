"""Job state machine for Stage 4 - defines valid job transitions."""

from enum import Enum
from typing import Set
from datetime import datetime, timezone

from backend.core.logging import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job status enum."""
    QUEUED = "Queued"
    SCHEDULED = "Scheduled"
    CLAIMED = "Claimed"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    RETRYING = "Retrying"
    DEAD_LETTER_QUEUE = "DeadLetterQueue"
    CANCELLED = "Cancelled"


class JobStateMachine:
    """
    Job state machine enforcing valid transitions.
    
    Valid transitions:
    - Queued → Claimed (worker claims job)
    - Claimed → Running (worker starts execution)
    - Running → Completed (job succeeds)
    - Running → Failed (job fails, no more retries)
    - Failed → Retrying (retry attempt scheduled)
    - Retrying → Queued (put back in queue)
    - Running → DeadLetterQueue (max retries exceeded)
    - Any → Cancelled (explicit cancellation)
    """

    # Define valid transitions
    VALID_TRANSITIONS = {
        JobStatus.QUEUED: {JobStatus.CLAIMED, JobStatus.CANCELLED},
        JobStatus.SCHEDULED: {JobStatus.QUEUED, JobStatus.CANCELLED},
        JobStatus.CLAIMED: {JobStatus.RUNNING, JobStatus.QUEUED},  # Can unclaim
        JobStatus.RUNNING: {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.DEAD_LETTER_QUEUE,
        },
        JobStatus.FAILED: {JobStatus.RETRYING, JobStatus.DEAD_LETTER_QUEUE},
        JobStatus.RETRYING: {JobStatus.QUEUED},
        JobStatus.DEAD_LETTER_QUEUE: set(),  # Terminal state
        JobStatus.COMPLETED: set(),  # Terminal state
        JobStatus.CANCELLED: set(),  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if transition is valid."""
        try:
            from_state = JobStatus(from_status)
            to_state = JobStatus(to_status)
            return to_state in cls.VALID_TRANSITIONS.get(from_state, set())
        except ValueError:
            return False

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if status is terminal (no further transitions)."""
        try:
            state = JobStatus(status)
            return len(cls.VALID_TRANSITIONS[state]) == 0
        except ValueError:
            return False

    @classmethod
    def is_running(cls, status: str) -> bool:
        """Check if job is actively running."""
        return status in (JobStatus.CLAIMED.value, JobStatus.RUNNING.value)

    @classmethod
    def is_queued(cls, status: str) -> bool:
        """Check if job is queued (ready to claim)."""
        return status == JobStatus.QUEUED.value

    @classmethod
    def log_transition(cls, job_id: str, from_status: str, to_status: str, reason: str = None):
        """Log state transition."""
        logger.info(
            "job_state_transition",
            job_id=job_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )


# Convenience type aliases
RunningStatuses = {JobStatus.CLAIMED.value, JobStatus.RUNNING.value}
TerminalStatuses = {JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.DEAD_LETTER_QUEUE.value, JobStatus.CANCELLED.value}
RetryableStatuses = {JobStatus.FAILED.value}  # Only failed jobs can retry
