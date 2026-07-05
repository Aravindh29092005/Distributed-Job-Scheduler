from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.dependencies import get_db
from backend.app.services.job_service import MetricsService

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("", summary="Platform metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    svc = MetricsService(db)
    return await svc.get_dashboard_metrics()

@router.get("/jobs", summary="Job metrics")
async def get_jobs_metrics(db: AsyncSession = Depends(get_db)):
    svc = MetricsService(db)
    return await svc.get_dashboard_metrics()

@router.get("/queues", summary="Queue metrics")
async def get_queues_metrics(db: AsyncSession = Depends(get_db)):
    svc = MetricsService(db)
    return await svc.get_dashboard_metrics()

@router.get("/workers", summary="Worker metrics")
async def get_workers_metrics(db: AsyncSession = Depends(get_db)):
    svc = MetricsService(db)
    return await svc.get_dashboard_metrics()
