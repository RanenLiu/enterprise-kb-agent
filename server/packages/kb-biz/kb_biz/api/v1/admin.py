from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import delete, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.config.settings import settings
from kb_biz.core.auth.deps import PermissionChecker, RoleChecker, get_current_user
from kb_biz.core.auth.password import hash_password
import kb_biz.services.instances as _instances
from kb_biz.core.user_cache import set_cached_user, invalidate_user
from kb_biz.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from kb_biz.core.limits import MAX_DEPARTMENTS, MAX_USERS
from kb_biz.core.operation_log import record_operation
from kb_biz.core.user_utils import generate_ep_number
from kb_adapter_postgres.session import get_session
from kb_biz.models.announcement import Announcement, AnnouncementRead
from kb_biz.models.department import Department
from kb_biz.models.llm_config import LLMConfig
from kb_biz.models.permission import Permission
from kb_biz.models.role import Role, RolePermission, UserRole
from kb_biz.models.tenant import Tenant
from kb_biz.models.user import User
from kb_biz.schemas.admin import (
    AnnouncementCreate,
    AnnouncementReaderInfo,
    AnnouncementReadStatsResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    LLMConfigCreate,
    LLMConfigResponse,
    LLMConfigUpdate,
    PermissionResponse,
    ResetPasswordRequest,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from kb_biz.schemas.common import Response

router = APIRouter(prefix="/admin", tags=["admin"])


# ──────────────────────────────────────────────
# Departments
# ──────────────────────────────────────────────

@router.get("/departments", response_model=Response[list[DepartmentResponse]])
async def list_departments(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(PermissionChecker(["department.read"])),
):
    is_super = await _is_super_admin(session, current_user)
    query = select(Department)
    if not is_super:
        if current_user.tenant_id:
            query = query.where(Department.tenant_id == current_user.tenant_id)
        if current_user.dept_id and not await _is_tenant_admin(session, current_user):
            query = query.where(Department.id == current_user.dept_id)
    result = await session.execute(query.order_by(Department.sort_order, Department.name))
    depts = result.scalars().all()

    # Batch-load tenant names and codes
    tenant_ids = {d.tenant_id for d in depts if d.tenant_id}
    tenant_info: dict[str, tuple[str, str]] = {}
    if tenant_ids:
        t_result = await session.execute(
            select(Tenant.id, Tenant.name, Tenant.code).where(Tenant.id.in_(list(tenant_ids)))
        )
        tenant_info = {str(row[0]): (row[1], row[2]) for row in t_result.all()}

    return Response(data=[
        _dept_to_response(
            d,
            tenant_name=tenant_info.get(str(d.tenant_id), (None, None))[0] if d.tenant_id else None,
            tenant_code=tenant_info.get(str(d.tenant_id), (None, None))[1] if d.tenant_id else None,
        ) for d in depts
    ])


@router.get("/departments/{dept_id}", response_model=Response[DepartmentResponse])
async def get_department(
    dept_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["department.read"])),
):
    dept = await session.get(Department, dept_id)
    if not dept:
        raise NotFoundException("Department")
    return Response(data=_dept_to_response(dept))


@router.post("/departments", response_model=Response[DepartmentResponse])
async def create_department(
    request: DepartmentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(PermissionChecker(["department.create"])),
):
    existing = await session.execute(
        select(Department).where(Department.code == request.code)
    )
    if existing.scalar_one_or_none():
        raise ConflictException("Department code already exists")

    # Check department limit for tenant
    count_query = select(sa.func.count()).select_from(Department).where(Department.tenant_id == current_user.tenant_id)
    dept_count = (await session.execute(count_query)).scalar()
    if dept_count >= MAX_DEPARTMENTS:
        raise ValidationException(f"已达部门数量上限（{MAX_DEPARTMENTS} 个）")

    # Get tenant (from request for super admin, fallback to user's tenant or default)
    tenant_id = uuid.UUID(request.tenant_id) if request.tenant_id and request.tenant_id.strip() else current_user.tenant_id
    if not tenant_id:
        default = await session.execute(select(Tenant).where(Tenant.code == "default"))
        default_t = default.scalar_one_or_none()
        tenant_id = default_t.id if default_t else None

    # All departments under a tenant share the same partition
    if tenant_id:
        tenant = await session.get(Tenant, tenant_id)
        if tenant:
            tenant_partition = tenant.milvus_partition or f"tenant_{tenant.code}"
        else:
            tenant_partition = "default"
    else:
        tenant_partition = "default"

    dept = Department(
        tenant_id=tenant_id,
        name=request.name,
        code=request.code,
        milvus_partition=tenant_partition,
        parent_id=uuid.UUID(request.parent_id) if request.parent_id else None,
        sort_order=request.sort_order,
        description=request.description,
    )
    session.add(dept)
    await session.flush()
    await record_operation(session, current_user, "create", "department", str(dept.id), dept.name)
    return Response(data=_dept_to_response(dept))


@router.put("/departments/{dept_id}", response_model=Response[DepartmentResponse])
async def update_department(
    dept_id: uuid.UUID,
    request: DepartmentUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["department.update"])),
):
    dept = await session.get(Department, dept_id)
    if not dept:
        raise NotFoundException("Department")

    if request.name is not None:
        dept.name = request.name
    if request.sort_order is not None:
        dept.sort_order = request.sort_order
    if request.description is not None:
        dept.description = request.description
    if request.status is not None:
        dept.status = request.status
    if request.logo is not None:
        dept.logo = request.logo

    session.add(dept)
    await record_operation(session, _user, "update", "department", str(dept_id), dept.name)
    return Response(data=_dept_to_response(dept))


@router.delete("/departments/{dept_id}", response_model=Response[None])
async def delete_department(
    dept_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["department.delete"])),
):
    dept = await session.get(Department, dept_id)
    if not dept:
        raise NotFoundException("Department")

    if dept.status == 0:
        raise ConflictException("该部门已停用")

    dept.status = 0
    session.add(dept)
    await record_operation(session, _user, "delete", "department", str(dept_id), dept.name)
    return Response(data=None)


# ──────────────────────────────────────────────
# Roles
# ──────────────────────────────────────────────

@router.get("/roles", response_model=Response[list[RoleResponse]])
async def list_roles(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["role.read"])),
):
    result = await session.execute(select(Role).order_by(Role.sort_order))
    roles = result.scalars().all()
    # Batch-load permission IDs for all roles
    rp_rows = await session.execute(
        select(RolePermission).where(RolePermission.role_id.in_([r.id for r in roles]))
    )
    role_perm_ids: dict[uuid.UUID, list[str]] = {}
    for rp in rp_rows.scalars().all():
        role_perm_ids.setdefault(rp.role_id, []).append(str(rp.permission_id))
    return Response(data=[_role_to_response(r, role_perm_ids.get(r.id, [])) for r in roles])


@router.get("/roles/{role_id}", response_model=Response[RoleResponse])
async def get_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["role.read"])),
):
    role = await session.get(Role, role_id)
    if not role:
        raise NotFoundException("Role")
    # Load permission IDs
    perm_rows = await session.execute(
        select(RolePermission.permission_id).where(RolePermission.role_id == role_id)
    )
    perm_ids = [str(p[0]) for p in perm_rows.all()]
    return Response(data=_role_to_response(role, perm_ids))


@router.post("/roles", response_model=Response[RoleResponse])
async def create_role(
    request: RoleCreate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["role.create"])),
):
    existing = await session.execute(
        select(Role).where(Role.code == request.code)
    )
    if existing.scalar_one_or_none():
        raise ConflictException("Role code already exists")

    role = Role(
        name=request.name,
        code=request.code,
        description=request.description,
        sort_order=request.sort_order,
    )
    session.add(role)
    await session.flush()
    await record_operation(session, _user, "create", "role", str(role.id), role.name)

    for pid in request.permission_ids:
        session.add(RolePermission(role_id=role.id, permission_id=uuid.UUID(pid)))

    return Response(data=_role_to_response(role))


@router.put("/roles/{role_id}", response_model=Response[RoleResponse])
async def update_role(
    role_id: uuid.UUID,
    request: RoleUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["role.update"])),
):
    role = await session.get(Role, role_id)
    if not role:
        raise NotFoundException("Role")

    if request.name is not None:
        role.name = request.name
    if request.description is not None:
        role.description = request.description
    if request.sort_order is not None:
        role.sort_order = request.sort_order

    if request.permission_ids is not None:
        await session.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        for pid in request.permission_ids:
            session.add(RolePermission(role_id=role.id, permission_id=uuid.UUID(pid)))

    session.add(role)
    await session.flush()
    await session.refresh(role)

    await record_operation(session, _user, "update", "role", str(role_id), role.name)

    # Return response — permission_ids will be [] in response
    # but callers should reload via GET /roles/{id} for accurate count
    return Response(data=_role_to_response(role))


@router.delete("/roles/{role_id}", response_model=Response[None])
async def delete_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["role.delete"])),
):
    role = await session.get(Role, role_id)
    if not role:
        raise NotFoundException("Role")
    if role.is_system:
        raise ConflictException("Cannot delete system role")
    await session.delete(role)
    await record_operation(session, _user, "delete", "role", str(role_id), role.name)
    return Response(data=None)


# ──────────────────────────────────────────────
# Permissions
# ──────────────────────────────────────────────

@router.get("/permissions", response_model=Response[list[PermissionResponse]])
async def list_permissions(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["role.read"])),
):
    result = await session.execute(select(Permission).order_by(Permission.group, Permission.code))
    perms = result.scalars().all()
    return Response(data=[_perm_to_response(p) for p in perms])


# ──────────────────────────────────────────────
# Users (admin)
# ──────────────────────────────────────────────

@router.get("/users", response_model=Response[list[UserResponse]])
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(PermissionChecker(["user.read"])),
    scope: Optional[str] = Query(None),  # "all" to skip dept filter (for project member selection)
):
    # Non-super-admin users can only see users in their own tenant
    is_super = await _is_super_admin(session, current_user)
    query = select(User)
    if not is_super:
        if current_user.tenant_id:
            query = query.where(User.tenant_id == current_user.tenant_id)
        if scope != "all" and current_user.dept_id and not await _is_tenant_admin(session, current_user):
            ta_role = select(Role.id).where(Role.code == "tenant_admin")
            ta_ids = select(UserRole.user_id).where(UserRole.role_id.in_(ta_role))
            query = query.where(
                User.dept_id == current_user.dept_id,
                User.id.notin_(ta_ids),
            )
    result = await session.execute(query.order_by(User.created_at.desc()))
    users = result.scalars().all()
    user_ids = [u.id for u in users]

    # Batch-load role IDs and names via UserRole → Role join
    role_query = await session.execute(
        select(UserRole.user_id, UserRole.role_id, Role.name)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id.in_(user_ids))
    )
    user_role_map: dict[uuid.UUID, tuple[list[str], list[str]]] = {}
    for user_id, role_id, role_name in role_query.all():
        ids, names = user_role_map.setdefault(user_id, ([], []))
        ids.append(str(role_id))
        names.append(role_name)

    return Response(data=[
        _user_to_response(u, *(user_role_map.get(u.id, ([], []))))
        for u in users
    ])


@router.get("/users/next-ep", response_model=Response[str])
async def next_ep_number(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["user.create"])),
):
    ep = await generate_ep_number(session, str(_user.tenant_id) if _user.tenant_id else None)
    return Response(data=ep)


@router.post("/users", response_model=Response[UserResponse])
async def create_user(
    request: UserCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(PermissionChecker(["user.create"])),
):
    # Check user limit for tenant
    count_query = select(sa.func.count()).select_from(User).where(User.tenant_id == current_user.tenant_id)
    user_count = (await session.execute(count_query)).scalar()
    if user_count >= MAX_USERS:
        raise ValidationException(f"已达用户数量上限（{MAX_USERS} 个）")

    username = await generate_ep_number(session, str(current_user.tenant_id) if current_user.tenant_id else None)

    user = User(
        tenant_id=current_user.tenant_id,
        username=username,
        password_hash=hash_password(request.password or "admin123"),
        display_name=request.display_name,
        email=request.email,
        phone=request.phone,
        dept_id=uuid.UUID(request.dept_id) if request.dept_id else (current_user.dept_id if current_user.dept_id else None),
    )
    session.add(user)
    await session.flush()
    await record_operation(session, current_user, "create", "user", str(user.id), user.display_name or user.username)

    for rid in request.role_ids:
        session.add(UserRole(user_id=user.id, role_id=uuid.UUID(rid)))

    return Response(data=_user_to_response(user))


@router.put("/users/{user_id}", response_model=Response[UserResponse])
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["user.update"])),
):
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException("User")

    if request.display_name is not None:
        user.display_name = request.display_name
    if request.email is not None:
        user.email = request.email
    if request.phone is not None:
        user.phone = request.phone
    if request.dept_id is not None:
        user.dept_id = uuid.UUID(request.dept_id) if request.dept_id else None
    if request.status is not None:
        user.status = request.status

    if request.role_ids is not None:
        await session.execute(
            delete(UserRole).where(UserRole.user_id == user_id)
        )
        for rid in request.role_ids:
            session.add(UserRole(user_id=user.id, role_id=uuid.UUID(rid)))

    session.add(user)
    await session.flush()
    await session.refresh(user)
    await record_operation(session, _user, "update", "user", str(user_id), user.display_name or user.username)
    await set_cached_user(user.username, {
        "user_id": str(user.id),
        "password_hash": user.password_hash,
        "display_name": user.display_name,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "dept_id": str(user.dept_id) if user.dept_id else None,
        "status": user.status,
    })
    return Response(data=_user_to_response(user))


@router.delete("/users/{user_id}", response_model=Response[None])
async def delete_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(PermissionChecker(["user.delete"])),
):
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException("User")

    # Scoping: non-super can only delete users in their own tenant/department
    is_super = await _is_super_admin(session, current_user)
    if not is_super:
        if current_user.tenant_id:
            if user.tenant_id != current_user.tenant_id:
                raise ForbiddenException("Cannot delete users from another tenant")
        elif current_user.dept_id and user.dept_id != current_user.dept_id:
            raise ForbiddenException("Cannot delete users from another department")

    if user.status == 0:
        raise ConflictException("该用户已停用")

    user.status = 0
    session.add(user)
    await record_operation(session, current_user, "delete", "user", str(user_id), user.display_name or user.username)
    await invalidate_user(user.username)
    return Response(data=None)


@router.put("/users/{user_id}/reset-password", response_model=Response[None])
async def reset_user_password(
    user_id: uuid.UUID,
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(PermissionChecker(["user.update"])),
):
    """Admin-only: reset a user's password (no old password required)."""
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundException("User")
    is_super = await _is_super_admin(session, current_user)
    if not is_super:
        if current_user.tenant_id:
            if user.tenant_id != current_user.tenant_id:
                raise ForbiddenException("Cannot reset password for users from another tenant")
        elif current_user.dept_id and user.dept_id != current_user.dept_id:
            raise ForbiddenException("Cannot reset password for users from another department")
    if len(body.new_password) < 6:
        raise ValidationException("Password must be at least 6 characters")
    user.password_hash = hash_password(body.new_password)
    session.add(user)
    await record_operation(session, current_user, "update", "user", str(user_id), f"{user.display_name or user.username}: password reset")
    await set_cached_user(user.username, {
        "user_id": str(user.id),
        "password_hash": user.password_hash,
        "display_name": user.display_name,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "dept_id": str(user.dept_id) if user.dept_id else None,
        "status": user.status,
    })
    return Response(data=None)


@router.put("/departments/my", response_model=Response[DepartmentResponse])
async def update_my_department(
    request: DepartmentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(RoleChecker(["super_admin", "tenant_admin", "dept_admin"])),
):
    """Allow dept_admin to update their own department's name/logo/description."""
    if not current_user.dept_id:
        raise NotFoundException("Department")
    dept = await session.get(Department, current_user.dept_id)
    if not dept:
        raise NotFoundException("Department")

    if request.name is not None:
        dept.name = request.name
    if request.description is not None:
        dept.description = request.description
    if request.logo is not None:
        dept.logo = request.logo

    session.add(dept)
    await record_operation(session, current_user, "update", "department", str(dept.id), dept.name)
    return Response(data=_dept_to_response(dept))


# ──────────────────────────────────────────────
# LLM Configs
# ──────────────────────────────────────────────

@router.get("/llm-configs", response_model=Response[list[LLMConfigResponse]])
async def list_llm_configs(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(PermissionChecker(["llm_config.read"])),
):
    query = select(LLMConfig).order_by(LLMConfig.sort_order, LLMConfig.name)
    if user.tenant_id:
        query = query.where(
            (LLMConfig.tenant_id == user.tenant_id) | (LLMConfig.tenant_id.is_(None))
        )
    result = await session.execute(query)
    configs = result.scalars().all()
    return Response(data=[_llm_config_to_response(c) for c in configs])


@router.post("/llm-configs", response_model=Response[LLMConfigResponse])
async def create_llm_config(
    request: LLMConfigCreate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["llm_config.update"])),
):
    if request.is_default:
        await session.execute(
            sa_update(LLMConfig).where(LLMConfig.is_default == True).values(is_default=False)  # noqa: E712
        )

    config = LLMConfig(
        tenant_id=_user.tenant_id,  # tenant admin → scoped; super admin → NULL (global)
        name=request.name,
        provider=request.provider,
        api_key_encrypted=request.api_key,
        base_url=request.base_url,
        model=request.model,
        max_tokens=request.max_tokens,
        temperature=int(request.temperature * 10),
        is_active=request.is_active,
        is_default=request.is_default,
    )
    session.add(config)
    await session.flush()
    await record_operation(session, _user, "create", "llm_config", str(config.id), config.name)
    return Response(data=_llm_config_to_response(config))


@router.put("/llm-configs/{config_id}", response_model=Response[LLMConfigResponse])
async def update_llm_config(
    config_id: uuid.UUID,
    request: LLMConfigUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["llm_config.update"])),
):
    if request.is_default:
        await session.execute(
            sa_update(LLMConfig).where(LLMConfig.is_default == True).values(is_default=False)  # noqa: E712
        )

    config = await session.get(LLMConfig, config_id)
    if not config:
        raise NotFoundException("LLMConfig")

    if request.name is not None:
        config.name = request.name
    if request.provider is not None:
        config.provider = request.provider
    if request.api_key is not None:
        config.api_key_encrypted = request.api_key
    if request.base_url is not None:
        config.base_url = request.base_url
    if request.model is not None:
        config.model = request.model
    if request.max_tokens is not None:
        config.max_tokens = request.max_tokens
    if request.temperature is not None:
        config.temperature = int(request.temperature * 10)
    if request.is_active is not None:
        config.is_active = request.is_active
    if request.is_default is not None:
        config.is_default = request.is_default

    session.add(config)
    await record_operation(session, _user, "update", "llm_config", str(config_id), config.name)
    return Response(data=_llm_config_to_response(config))


@router.delete("/llm-configs/{config_id}", response_model=Response[None])
async def delete_llm_config(
    config_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["llm_config.update"])),
):
    config = await session.get(LLMConfig, config_id)
    if not config:
        raise NotFoundException("LLMConfig")
    await session.delete(config)
    await record_operation(session, _user, "delete", "llm_config", str(config_id), config.name)
    return Response(data=None)


@router.put("/llm-configs/{config_id}/default", response_model=Response[LLMConfigResponse])
async def set_default_llm_config(
    config_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["llm_config.update"])),
):
    config = await session.get(LLMConfig, config_id)
    if not config:
        raise NotFoundException("LLMConfig")

    await session.execute(
        sa_update(LLMConfig).where(LLMConfig.is_default == True).values(is_default=False)  # noqa: E712
    )
    config.is_default = True
    session.add(config)
    await record_operation(session, _user, "update", "llm_config", str(config_id), config.name)
    return Response(data=_llm_config_to_response(config))


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _is_super_admin(session: AsyncSession, user: User) -> bool:
    """Check whether the user has the super_admin role."""
    result = await session.execute(
        select(Role).join(UserRole).where(
            UserRole.user_id == user.id, Role.code == "super_admin"
        )
    )
    return result.scalar_one_or_none() is not None


async def _is_tenant_admin(session: AsyncSession, user: User) -> bool:
    """Check whether the user has the tenant_admin role."""
    result = await session.execute(
        select(Role).join(UserRole).where(
            UserRole.user_id == user.id, Role.code == "tenant_admin"
        )
    )
    return result.scalar_one_or_none() is not None


# ──────────────────────────────────────────────
# File Upload (avatar, logo, etc.)
# ──────────────────────────────────────────────

# File serving endpoint
@router.get("/files/{path:path}", include_in_schema=False)
async def serve_file(path: str):
    """Serve uploaded files from MinIO."""


    try:
        data = await _instances.storage_client.download_file(path)

        content_type, _ = mimetypes.guess_type(path)
        return StreamingResponse(iter([data]), media_type=content_type or "application/octet-stream")
    except Exception:
        raise NotFoundException("File")


@router.post("/upload", response_model=Response[dict])
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload an image file (avatar, logo) and return its URL."""

    allowed = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
    if file.content_type not in allowed:
        raise ValidationException("Only image files are allowed (JPEG, PNG, GIF, WebP, SVG)")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise ValidationException("File exceeds 2MB limit")


    md5 = hashlib.md5(content).hexdigest()
    ext = Path(file.filename or "image.png").suffix if file.filename else ".png"
    object_path = f"uploads/{md5}{ext}"

    await _instances.storage_client.ensure_bucket()
    await _instances.storage_client.upload_file(object_path, content, content_type=file.content_type)

    url = f"/api/v1/admin/files/{object_path}"
    return Response(data={"url": url, "path": object_path})

# Announcements — SSE & Helpers
# ──────────────────────────────────────────────


ANNOUNCEMENT_REDIS_CHANNEL = "announcements:events"


async def _publish_announcement_event(event_type: str = "updated") -> None:
    """Publish announcement change to Redis for SSE broadcast (best-effort)."""
    try:
        r = AsyncRedis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.publish(ANNOUNCEMENT_REDIS_CHANNEL, json.dumps({"type": event_type}))
        await r.aclose()
    except Exception:
        pass


def _determine_announcement_scope(user_role_codes: list[str]) -> str:
    """Determine announcement scope based on user's role codes."""
    if "super_admin" in user_role_codes:
        return "system"
    if "tenant_admin" in user_role_codes:
        return "tenant"
    return "dept"


def _check_announcement_scope_access(user_role_codes: list[str], scope: str, user_dept_id: uuid.UUID | None = None, ann_dept_id: uuid.UUID | None = None) -> bool:
    """Check if user's roles allow managing an announcement with the given scope."""
    if "super_admin" in user_role_codes:
        return True  # super_admin can manage any scope
    if "tenant_admin" in user_role_codes:
        return scope in ("tenant", "dept")  # tenant_admin can manage tenant + dept
    # dept_admin can only manage announcements belonging to their own department
    if scope == "dept" and user_dept_id and ann_dept_id:
        return user_dept_id == ann_dept_id
    return False


async def _user_has_permission(session: AsyncSession, user: User, permission_code: str) -> bool:
    """Check if a user has a specific permission (for user-facing endpoints)."""
    from kb_biz.models.permission import Permission
    from kb_biz.models.role import RolePermission, UserRole
    from kb_biz.models.role import DepartmentRole

    role_ids = select(UserRole.role_id).where(UserRole.user_id == user.id)
    if user.dept_id:
        dept_role_ids = select(DepartmentRole.role_id).where(DepartmentRole.dept_id == user.dept_id)
        role_ids = role_ids.union(dept_role_ids)
    result = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id.in_(role_ids))
        .where(Permission.code == permission_code)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


@router.get("/announcements/sse")
async def announcement_sse(
    request: Request,
):
    """SSE endpoint for real-time announcement updates.
    No auth required — only sends notification events; actual data is fetched
    via authenticated REST endpoints. Matches the /knowledge/status/events pattern.
    """
    redis_client = AsyncRedis.from_url(settings.redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(ANNOUNCEMENT_REDIS_CHANNEL)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await pubsub.get_message(timeout=15, ignore_subscribe_messages=True)
                    if msg and msg["type"] == "message":
                        yield f"event: announcement\ndata: {msg['data'].decode()}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            await pubsub.unsubscribe(ANNOUNCEMENT_REDIS_CHANNEL)
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────────
# Announcements (user-facing)
# ──────────────────────────────────────────────


@router.get("/announcements", response_model=Response[list[AnnouncementResponse]])
async def list_announcements(
    all: bool = Query(False, description="Include inactive/expired (for admin)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List announcements with read status for current user."""
    now = datetime.now(timezone.utc)
    from sqlalchemy import select as sa_select
    from kb_biz.models.role import UserRole, Role
    role_query = await session.execute(
        sa_select(Role.code).join(UserRole).where(UserRole.user_id == current_user.id)
    )
    user_role_codes = [row[0] for row in role_query]
    is_super = "super_admin" in user_role_codes
    show_all = all and _user_has_permission(session, current_user, "system.config")
    stmt = select(Announcement).order_by(Announcement.created_at.desc())
    if not show_all:
        stmt = stmt.where(Announcement.is_active == True).where(
            sa.or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
        )
    # Scope filtering: non-super_admins only see announcements relevant to them
    if not is_super:
        user = await session.get(User, current_user.id)
        scope_filters = [Announcement.scope == "system"]
        if user.tenant_id:
            scope_filters.append(
                sa.and_(Announcement.scope == "tenant", Announcement.tenant_id == user.tenant_id)
            )
        if user.dept_id:
            scope_filters.append(
                sa.and_(Announcement.scope == "dept", Announcement.dept_id == user.dept_id)
            )
        stmt = stmt.where(sa.or_(*scope_filters))
    result = await session.execute(stmt)
    announcements = result.scalars().all()

    # Get read announcement IDs for current user
    read_ids = set()
    if announcements:
        read_result = await session.execute(
            select(AnnouncementRead.announcement_id).where(
                AnnouncementRead.user_id == current_user.id,
                AnnouncementRead.announcement_id.in_([a.id for a in announcements]),
            )
        )
        read_ids = {r for r in read_result.scalars().all()}

    return Response(
        data=[
            AnnouncementResponse(
                id=str(a.id),
                title=a.title,
                content=a.content,
                scope=a.scope,
                read=a.id in read_ids,
                is_active=a.is_active,
                expires_at=a.expires_at,
                created_by=str(a.created_by) if a.created_by else None,
                tenant_id=str(a.tenant_id) if a.tenant_id else None,
                dept_id=str(a.dept_id) if a.dept_id else None,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in announcements
        ]
    )


@router.get("/announcements/unread-count", response_model=Response[int])
async def get_unread_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get the count of unread announcements for the current user."""
    now = datetime.now(timezone.utc)
    from sqlalchemy import select as sa_select
    from kb_biz.models.role import UserRole, Role
    role_query = await session.execute(
        sa_select(Role.code).join(UserRole).where(UserRole.user_id == current_user.id)
    )
    user_role_codes = [row[0] for row in role_query]
    is_super = "super_admin" in user_role_codes

    base = select(Announcement.id).where(Announcement.is_active == True).where(
        sa.or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
    )
    if not is_super:
        user = await session.get(User, current_user.id)
        scope_filters = [Announcement.scope == "system"]
        if user.tenant_id:
            scope_filters.append(
                sa.and_(Announcement.scope == "tenant", Announcement.tenant_id == user.tenant_id)
            )
        if user.dept_id:
            scope_filters.append(
                sa.and_(Announcement.scope == "dept", Announcement.dept_id == user.dept_id)
            )
        base = base.where(sa.or_(*scope_filters))

    total = await session.scalar(select(sa.func.count()).select_from(base.subquery()))
    read = await session.scalar(
        select(sa.func.count(AnnouncementRead.id))
        .where(AnnouncementRead.user_id == current_user.id)
        .where(AnnouncementRead.announcement_id.in_(base))
    )
    return Response(data=(total or 0) - (read or 0))


@router.put("/announcements/read-all", response_model=Response[None])
async def mark_all_announcements_read(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark all active announcements as read."""
    now = datetime.now(timezone.utc)
    from sqlalchemy import select as sa_select
    from kb_biz.models.role import UserRole, Role
    role_query = await session.execute(
        sa_select(Role.code).join(UserRole).where(UserRole.user_id == current_user.id)
    )
    user_role_codes = [row[0] for row in role_query]
    is_super = "super_admin" in user_role_codes

    stmt = select(Announcement).where(Announcement.is_active == True).where(
        sa.or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
    )
    if not is_super:
        user = await session.get(User, current_user.id)
        scope_filters = [Announcement.scope == "system"]
        if user.tenant_id:
            scope_filters.append(
                sa.and_(Announcement.scope == "tenant", Announcement.tenant_id == user.tenant_id)
            )
        if user.dept_id:
            scope_filters.append(
                sa.and_(Announcement.scope == "dept", Announcement.dept_id == user.dept_id)
            )
        stmt = stmt.where(sa.or_(*scope_filters))
    result = await session.execute(stmt)
    for a in result.scalars().all():
        existing = await session.execute(
            select(AnnouncementRead).where(
                AnnouncementRead.announcement_id == a.id,
                AnnouncementRead.user_id == current_user.id,
            )
        )
        if not existing.scalar_one_or_none():
            session.add(
                AnnouncementRead(
                    announcement_id=a.id,
                    user_id=current_user.id,
                    read_at=now,
                )
            )
    return Response(data=None)


@router.put("/announcements/{announcement_id}/read", response_model=Response[None])
async def mark_announcement_read(
    announcement_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark an announcement as read by current user."""
    existing = await session.execute(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == current_user.id,
        )
    )
    if not existing.scalar_one_or_none():
        session.add(
            AnnouncementRead(
                announcement_id=announcement_id,
                user_id=current_user.id,
                read_at=datetime.now(timezone.utc),
            )
        )
    return Response(data=None)


# ──────────────────────────────────────────────
# Announcements (admin / super_admin CRUD)
# ──────────────────────────────────────────────


@router.post("/announcements", response_model=Response[AnnouncementResponse])
async def create_announcement(
    body: AnnouncementCreate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["system.config"])),
):
    """Create an announcement."""
    from sqlalchemy import select
    from kb_biz.models.role import UserRole, Role
    role_query = await session.execute(
        select(Role.code).join(UserRole).where(UserRole.user_id == _user.id)
    )
    user_role_codes = [row[0] for row in role_query]
    scope = _determine_announcement_scope(user_role_codes)
    a = Announcement(
        title=body.title,
        content=body.content,
        expires_at=body.expires_at,
        created_by=_user.id,
        scope=scope,
        tenant_id=_user.tenant_id,
        dept_id=_user.dept_id,
    )
    session.add(a)
    await session.flush()
    # Creator auto-marked as read
    session.add(AnnouncementRead(announcement_id=a.id, user_id=_user.id))
    await _publish_announcement_event("created")
    return Response(
        data=AnnouncementResponse(
            id=str(a.id),
            title=a.title,
            content=a.content,
            scope=a.scope,
            is_active=a.is_active,
            expires_at=a.expires_at,
            created_by=str(a.created_by) if a.created_by else None,
            tenant_id=str(a.tenant_id) if a.tenant_id else None,
            dept_id=str(a.dept_id) if a.dept_id else None,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
    )


@router.put("/announcements/{announcement_id}", response_model=Response[AnnouncementResponse])
async def update_announcement(
    announcement_id: uuid.UUID,
    body: AnnouncementUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["system.config"])),
):
    """Update an announcement. Scope is validated against the caller's role."""
    a = await session.get(Announcement, announcement_id)
    if not a:
        raise NotFoundException("Announcement")
    # Scope check: user can only update announcements at or below their role level
    from sqlalchemy import select
    from kb_biz.models.role import UserRole, Role
    role_query = await session.execute(
        select(Role.code).join(UserRole).where(UserRole.user_id == _user.id)
    )
    user_role_codes = [row[0] for row in role_query]
    if not _check_announcement_scope_access(user_role_codes, a.scope, _user.dept_id, a.dept_id):
        raise ForbiddenException("You can only manage announcements within your scope")
    if body.title is not None:
        a.title = body.title
    if body.content is not None:
        a.content = body.content
    if body.is_active is not None:
        a.is_active = body.is_active
    if body.expires_at is not None:
        a.expires_at = body.expires_at
    # Reset read status for other users so they see the updated announcement as unread
    await session.execute(
        delete(AnnouncementRead).where(
            AnnouncementRead.announcement_id == a.id,
            AnnouncementRead.user_id != _user.id,
        )
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    await _publish_announcement_event("updated")
    return Response(
        data=AnnouncementResponse(
            id=str(a.id),
            title=a.title,
            content=a.content,
            scope=a.scope,
            is_active=a.is_active,
            expires_at=a.expires_at,
            created_by=str(a.created_by) if a.created_by else None,
            tenant_id=str(a.tenant_id) if a.tenant_id else None,
            dept_id=str(a.dept_id) if a.dept_id else None,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
    )


@router.delete("/announcements/{announcement_id}", response_model=Response[None])
async def delete_announcement(
    announcement_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["system.config"])),
):
    """Delete an announcement. Scope is validated against the caller's role."""
    a = await session.get(Announcement, announcement_id)
    if not a:
        raise NotFoundException("Announcement")
    from sqlalchemy import select
    from kb_biz.models.role import UserRole, Role
    role_query = await session.execute(
        select(Role.code).join(UserRole).where(UserRole.user_id == _user.id)
    )
    user_role_codes = [row[0] for row in role_query]
    if not _check_announcement_scope_access(user_role_codes, a.scope, _user.dept_id, a.dept_id):
        raise ForbiddenException("You can only manage announcements within your scope")
    await session.delete(a)
    await _publish_announcement_event("deleted")
    return Response(data=None)


@router.get("/announcements/{announcement_id}/read-stats", response_model=Response[AnnouncementReadStatsResponse])
async def get_announcement_read_stats(
    announcement_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["system.config"])),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get read receipt stats for an announcement."""
    a = await session.get(Announcement, announcement_id)
    if not a:
        raise NotFoundException("Announcement")

    from sqlalchemy import func
    from kb_biz.models.department import Department
    from kb_biz.models.user import User

    # Count total readers
    count_query = await session.execute(
        select(func.count()).select_from(AnnouncementRead).where(AnnouncementRead.announcement_id == announcement_id)
    )
    total_read: int = count_query.scalar() or 0

    # Get reader details (paginated)
    readers_query = await session.execute(
        select(
            AnnouncementRead.user_id,
            User.display_name,
            Department.name.label("dept_name"),
            AnnouncementRead.read_at,
        )
        .join(User, AnnouncementRead.user_id == User.id)
        .outerjoin(Department, User.dept_id == Department.id)
        .where(AnnouncementRead.announcement_id == announcement_id)
        .order_by(AnnouncementRead.read_at.desc())
        .offset(offset)
        .limit(limit)
    )
    has_more = total_read > offset + limit
    readers = [
        AnnouncementReaderInfo(
            user_id=str(row.user_id),
            display_name=row.display_name,
            dept_name=row.dept_name,
            read_at=row.read_at,
        )
        for row in readers_query
    ]

    return Response(
        data=AnnouncementReadStatsResponse(
            announcement_id=str(a.id),
            announcement_title=a.title,
            total_read=total_read,
            has_more=has_more,
            readers=readers,
        )
    )


# ──────────────────────────────────────────────
# Converters
# ──────────────────────────────────────────────


def _dept_to_response(d: Department, tenant_name: str | None = None, tenant_code: str | None = None) -> DepartmentResponse:
    partition = d.milvus_partition or (f"tenant_{tenant_code}" if tenant_code else "default")
    return DepartmentResponse(
        id=str(d.id),
        name=d.name,
        code=d.code,
        tenant_id=str(d.tenant_id) if d.tenant_id else None,
        tenant_name=tenant_name,
        milvus_partition=partition,
        parent_id=str(d.parent_id) if d.parent_id else None,
        logo=d.logo,
        status=d.status,
        sort_order=d.sort_order,
        description=d.description,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _role_to_response(r: Role, perm_ids: list[str] | None = None) -> RoleResponse:
    return RoleResponse(
        id=str(r.id),
        name=r.name,
        code=r.code,
        description=r.description,
        is_system=r.is_system,
        sort_order=r.sort_order,
        permission_ids=perm_ids or [],
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _user_to_response(u: User, role_ids: list[str] | None = None, role_names: list[str] | None = None) -> UserResponse:
    return UserResponse(
        id=str(u.id),
        username=u.username,
        display_name=u.display_name,
        avatar=u.avatar,
        email=u.email,
        phone=u.phone,
        dept_id=str(u.dept_id) if u.dept_id else None,
        role_ids=role_ids or [],
        role_names=role_names or [],
        status=u.status,
        last_login_at=u.last_login_at,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


def _perm_to_response(p: Permission) -> PermissionResponse:
    return PermissionResponse(
        id=str(p.id),
        code=p.code,
        name=p.name,
        group=p.group,
        description=p.description,
    )


def _llm_config_to_response(c: LLMConfig) -> LLMConfigResponse:
    return LLMConfigResponse(
        id=str(c.id),
        tenant_id=str(c.tenant_id) if c.tenant_id else None,
        name=c.name,
        provider=c.provider,
        base_url=c.base_url,
        model=c.model,
        max_tokens=c.max_tokens,
        temperature=c.temperature / 10.0,
        is_active=c.is_active,
        is_default=c.is_default,
        sort_order=c.sort_order,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )
