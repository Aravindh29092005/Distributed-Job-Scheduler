"""Organization router — CRUD + membership management."""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_db, get_current_user
from backend.core.security import TokenClaims
from backend.core.errors import AppException
from backend.services.org_project import OrganizationService

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


# --- Schemas ---

class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Acme Corp"])


class OrgMemberAdd(BaseModel):
    user_id: str
    role: str = Field(default="member", pattern="^(admin|member)$")


class OrgResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# --- Routes ---

@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED,
             summary="Create organization",
             openapi_extra={"requestBody": {"content": {"application/json": {
                 "examples": {"basic": {"value": {"name": "Acme Corp"}}}}}}})
async def create_organization(
    body: OrgCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Create a new organization. The authenticated user becomes its admin."""
    service = OrganizationService(db)
    org = await service.create(name=body.name, owner_user_id=uuid.UUID(current_user.sub))
    return _to_response(org)


@router.get("", response_model=list[OrgResponse], summary="List my organizations")
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """List organizations the authenticated user belongs to."""
    service = OrganizationService(db)
    orgs, _ = await service.list_for_user(uuid.UUID(current_user.sub), skip=skip, limit=limit)
    return [_to_response(o) for o in orgs]


@router.get("/{org_id}", response_model=OrgResponse, summary="Get organization")
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    service = OrganizationService(db)
    org = await service.get(org_id, uuid.UUID(current_user.sub))
    return _to_response(org)


@router.post("/{org_id}/members", status_code=status.HTTP_201_CREATED,
             summary="Add organization member")
async def add_member(
    org_id: str,
    body: OrgMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Add a user to the organization. Requester must be an admin."""
    service = OrganizationService(db)
    member = await service.add_member(
        org_id=org_id,
        target_user_id=body.user_id,
        role=body.role,
        requester_id=uuid.UUID(current_user.sub),
    )
    return {"id": str(member.id), "user_id": str(member.user_id), "role": member.role}


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Archive organization")
async def archive_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenClaims = Depends(get_current_user),
):
    """Soft-delete the organization. Requester must be an admin."""
    service = OrganizationService(db)
    await service.archive(org_id, uuid.UUID(current_user.sub))


def _to_response(org) -> dict:
    return {
        "id": str(org.id),
        "name": org.name,
        "created_at": org.created_at.isoformat(),
        "updated_at": org.updated_at.isoformat(),
    }
