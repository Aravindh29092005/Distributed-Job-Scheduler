"""Request ID & Correlation ID injection middleware.

Injects a unique X-Request-ID per HTTP request (generated here) and
propagates an X-Correlation-ID from upstream callers, generating one if
absent. Both IDs are stored in contextvars so they appear in every log
line emitted during the request lifecycle — including the worker's logs
for the same job (correlation_id is stored on the Job row and propagated
to the worker via the DB record).
"""
from __future__ import annotations

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.logger import (
    set_request_id,
    set_correlation_id,
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign and propagate request/correlation IDs for every HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        """Inject IDs before processing and expose them in response headers."""
        # Assign a fresh request-scoped ID
        request_id = str(uuid.uuid4())
        set_request_id(request_id)

        # Propagate or generate a correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_correlation_id(correlation_id)

        response: Response = await call_next(request)

        # Expose IDs in response headers so clients can correlate logs
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response
