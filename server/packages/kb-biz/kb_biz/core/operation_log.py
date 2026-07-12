"""Audit log utility. Call in CRUD endpoints to record operator, resource, and result."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.models.log import OperationLog
from kb_biz.models.user import User


async def record_operation(
    session: AsyncSession,
    user: User,
    action_type: str,       # create / update / delete / upload / login / publish / unpublish / reindex
    resource_type: str,     # document / department / role / user / menu / llm_config / session / auth / profile / password
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
    result: str = "success",
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Record an operation log entry."""
    log = OperationLog(
        user_id=user.id,
        user_name=user.username,
        tenant_id=user.tenant_id,
        dept_id=user.dept_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        detail=detail,
        ip_address=ip_address,
        result=result,
        error_message=error_message,
        duration_ms=duration_ms,
        created_at=datetime.now(timezone.utc),
    )
    session.add(log)
