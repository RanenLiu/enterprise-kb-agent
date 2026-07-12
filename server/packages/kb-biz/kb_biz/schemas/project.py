from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    leader_ids: list[str]  # at least one leader required


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: str  # "department" | "tenant"
    tenant_id: Optional[str] = None
    dept_id: Optional[str] = None
    dept_name: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    leader_count: int = 0
    member_count: int = 0
    my_role: str = "viewer"  # "leader" | "member" | "viewer"


class ProjectDetailResponse(ProjectResponse):
    pass


class ProjectMemberAdd(BaseModel):
    user_ids: list[str]
    role: str = "member"  # "leader" | "member"


class ProjectMemberResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    joined_at: datetime
    user_name: str = ""
    dept_name: Optional[str] = None


class ProjectMemberRoleUpdate(BaseModel):
    role: str = "member"


class ProjectDowngrade(BaseModel):
    dept_id: str
