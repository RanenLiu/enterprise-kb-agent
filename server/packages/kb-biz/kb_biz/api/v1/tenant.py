from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_adapter_postgres.session import get_session
from kb_biz.core.auth.deps import RoleChecker, get_current_user
from kb_biz.models.tenant import Tenant
from kb_biz.models.user import User
from kb_biz.schemas.common import Response

router = APIRouter()


@router.get("/admin/tenant", response_model=Response)
async def get_tenant(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tenant = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant.scalar_one_or_none()
    if tenant:
        return Response(data={"name": tenant.name, "logo": tenant.logo})
    return Response(data={"name": "企业知识库", "logo": None})


@router.put("/admin/tenant", response_model=Response)
async def update_tenant(
    body: dict,
    current_user: User = Depends(get_current_user),
    _: User = Depends(RoleChecker(["super_admin", "tenant_admin"])),
    session: AsyncSession = Depends(get_session),
):
    name = body.get("name", "企业知识库")
    logo = body.get("logo")

    tenant = await session.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant.scalar_one_or_none()
    if tenant:
        tenant.name = name
        if logo is not None:
            tenant.logo = logo
        session.add(tenant)
        await session.commit()
    return Response(data={"name": name, "logo": logo})


@router.get("/admin/tenants", response_model=Response)
async def list_tenants():
    return Response(
        data=[
            {"id": "default", "name": "企业知识库", "code": "default", "status": 1}
        ],
        meta={"total": 1, "page": 1, "page_size": 20},
    )
