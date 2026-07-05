"""Job State Machine package.

The JobStateMachine is the single enforcer of job status transitions.
No code outside this package should ever assign job.status directly.
"""
from backend.state_machine.machine import JobStateMachine, InvalidTransitionError, JobStatus

__all__ = ["JobStateMachine", "InvalidTransitionError", "JobStatus"]
