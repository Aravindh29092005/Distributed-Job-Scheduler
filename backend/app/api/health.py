from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("", summary="Health check")
async def health():
    return {"status": "healthy", "environment": settings.ENVIRONMENT, "version": "1.0.0"}
