"""Projects router."""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_db, get_current_user
from backend.app.core.security import TokenClaims
from backend.app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=1, max_length=255, examples=["backend-jobs"])
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED,
             summary="Create project")
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = ProjectService(db)
    project = await service.create(
        org_id=body.organization_id,
        name=body.name,
        description=body.description,
        user_id=uuid.UUID(current_user.sub),
    )
    return _to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = ProjectService(db)
    project = await service.get(project_id, uuid.UUID(current_user.sub))
    return _to_response(project)


@router.get("", response_model=list[ProjectResponse], summary="List projects in organization")
async def list_projects(
    org_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = ProjectService(db)
    projects, _ = await service.list_by_org(org_id, uuid.UUID(current_user.sub), skip=skip, limit=limit)
    return [_to_response(p) for p in projects]


def _to_response(p) -> dict:
    return {
        "id": str(p.id),
        "organization_id": str(p.organization_id),
        "name": p.name,
        "description": p.description,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }
