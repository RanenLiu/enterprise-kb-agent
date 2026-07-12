from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.core.auth.deps import RoleChecker, get_current_user
from kb_adapter_postgres.session import get_session
from kb_biz.models.log import LoginLog, OperationLog
from kb_biz.models.role import Role, UserRole
from kb_biz.models.user import User
from kb_biz.schemas.admin import LoginLogResponse, OperationLogResponse
from kb_biz.schemas.common import PaginationMeta, Response

router = APIRouter(prefix="/admin", tags=["admin-logs"])


@router.get("/operation-logs", response_model=None)
async def list_operation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    result: Optional[str] = None,
    keyword: Optional[str] = None,
    user: Optional[str] = None,
    dept_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _user: User = Depends(RoleChecker(["super_admin", "tenant_admin", "dept_admin"])),
):
    """查看操作日志。超管看全部，其他人看本租户/本部门。"""
    query = select(OperationLog)
    count_query = select(func.count(OperationLog.id))

    # Role-based scope
    is_super = await _is_super_admin(session, current_user)
    is_tenant = await _is_tenant_admin(session, current_user)

    # Tenant scope applies to all users (including super admin)
    if current_user.tenant_id:
        query = query.where(OperationLog.tenant_id == current_user.tenant_id)
        count_query = count_query.where(OperationLog.tenant_id == current_user.tenant_id)

    # Department scope for non-super, non-tenant-admin users
    if current_user.dept_id and not is_super and not is_tenant:
        query = query.where(OperationLog.dept_id == current_user.dept_id)
        count_query = count_query.where(OperationLog.dept_id == current_user.dept_id)

    # Optional tenant filter - reject if user has no tenant
    if tenant_id:
        if current_user.tenant_id:
            query = query.where(OperationLog.tenant_id == tenant_id)
            count_query = count_query.where(OperationLog.tenant_id == tenant_id)
        else:
            query = query.where(false())
            count_query = count_query.where(false())
    if is_tenant and dept_id:
        query = query.where(OperationLog.dept_id == dept_id)
        count_query = count_query.where(OperationLog.dept_id == dept_id)
    if dept_id and is_super and current_user.tenant_id:
        query = query.where(OperationLog.dept_id == dept_id)
        count_query = count_query.where(OperationLog.dept_id == dept_id)

    if keyword:
        query = query.where(OperationLog.user_name.ilike(f"%{keyword}%"))
        count_query = count_query.where(OperationLog.user_name.ilike(f"%{keyword}%"))
    if user:
        query = query.where(OperationLog.resource_name.ilike(f"%{user}%"))
        count_query = count_query.where(OperationLog.resource_name.ilike(f"%{user}%"))
    if action_type:
        query = query.where(OperationLog.action_type == action_type)
        count_query = count_query.where(OperationLog.action_type == action_type)
    if resource_type:
        query = query.where(OperationLog.resource_type == resource_type)
        count_query = count_query.where(OperationLog.resource_type == resource_type)
    if result:
        query = query.where(OperationLog.result == result)
        count_query = count_query.where(OperationLog.result == result)
    if start_time:
        query = query.where(OperationLog.created_at >= start_time)
        count_query = count_query.where(OperationLog.created_at >= start_time)
    if end_time:
        query = query.where(OperationLog.created_at <= end_time)
        count_query = count_query.where(OperationLog.created_at <= end_time)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(OperationLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    logs = result.scalars().all()

    # Batch-load department names and user display names
    dept_ids = {str(l.dept_id) for l in logs if l.dept_id}
    dept_names = {}
    if dept_ids:
        from kb_biz.models.department import Department
        dept_rows = await session.execute(
            select(Department.id, Department.name).where(Department.id.in_([uuid.UUID(d) for d in dept_ids]))
        )
        dept_names = {str(row[0]): row[1] for row in dept_rows}

    user_ids = {str(l.user_id) for l in logs if l.user_id}
    user_names = {}
    if user_ids:
        user_rows = await session.execute(
            select(User.id, User.display_name).where(User.id.in_([uuid.UUID(u) for u in user_ids]))
        )
        user_names = {str(row[0]): row[1] for row in user_rows}

    return Response(
        data=[_oplog_to_response(l, dept_names.get(str(l.dept_id) if l.dept_id else ''),
                                  user_names.get(str(l.user_id) if l.user_id else None)) for l in logs],
        meta=PaginationMeta(total=total, page=page, page_size=page_size).model_dump(),
    )




@router.get("/login-logs", response_model=Response[list[LoginLogResponse]])
async def list_login_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    username: Optional[str] = None,
    operator: Optional[str] = None,
    result: Optional[str] = None,
    tenant_id: Optional[str] = None,
    dept_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(RoleChecker(["super_admin", "tenant_admin", "dept_admin"])),
):
    from kb_biz.models.department import Department
    from kb_biz.models.tenant import Tenant
    query = select(LoginLog)
    count_query = select(func.count(LoginLog.id))

    is_super = await _is_super_admin(session, current_user)
    is_tenant = await _is_tenant_admin(session, current_user)

    if current_user.tenant_id:
        query = query.where(LoginLog.tenant_id == current_user.tenant_id)
        count_query = count_query.where(LoginLog.tenant_id == current_user.tenant_id)

    if current_user.dept_id and not is_super and not is_tenant:
        query = query.where(LoginLog.dept_id == current_user.dept_id)
        count_query = count_query.where(LoginLog.dept_id == current_user.dept_id)

    if tenant_id:
        if current_user.tenant_id:
            query = query.where(LoginLog.tenant_id == tenant_id)
            count_query = count_query.where(LoginLog.tenant_id == tenant_id)
        else:
            query = query.where(false())
            count_query = count_query.where(false())

    if dept_id and is_super and current_user.tenant_id:
        query = query.where(LoginLog.dept_id == dept_id)
        count_query = count_query.where(LoginLog.dept_id == dept_id)
    if dept_id and is_tenant:
        query = query.where(LoginLog.dept_id == dept_id)
        count_query = count_query.where(LoginLog.dept_id == dept_id)

    if username:
        query = query.where(LoginLog.user_name.ilike(f"%{username}%"))
        count_query = count_query.where(LoginLog.user_name.ilike(f"%{username}%"))
    if operator:
        op_user_ids = select(User.id).where(User.display_name.ilike(f"%{operator}%"))
        query = query.where(LoginLog.user_id.in_(op_user_ids))
        count_query = count_query.where(LoginLog.user_id.in_(op_user_ids))
    if result:
        query = query.where(LoginLog.result == result)
        count_query = count_query.where(LoginLog.result == result)
    if start_time:
        query = query.where(LoginLog.created_at >= start_time)
        count_query = count_query.where(LoginLog.created_at >= start_time)
    if end_time:
        query = query.where(LoginLog.created_at <= end_time)
        count_query = count_query.where(LoginLog.created_at <= end_time)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(LoginLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    logs = result.scalars().all()

    user_ids = [str(l.user_id) for l in logs if l.user_id]
    dept_map = {}
    name_map = {}
    if user_ids:
        user_rows = await session.execute(
            select(User.id, User.display_name, User.dept_id, Department.name, User.tenant_id, Tenant.name)
            .outerjoin(Department, User.dept_id == Department.id)
            .outerjoin(Tenant, User.tenant_id == Tenant.id)
            .where(User.id.in_([uuid.UUID(u) for u in user_ids]))
        )
        for uid, display_name, did, dname, tid, tname in user_rows:
            dept_map[str(uid)] = (display_name or None, str(did) if did else None, dname or None, str(tid) if tid else None, tname or None)

    name_lookup = [l.user_name for l in logs if not l.user_id and l.user_name]
    if name_lookup:
        name_rows = await session.execute(
            select(User.username, User.display_name, User.dept_id, Department.name, User.tenant_id, Tenant.name)
            .outerjoin(Department, User.dept_id == Department.id)
            .outerjoin(Tenant, User.tenant_id == Tenant.id)
            .where(User.username.in_(name_lookup))
        )
        for uname, display_name, did, dname, tid, tname in name_rows:
            name_map[uname] = (display_name or None, str(did) if did else None, dname or None, str(tid) if tid else None, tname or None)

    def _resolve(l):
        if l.user_id and str(l.user_id) in dept_map:
            return dept_map[str(l.user_id)]
        if l.user_name and l.user_name in name_map:
            return name_map[l.user_name]
        return (None, str(l.dept_id) if l.dept_id else None, None, None, None)

    return Response(
        data=[_loginlog_to_response(l, *_resolve(l)) for l in logs],
        meta=PaginationMeta(total=total, page=page, page_size=page_size).model_dump(),
    )


async def _is_super_admin(session: AsyncSession, user: User) -> bool:
    result = await session.execute(
        select(Role).join(UserRole).where(
            UserRole.user_id == user.id, Role.code == "super_admin"
        )
    )
    return result.scalar_one_or_none() is not None


async def _is_tenant_admin(session: AsyncSession, user: User) -> bool:
    result = await session.execute(
        select(Role).join(UserRole).where(
            UserRole.user_id == user.id, Role.code == "tenant_admin"
        )
    )
    return result.scalar_one_or_none() is not None


def _loginlog_to_response(l: LoginLog, display_name: str | None = None, dept_id: str | None = None,
                          dept_name: str | None = None, tenant_id: str | None = None, tenant_name: str | None = None) -> LoginLogResponse:
    return LoginLogResponse(
        id=str(l.id),
        user_id=str(l.user_id) if l.user_id else None,
        username=l.user_name,
        display_name=display_name or l.user_name,
        login_type=l.login_type,
        ip_address=l.ip_address,
        user_agent=l.user_agent,
        result=l.result,
        failure_reason=l.failure_reason,
        dept_id=dept_id,
        dept_name=dept_name,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        created_at=l.created_at,
    )


def _oplog_to_response(l: OperationLog, dept_name: str = "", user_display_name: str | None = None) -> OperationLogResponse:
    return OperationLogResponse(
        id=str(l.id),
        user_id=str(l.user_id) if l.user_id else None,
        user_name=l.user_name,
        display_name=user_display_name or l.user_name,
        dept_id=str(l.dept_id) if l.dept_id else None,
        dept_name=dept_name or None,
        action_type=l.action_type,
        resource_type=l.resource_type,
        resource_id=l.resource_id,
        resource_name=l.resource_name,
        detail=l.detail,
        ip_address=l.ip_address,
        user_agent=l.user_agent,
        result=l.result,
        error_message=l.error_message,
        duration_ms=l.duration_ms,
        created_at=l.created_at,
    )
