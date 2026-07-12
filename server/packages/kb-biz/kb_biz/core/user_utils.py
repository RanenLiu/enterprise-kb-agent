from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def generate_ep_number(
    session: AsyncSession,
    tenant_id: Optional[str] = None,
    tenant_code: Optional[str] = None,
) -> str:
    """Generate next EP number per tenant.

    Format: {tenant_code}_EP{number} (e.g. LingXI_EP00001) when tenant_code provided,
    or EP{number} (e.g. EP00001) for backward compatibility.

    If tenant_code not provided but tenant_id is, resolve tenant_code from DB.
    """
    if not tenant_code and tenant_id:
        from kb_biz.models.tenant import Tenant
        from sqlalchemy import select
        result = await session.execute(select(Tenant.code).where(Tenant.id == tenant_id))
        code = result.scalar_one_or_none()
        if code:
            tenant_code = str(code)

    prefix = f"{tenant_code}_" if tenant_code else ""
    # Use LIKE with parameterized prefix (safe from SQL injection)
    like_pattern = prefix + "EP____%"  # EP followed by at least 4 chars

    if tenant_id:
        result = await session.execute(
            text(
                "SELECT username FROM users "
                "WHERE username LIKE :pattern AND tenant_id = :tid"
            ),
            {"pattern": like_pattern, "tid": tenant_id},
        )
    else:
        result = await session.execute(
            text("SELECT username FROM users WHERE username LIKE :pattern"),
            {"pattern": like_pattern},
        )

    max_num = 0
    ep_re = re.compile(r"EP(\d+)$")
    for row in result:
        m = ep_re.search(row[0])
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num

    return f"{prefix}EP{max_num + 1:05d}"
