"""Job State Machine — single authoritative enforcer of valid status transitions.

DESIGN DECISION: Why a state machine package instead of ad-hoc status checks?
  - All transitions go through transition(), making illegal moves impossible
    to miss in code review — any direct `job.status = ...` is a red flag.
  - The VALID_TRANSITIONS table is the canonical, reviewable specification
    of the lifecycle. It lives in one place and is trivially testable.
  - Typed InvalidTransitionError lets callers distinguish transition errors
    from any other exception, enabling precise HTTP 409 responses.

Transition table (→ means "can transition to"):
  queued      → claimed, cancelled
  scheduled   → queued, cancelled
  claimed     → running, queued (unclaim on worker death)
  running     → completed, failed, dead_letter_queue
  failed      → retrying, dead_letter_queue
  retrying    → claimed
  completed   → (terminal)
  cancelled   → (terminal)
  dead_letter_queue → queued  (manual DLQ resubmission)
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.job import Job


# ---------------------------------------------------------------------------
# Canonical status enum — single definition; import from here everywhere.
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    """All valid statuses a Job can be in."""
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER_QUEUE = "dead_letter_queue"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class InvalidTransitionError(Exception):
    """Raised when code attempts an illegal job status transition.

    Args:
        from_status: The current (source) status.
        to_status:   The requested (destination) status.
    """

    def __init__(self, from_status: str, to_status: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid job status transition: {from_status!r} → {to_status!r}"
        )


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class JobStateMachine:
    """Enforces valid job status transitions via an explicit transition table.

    Usage::

        from backend.state_machine import JobStateMachine, JobStatus

        # In a service method that holds the ORM session:
        JobStateMachine.transition(job, JobStatus.CLAIMED)
        await db.flush()

    The machine mutates `job.status` only after validating the transition,
    so callers never need to (and must never) write `job.status = "..."`.
    """

    # Each key maps to the set of statuses it is allowed to transition *to*.
    VALID_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
        JobStatus.QUEUED: frozenset({
            JobStatus.CLAIMED,
            JobStatus.SCHEDULED,
            JobStatus.CANCELLED,
        }),
        JobStatus.SCHEDULED: frozenset({
            JobStatus.QUEUED,
            JobStatus.CANCELLED,
        }),
        JobStatus.CLAIMED: frozenset({
            JobStatus.RUNNING,
            JobStatus.QUEUED,   # unclaim on worker crash / reaper
            JobStatus.FAILED,   # claim → fail if pre-flight check dies
        }),
        JobStatus.RUNNING: frozenset({
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.DEAD_LETTER_QUEUE,
        }),
        JobStatus.FAILED: frozenset({
            JobStatus.RETRYING,
            JobStatus.DEAD_LETTER_QUEUE,
        }),
        JobStatus.RETRYING: frozenset({
            JobStatus.CLAIMED,
        }),
        JobStatus.DEAD_LETTER_QUEUE: frozenset({
            JobStatus.QUEUED,  # manual resubmission from DLQ
        }),
        JobStatus.COMPLETED: frozenset(),   # terminal
        JobStatus.CANCELLED: frozenset(),   # terminal
    }

    # Statuses that are considered "active" for concurrency limit accounting.
    ACTIVE_STATUSES: frozenset[JobStatus] = frozenset({
        JobStatus.CLAIMED,
        JobStatus.RUNNING,
    })

    # Statuses eligible for worker polling.
    POLLABLE_STATUSES: frozenset[JobStatus] = frozenset({
        JobStatus.QUEUED,
        JobStatus.RETRYING,
    })

    # --------------------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------------------

    @classmethod
    def transition(cls, job: "Job", to_status: JobStatus) -> None:
        """Validate and apply a status transition to an ORM Job instance.

        Mutates ``job.status`` in-place.  Raises ``InvalidTransitionError``
        before touching the object if the transition is not allowed.

        Args:
            job:       The ORM Job whose status will be changed.
            to_status: The target JobStatus enum member.

        Raises:
            InvalidTransitionError: if the transition is not in the table.
        """
        try:
            from_status = JobStatus(job.status)
        except ValueError:
            raise InvalidTransitionError(job.status, to_status.value)

        allowed = cls.VALID_TRANSITIONS.get(from_status, frozenset())
        if to_status not in allowed:
            raise InvalidTransitionError(from_status.value, to_status.value)

        job.status = to_status.value

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Pure predicate — does not mutate anything.

        Args:
            from_status: Current status string.
            to_status:   Desired status string.

        Returns:
            True iff the transition is in the table.
        """
        try:
            src = JobStatus(from_status)
            dst = JobStatus(to_status)
        except ValueError:
            return False
        return dst in cls.VALID_TRANSITIONS.get(src, frozenset())

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Return True when no further transitions are possible."""
        try:
            s = JobStatus(status)
        except ValueError:
            return False
        return len(cls.VALID_TRANSITIONS.get(s, frozenset())) == 0

    @classmethod
    def is_active(cls, status: str) -> bool:
        """Return True when the job is actively using a worker slot."""
        try:
            return JobStatus(status) in cls.ACTIVE_STATUSES
        except ValueError:
            return False

    @classmethod
    def is_pollable(cls, status: str) -> bool:
        """Return True when the job is eligible to be claimed by a worker."""
        try:
            return JobStatus(status) in cls.POLLABLE_STATUSES
        except ValueError:
            return False
