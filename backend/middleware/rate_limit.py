"""Token-bucket rate limiting middleware.

DESIGN: Token Bucket Algorithm
  - Each IP gets a bucket with capacity = RATE_LIMIT_BURST_SIZE tokens.
  - The bucket refills at RATE_LIMIT_TOKENS_PER_MINUTE / 60 tokens per second.
  - On each request: if tokens >= 1 → consume 1 and proceed; else → 429.
  - Stored in-process (dict); at scale, replace with Redis INCR + TTL.

WHY THIS MATTERS: An unthrottled job-creation endpoint is a direct
production risk — a single misbehaving client can fill the jobs table,
exhaust the worker pool, and starve legitimate tenants.

KNOWN LIMITATION: In-process storage means each API pod has its own bucket.
At N replicas the effective limit is N * RATE_LIMIT_TOKENS_PER_MINUTE.
The migration path is to replace the _buckets dict with Redis, requiring
no interface change in service code (the limit is enforced here, at the
edge, not in service logic).
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _Bucket:
    """Token bucket state for a single IP address."""
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP token-bucket rate limiter.

    Reads RATE_LIMIT_ENABLED and RATE_LIMIT_TOKENS_PER_MINUTE from settings.
    """

    _BURST_MULTIPLIER: float = 2.0   # Burst = 2× the per-minute rate

    def __init__(self, app, **kwargs) -> None:  # type: ignore[override]
        super().__init__(app, **kwargs)
        self._capacity: float = settings.RATE_LIMIT_TOKENS_PER_MINUTE * self._BURST_MULTIPLIER
        self._refill_rate: float = settings.RATE_LIMIT_TOKENS_PER_MINUTE / 60.0  # per second
        self._buckets: dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=self._capacity)
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, honouring X-Forwarded-For when behind a proxy."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _consume(self, ip: str) -> bool:
        """Attempt to consume one token for ``ip``.

        Returns True (request allowed) or False (rate limit exceeded).
        """
        now = time.monotonic()
        bucket = self._buckets[ip]

        # Refill based on elapsed time
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._refill_rate)
        bucket.last_refill = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        """Check and consume a rate-limit token before processing."""
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health and metrics endpoints
        if request.url.path in {"/health", "/metrics", "/api/metrics"}:
            return await call_next(request)

        ip = self._get_client_ip(request)
        if not self._consume(ip):
            logger.warning("rate_limit_exceeded", client_ip=ip, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down.",
                        "details": {
                            "limit_per_minute": settings.RATE_LIMIT_TOKENS_PER_MINUTE,
                            "retry_after_seconds": 60,
                        },
                    }
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
