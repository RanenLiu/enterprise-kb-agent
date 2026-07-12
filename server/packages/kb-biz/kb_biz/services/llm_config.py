"""LLM configuration service — queries the database for active LLM config."""

from __future__ import annotations

from sqlalchemy import select

from kb_biz.models.llm_config import LLMConfig


async def get_active_llm_config(session, tenant_id: str | None = None) -> dict | None:
    """Fetch the active LLM config from the database.

    Priority:
      1. Tenant-level default config (if tenant_id provided)
      2. Global default config (tenant_id = NULL)
      3. First active global config
      4. None -> fallback to env config
    """
    configs: list = []
    if tenant_id:
        result = await session.execute(
            select(LLMConfig).where(
                LLMConfig.tenant_id == tenant_id, LLMConfig.is_default == True  # noqa: E712
            )
        )
        configs.append(result.scalar_one_or_none())

    # Try global default (tenant_id = NULL)
    result = await session.execute(
        select(LLMConfig).where(
            LLMConfig.tenant_id.is_(None), LLMConfig.is_default == True  # noqa: E712
        )
    )
    configs.append(result.scalar_one_or_none())

    # Fallback: first active global config
    result = await session.execute(
        select(LLMConfig).where(
            LLMConfig.tenant_id.is_(None), LLMConfig.is_active == True  # noqa: E712
        ).order_by(LLMConfig.sort_order).limit(1)
    )
    configs.append(result.scalar_one_or_none())

    for cfg in configs:
        if cfg is not None:
            return {
                "provider": cfg.provider,
                "api_key_encrypted": cfg.api_key_encrypted,
                "base_url": cfg.base_url,
                "model": cfg.model,
                "max_tokens": cfg.max_tokens,
                "temperature": cfg.temperature / 10.0,
            }

    return None
