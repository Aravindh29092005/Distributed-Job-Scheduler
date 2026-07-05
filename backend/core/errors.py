"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


# ═════════════════════════════════════════════════════════════════════════
# AUTHENTICATION & AUTHORIZATION
# ═════════════════════════════════════════════════════════════════════════


class AuthenticationError(AppException):
    """Authentication failed (invalid credentials, expired token)."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message=message, status_code=401, **kwargs)


class AuthorizationError(AppException):
    """User not authorized to perform action (insufficient role)."""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message=message, status_code=403, **kwargs)


class InvalidTokenError(AuthenticationError):
    """Token is invalid or malformed."""
    
    def __init__(self, message: str = "Invalid or expired token", **kwargs):
        super().__init__(message=message, **kwargs)


class EmailAlreadyExistsError(AppException):
    """Email already registered."""
    
    def __init__(self, email: str, **kwargs):
        super().__init__(
            message=f"Email {email} already registered",
            status_code=409,
            **kwargs
        )


# ═════════════════════════════════════════════════════════════════════════
# RESOURCE NOT FOUND
# ═════════════════════════════════════════════════════════════════════════


class NotFoundError(AppException):
    """Resource not found."""
    
    def __init__(self, resource: str, resource_id: str, **kwargs):
        super().__init__(
            message=f"{resource} with id {resource_id} not found",
            status_code=404,
            **kwargs
        )


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: str, **kwargs):
        super().__init__("User", user_id, **kwargs)


class OrganizationNotFoundError(NotFoundError):
    def __init__(self, org_id: str, **kwargs):
        super().__init__("Organization", org_id, **kwargs)


class ProjectNotFoundError(NotFoundError):
    def __init__(self, project_id: str, **kwargs):
        super().__init__("Project", project_id, **kwargs)


class QueueNotFoundError(NotFoundError):
    def __init__(self, queue_id: str, **kwargs):
        super().__init__("Queue", queue_id, **kwargs)


class JobNotFoundError(NotFoundError):
    def __init__(self, job_id: str, **kwargs):
        super().__init__("Job", job_id, **kwargs)


class WorkerNotFoundError(NotFoundError):
    def __init__(self, worker_id: str, **kwargs):
        super().__init__("Worker", worker_id, **kwargs)


# ═════════════════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ═════════════════════════════════════════════════════════════════════════


class ValidationError(AppException):
    """Input validation failed."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, status_code=400, **kwargs)


class InvalidJobStatusTransitionError(ValidationError):
    """Job status transition not allowed."""
    
    def __init__(self, current_status: str, requested_status: str, **kwargs):
        super().__init__(
            message=f"Cannot transition from {current_status} to {requested_status}",
            **kwargs
        )


class QueuePausedError(ValidationError):
    """Queue is paused, cannot accept jobs."""
    
    def __init__(self, queue_name: str, **kwargs):
        super().__init__(
            message=f"Queue '{queue_name}' is paused",
            **kwargs
        )


class MaxRetriesExceededError(ValidationError):
    """Job exceeded max retry attempts."""
    
    def __init__(self, job_id: str, max_retries: int, **kwargs):
        super().__init__(
            message=f"Job {job_id} exceeded max retries ({max_retries})",
            **kwargs
        )


class IdempotencyError(ValidationError):
    """Idempotency key conflict."""
    
    def __init__(self, idempotency_key: str, existing_job_id: str, **kwargs):
        super().__init__(
            message=f"Job already exists with idempotency_key={idempotency_key}",
            details={"existing_job_id": existing_job_id},
            **kwargs
        )


# ═════════════════════════════════════════════════════════════════════════
# DATABASE & CONCURRENCY
# ═════════════════════════════════════════════════════════════════════════


class DatabaseError(AppException):
    """Database operation failed."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, status_code=500, **kwargs)


class IntegrityConstraintError(DatabaseError):
    """Unique constraint or foreign key violation."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, **kwargs)


class ConcurrencyError(AppException):
    """Concurrent access conflict."""
    
    def __init__(self, message: str = "Concurrent access conflict", **kwargs):
        super().__init__(message=message, status_code=409, **kwargs)


# ═════════════════════════════════════════════════════════════════════════
# WORKER & JOB EXECUTION
# ═════════════════════════════════════════════════════════════════════════


class WorkerError(AppException):
    """Worker operation failed."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, status_code=500, **kwargs)


class NoAvailableWorkerError(WorkerError):
    """No worker available to claim job."""
    
    def __init__(self, queue_name: str, **kwargs):
        super().__init__(
            message=f"No available worker in queue '{queue_name}'",
            **kwargs
        )


class JobExecutionError(WorkerError):
    """Job execution failed."""
    
    def __init__(self, job_id: str, error: str, **kwargs):
        super().__init__(
            message=f"Job {job_id} execution failed: {error}",
            **kwargs
        )
