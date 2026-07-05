from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.dependencies import get_db
from backend.app.services.job_service import MetricsService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("", summary="Dashboard metrics")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    svc = MetricsService(db)
    return await svc.get_dashboard_metrics()
