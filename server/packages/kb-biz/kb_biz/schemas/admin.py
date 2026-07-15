from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# Department
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    parent_id: Optional[str] = None
    sort_order: int = 0
    description: Optional[str] = None
    tenant_id: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = None
    description: Optional[str] = None
    status: Optional[int] = None
    logo: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: str
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    milvus_partition: str
    parent_id: Optional[str] = None
    logo: Optional[str] = None
    status: int
    sort_order: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Role
class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    sort_order: int = 0
    permission_ids: list[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    permission_ids: Optional[list[str]] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool
    sort_order: int
    permission_ids: list[str] = []
    created_at: datetime
    updated_at: datetime


# User
class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=100)
    password: Optional[str] = None
    display_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    dept_id: Optional[str] = None
    role_ids: list[str] = []


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    dept_id: Optional[str] = None
    status: Optional[int] = None
    role_ids: Optional[list[str]] = None


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    avatar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    dept_id: Optional[str] = None
    dept_name: Optional[str] = None
    role_ids: list[str] = []
    role_names: list[str] = []
    status: int
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    group: str
    description: Optional[str] = None


# Menu
class MenuNode(BaseModel):
    id: str
    parent_id: Optional[str] = None
    name: str
    path: Optional[str] = None
    icon: Optional[str] = None
    permission_code: Optional[str] = None
    sort_order: int
    hidden: bool
    children: list[MenuNode] = []


class MenuCreate(BaseModel):
    parent_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    path: Optional[str] = None
    icon: Optional[str] = None
    permission_code: Optional[str] = None
    sort_order: int = 0
    hidden: bool = False


class MenuUpdate(BaseModel):
    parent_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    path: Optional[str] = None
    icon: Optional[str] = None
    permission_code: Optional[str] = None
    sort_order: Optional[int] = None
    hidden: Optional[bool] = None


class MenuRoleAssign(BaseModel):
    role_ids: list[str]


# Operation Logs
class OperationLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    display_name: Optional[str] = None
    dept_id: Optional[str] = None
    dept_name: Optional[str] = None
    action_type: str
    resource_type: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    detail: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    result: str
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime


class LoginLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    username: str
    display_name: Optional[str] = None
    login_type: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    result: str
    failure_reason: Optional[str] = None
    dept_id: Optional[str] = None
    dept_name: Optional[str] = None
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    created_at: datetime


# LLM Config
class LLMConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1, max_length=500)
    base_url: Optional[str] = None
    model: str = Field(..., min_length=1, max_length=100)
    max_tokens: int = 4096
    temperature: float = 1.0
    is_active: bool = False
    is_default: bool = False


class LLMConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class LLMConfigResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    name: str
    provider: str
    base_url: Optional[str] = None
    model: str
    max_tokens: int
    temperature: float
    is_active: bool
    is_default: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# Service Health
class ServiceHealthItem(BaseModel):
    name: str
    status: str  # "ok" | "degraded" | "down"
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


# Tenant
class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    logo: Optional[str] = None
    status: Optional[int] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    code: str
    milvus_partition: str
    status: int
    description: Optional[str] = None
    logo: Optional[str] = None
    created_by: Optional[str] = None
    admin_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TransferAdminRequest(BaseModel):
    user_id: str


class TenantInfoResponse(BaseModel):
    name: str
    logo: Optional[str] = None


class TenantInfoUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None


# Announcement
class AnnouncementResponse(BaseModel):
    id: str
    title: str
    content: str
    read: bool = False
    scope: str = "tenant"
    is_active: bool
    expires_at: Optional[datetime] = None
    created_by: Optional[str] = None
    tenant_id: Optional[str] = None
    dept_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AnnouncementReadResponse(BaseModel):
    id: str
    read: bool
    read_at: Optional[datetime] = None


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class AnnouncementReaderInfo(BaseModel):
    user_id: str
    display_name: str
    dept_name: Optional[str] = None
    read_at: datetime


class AnnouncementReadStatsResponse(BaseModel):
    announcement_id: str
    announcement_title: str
    total_read: int
    has_more: bool = False
    readers: list[AnnouncementReaderInfo]
