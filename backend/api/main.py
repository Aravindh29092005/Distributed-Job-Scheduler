"""Main FastAPI application entry point.

Architecture notes:
- Middleware registered in outer → inner order (last registered runs first).
- All business logic lives in services/, not here.
- Exception handlers map AppException → standard error envelope.
- OpenAPI docs available at /docs (Swagger) and /redoc.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.errors import AppException, NotFoundError
from backend.core.logging import configure_logging, get_logger
from backend.db.session import engine
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.middleware.request_id import RequestIDMiddleware

# Configure structured JSON logging at module load time
configure_logging(level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Application lifecycle
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown managed via async context manager (replaces @on_event)."""
    logger.info("api_server_starting", environment=settings.ENVIRONMENT)
    
    # Auto-create tables if running in SQLite fallback mode
    if engine.url.drivername == "sqlite+aiosqlite":
        logger.info("auto_creating_sqlite_tables_fallback")
        from backend.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    yield
    logger.info("api_server_shutdown")
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "Production-grade Distributed Job Scheduling Platform. "
        "Supports immediate, delayed, scheduled, recurring, and batch jobs "
        "backed by PostgreSQL with SELECT FOR UPDATE SKIP LOCKED claiming."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ─────────────────────────────────────────────────────────────────────────────
# Middleware (added in reverse order of execution — last added, first run)
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(RateLimitMiddleware)      # outermost: reject before processing
app.add_middleware(RequestIDMiddleware)     # inject IDs into all log lines

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Exception handlers — uniform error envelope: {"error": {"code", "message", "details"}}
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Map typed AppExceptions to the standard error envelope.

    Never exposes stack traces to clients.
    """
    logger.warning(
        "app_exception",
        error_code=exc.error_code,
        status_code=exc.status_code,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )



@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Convert UUID/value parse errors into 422 instead of leaking a 500."""
    msg = str(exc)
    logger.warning("value_error", error=msg, path=str(request.url))
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_INPUT",
                "message": msg or "Invalid value provided",
                "details": {},
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all to prevent raw tracebacks leaking to clients."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=str(request.url),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            }
        },
    )



# ─────────────────────────────────────────────────────────────────────────────
# Core endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"], summary="Health check")
async def health():
    """Lightweight liveness probe — returns immediately without DB I/O."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT, "version": "1.0.0"}


@app.get("/", tags=["system"], include_in_schema=False)
async def root():
    return {"message": "Distributed Job Scheduling Platform", "docs": "/docs"}


# ─────────────────────────────────────────────────────────────────────────────
# Feature routers
# ─────────────────────────────────────────────────────────────────────────────

from backend.api.auth import router as auth_router
from backend.api.organizations import router as org_router
from backend.api.projects import router as project_router
from backend.api.queues import queue_router, retry_router
from backend.api.jobs import router as job_router
from backend.api.workers import router as worker_router
from backend.api.dlq import router as dlq_router

app.include_router(auth_router)
app.include_router(org_router)
app.include_router(project_router)
app.include_router(queue_router)
app.include_router(retry_router)
app.include_router(job_router)
app.include_router(worker_router)
app.include_router(dlq_router)


# ─────────────────────────────────────────────────────────────────────────────
# Metrics endpoint (real DB queries via MetricsService)
# ─────────────────────────────────────────────────────────────────────────────

from backend.core.dependencies import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


@app.get("/api/metrics", tags=["metrics"], summary="Platform metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    """Return real-time job/worker/queue counts from the database.

    Polled by the frontend dashboard every 5 seconds.
    Future: expose as Prometheus /metrics with push-gateway integration.
    """
    from backend.services.job import MetricsService
    svc = MetricsService(db)
    return await svc.get_dashboard_metrics()


# ─────────────────────────────────────────────────────────────────────────────
# Dev runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )
