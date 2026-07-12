from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.core.auth.deps import PermissionChecker, get_current_user
from kb_biz.core.exceptions import NotFoundException
from kb_adapter_postgres.session import get_session
from kb_biz.models.conversation import ConversationMessage, ConversationSession
from kb_biz.models.department import Department
from kb_biz.models.role import DepartmentRole, Role, UserRole
from kb_biz.models.user import User
from kb_biz.modules.chat.graph import run_agent
from kb_core.llm.client import LLMClient
from kb_biz.modules.chat.memory import clear_retrieval_cache
from kb_biz.services.llm_config import get_active_llm_config
from kb_biz.schemas.chat import ChatRequest, MessageResponse, SessionCreateResponse, SessionResponse
from kb_biz.schemas.common import Response

logger = logging.getLogger("kb_biz.api.chat")

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=Response[list[SessionResponse]])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    _user: User = Depends(PermissionChecker(["chat.access"])),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == current_user.id)
        .where(ConversationSession.status == "active")
        .order_by(ConversationSession.last_message_at.desc().nullsfirst())
    )
    sessions = result.scalars().all()
    return Response(data=[
        SessionResponse(
            id=str(s.id),
            title=s.title,
            message_count=s.message_count,
            last_message_at=s.last_message_at,
            created_at=s.created_at,
        )
        for s in sessions
    ])


@router.post("/sessions", response_model=Response[SessionCreateResponse])
async def create_session(
    current_user: User = Depends(get_current_user),
    _user: User = Depends(PermissionChecker(["chat.access"])),
    db_session: AsyncSession = Depends(get_session),
):
    cs = ConversationSession(user_id=current_user.id)
    db_session.add(cs)
    await db_session.flush()
    return Response(data=SessionCreateResponse(id=str(cs.id), title=cs.title))


@router.delete("/sessions/{session_id}", response_model=Response[None])
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _user: User = Depends(PermissionChecker(["chat.access"])),
    db_session: AsyncSession = Depends(get_session),
):
    cs = await db_session.get(ConversationSession, session_id)
    if not cs or cs.user_id != current_user.id:
        raise NotFoundException("Session")
    cs.status = "deleted"
    db_session.add(cs)
    await clear_retrieval_cache(str(session_id))
    return Response(data=None)


@router.get("/sessions/{session_id}/messages", response_model=Response[list[MessageResponse]])
async def list_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _user: User = Depends(PermissionChecker(["chat.access"])),
    db_session: AsyncSession = Depends(get_session),
):
    cs = await db_session.get(ConversationSession, session_id)
    if not cs or cs.user_id != current_user.id:
        raise NotFoundException("Session")

    result = await db_session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at)
    )
    messages = result.scalars().all()
    return Response(data=[
        MessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            metadata=m.metadata_,
            created_at=m.created_at,
        )
        for m in messages
    ])


@router.post("/message")
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    _user: User = Depends(PermissionChecker(["chat.access"])),
    db_session: AsyncSession = Depends(get_session),
):
    """SSE streaming message endpoint powered by the LangGraph agent.

    Yields events: intent, retrieval (optional), token (per chunk), done, error.
    """
    # 1. Resolve or create conversation session
    if request.session_id:
        session_id = request.session_id
        cs = await db_session.get(ConversationSession, uuid.UUID(session_id))
        if not cs or cs.user_id != current_user.id:
            raise NotFoundException("Session")
    else:
        cs = ConversationSession(user_id=current_user.id, dept_id=current_user.dept_id)
        db_session.add(cs)
        await db_session.flush()
        session_id = str(cs.id)

    # Use current user's dept_id for access control (session may have stale dept)
    dept_ids = [str(current_user.dept_id)] if current_user.dept_id else []

    # 2. Obtain LLM configuration (tenant-level → global fallback)
    llm_cfg = await get_active_llm_config(
        db_session, tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None
    )
    llm = LLMClient.from_config(llm_cfg) if llm_cfg else LLMClient()

    # 4. Run agent and stream SSE events
    return StreamingResponse(
        _stream_agent(
            session_id, str(current_user.id), dept_ids,
            request.content, llm,
            deep_thinking=request.deep_thinking,
            timezone=request.timezone,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


async def _stream_agent(
    session_id: str,
    user_id: str,
    dept_ids: list[str],
    query: str,
    llm: LLMClient,
    deep_thinking: bool = False,
    timezone: str = "+08:00",
) -> AsyncGenerator[str, None]:
    """Wrap run_agent and emit SSE-formatted events.

    NOTE: run_agent() yields dict[str, Any] objects (not JSON strings).
    """
    try:
        async for event_dict in run_agent(
            session_id=session_id,
            user_id=user_id,
            dept_ids=dept_ids,
            query=query,
            llm=llm,
            deep_thinking=deep_thinking,
            timezone=timezone,
        ):
            event_type = event_dict["event"]
            event_data = event_dict["data"]
            yield f"event: {event_type}\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
    except Exception:
        logger.exception("Agent error")
        yield f"event: error\ndata: {json.dumps({'code': 500, 'message': 'Internal error'}, ensure_ascii=False)}\n\n"


async def _is_super_admin(db_session: AsyncSession, user: User) -> bool:
    """Check whether the user has the super_admin role."""
    # Load user's direct role IDs
    user_role_result = await db_session.execute(
        select(UserRole.role_id).where(UserRole.user_id == user.id)
    )
    role_ids = {r for r in user_role_result.scalars().all()}

    # Add department-inherited roles
    if user.dept_id:
        dept_role_result = await db_session.execute(
            select(DepartmentRole.role_id).where(
                DepartmentRole.dept_id == user.dept_id
            )
        )
        role_ids.update(dept_role_result.scalars().all())

    if not role_ids:
        return False

    # Check role codes
    role_result = await db_session.execute(
        select(Role.code).where(Role.id.in_(role_ids))
    )
    role_codes = set(role_result.scalars().all())
    return "super_admin" in role_codes
