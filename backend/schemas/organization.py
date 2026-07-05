"""Pydantic schemas for organizations and projects."""

from typing import List, Optional
from pydantic import BaseModel, Field


# ═════════════════════════════════════════════════════════════════════════
# ORGANIZATION
# ═════════════════════════════════════════════════════════════════════════


class OrganizationCreate(BaseModel):
    """Create organization request."""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    """Update organization request."""
    name: Optional[str] = None
    description: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════════════════════════════════
# ORGANIZATION MEMBERS
# ═════════════════════════════════════════════════════════════════════════


class AddOrgMemberRequest(BaseModel):
    """Add member to organization."""
    user_id: str
    role: str = Field(regex="^(admin|member|viewer)$", default="member")


class UpdateOrgMemberRequest(BaseModel):
    """Update organization member role."""
    role: str = Field(regex="^(admin|member|viewer)$")


class OrgMemberResponse(BaseModel):
    """Organization member response."""
    id: str
    user_id: str
    organization_id: str
    role: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════════════════════════════════
# PROJECTS
# ═════════════════════════════════════════════════════════════════════════


class ProjectCreate(BaseModel):
    """Create project request."""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Update project request."""
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ═════════════════════════════════════════════════════════════════════════
# PROJECT MEMBERS
# ═════════════════════════════════════════════════════════════════════════


class AddProjectMemberRequest(BaseModel):
    """Add member to project."""
    user_id: str
    role: str = Field(regex="^(admin|member|viewer)$", default="member")


class UpdateProjectMemberRequest(BaseModel):
    """Update project member role."""
    role: str = Field(regex="^(admin|member|viewer)$")


class ProjectMemberResponse(BaseModel):
    """Project member response."""
    id: str
    user_id: str
    project_id: str
    role: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
