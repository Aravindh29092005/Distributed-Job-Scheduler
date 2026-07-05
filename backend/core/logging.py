"""Structured logging configuration with structlog."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict

import structlog

# Context variables for correlation ID and request tracking
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
_request_id: ContextVar[str] = ContextVar("request_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    _correlation_id.set(correlation_id)


def get_request_id() -> str:
    """Get current request ID from context."""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    _request_id.set(request_id)


def generate_request_id() -> str:
    """Generate new request ID."""
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    return request_id


def generate_correlation_id(existing_id: str = None) -> str:
    """Generate or reuse correlation ID."""
    if existing_id:
        set_correlation_id(existing_id)
        return existing_id
    
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    return correlation_id


# ═════════════════════════════════════════════════════════════════════════
# CONTEXT PROCESSORS
# ═════════════════════════════════════════════════════════════════════════


def add_context_fields(logger, name, event_dict):
    """Add correlation_id and request_id to all log events."""
    correlation_id = get_correlation_id()
    request_id = get_request_id()
    
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    if request_id:
        event_dict["request_id"] = request_id
    
    return event_dict


def add_timestamp(logger, name, event_dict):
    """Add timestamp to all log events."""
    import datetime
    event_dict["timestamp"] = datetime.datetime.utcnow().isoformat()
    return event_dict


# ═════════════════════════════════════════════════════════════════════════
# LOGGER SETUP
# ═════════════════════════════════════════════════════════════════════════


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure structlog for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to use JSON output (True) or pretty-print (False)
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
    )
    
    # Context processors
    processors = [
        add_context_fields,
        add_timestamp,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Bound logger instance
    """
    if name is None:
        name = "codity"
    return structlog.get_logger(name)


# ═════════════════════════════════════════════════════════════════════════
# STRUCTURED LOG HELPERS
# ═════════════════════════════════════════════════════════════════════════


def log_api_request(
    method: str,
    path: str,
    user_id: str = None,
    org_id: str = None,
    **kwargs
) -> None:
    """Log incoming API request."""
    logger = get_logger()
    logger.info(
        "api_request",
        method=method,
        path=path,
        user_id=user_id,
        org_id=org_id,
        **kwargs
    )


def log_api_response(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float = None,
    **kwargs
) -> None:
    """Log outgoing API response."""
    logger = get_logger()
    logger.info(
        "api_response",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_job_event(
    event: str,
    job_id: str,
    status: str = None,
    attempt: int = None,
    **kwargs
) -> None:
    """Log job lifecycle event."""
    logger = get_logger()
    logger.info(
        f"job_{event}",
        job_id=job_id,
        status=status,
        attempt=attempt,
        **kwargs
    )


def log_worker_event(
    event: str,
    worker_id: str,
    worker_name: str = None,
    **kwargs
) -> None:
    """Log worker lifecycle event."""
    logger = get_logger()
    logger.info(
        f"worker_{event}",
        worker_id=worker_id,
        worker_name=worker_name,
        **kwargs
    )


def log_error(
    error: str,
    exception: Exception = None,
    context: Dict[str, Any] = None,
    **kwargs
) -> None:
    """Log error with context."""
    logger = get_logger()
    logger.error(
        error,
        exc_info=exception,
        context=context or {},
        **kwargs
    )


def log_database_query(
    query: str,
    duration_ms: float = None,
    rows_affected: int = None,
    **kwargs
) -> None:
    """Log database query."""
    logger = get_logger()
    logger.debug(
        "database_query",
        query=query,
        duration_ms=duration_ms,
        rows_affected=rows_affected,
        **kwargs
    )
