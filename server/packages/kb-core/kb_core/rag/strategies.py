"""检索增强策略：HyDE、QueryFusion、StepDecomp。

每个策略是一个独立的 async 函数，接收 query 和可选 llm_client，
返回转换后的查询或查询列表，可自由组合。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kb_core.rag.strategies")

# ── Prompts ──────────────────────────────────────────────────────────

HYDE_SYSTEM_PROMPT = (
    "你是一个检索辅助助手。用户的问题可能无法直接匹配知识库文档的措辞。"
    "请根据问题生成一段假设性的回答文本，这段文本应该：\n"
    "1. 用陈述句描述问题对应的答案，就像知识库中会写的那样\n"
    "2. 包含关键的业务术语和实体名称\n"
    "3. 50-150 字，简洁准确\n"
    "只输出假设回答文本，不要解释。"
)

QUERY_FUSION_SYSTEM_PROMPT = (
    "你是一个检索优化助手。将用户的问题改写成 3-5 个不同角度的检索查询，"
    "每个查询覆盖问题的不同方面或使用不同的措辞。\n"
    "输出 JSON 字符串数组格式，如 [\"查询1\", \"查询2\", \"查询3\"]。\n"
    "只输出 JSON 数组，不要其他内容。"
)

DECOMP_SYSTEM_PROMPT = (
    "你是一个任务分解助手。分析用户问题是否包含多个独立的子问题。\n"
    "如果问题可以分解为多个子问题，输出 JSON 字符串数组，如 [\"子问题1\", \"子问题2\"]。\n"
    "如果问题很简单无需分解，输出空数组 []。\n"
    "只输出 JSON 数组，不要其他内容。"
)


# ── Strategy: HyDE ───────────────────────────────────────────────────

async def hyde(query: str, llm_client: Any | None = None) -> str:
    """Hypothetical Document Embedding: 生成假设答案替换查询进行向量检索。

    向量检索用假设答案做 embedding（语义更接近目标文档），
    全文检索仍用原 query（关键词匹配更准）。

    Returns:
        假设回答文本。如果 LLM 调用失败则返回原 query。
    """
    if not query.strip():
        return query

    from kb_core.llm.client import LLMClient

    client = llm_client or LLMClient()
    try:
        hypo = await client.chat(
            prompt=f"问题：{query}\n\n请生成一段假设性的回答文本：",
            system_prompt=HYDE_SYSTEM_PROMPT,
        )
        hypo = hypo.strip().strip('"').strip("'")
        if hypo and len(hypo) > 10:
            logger.info("HyDE: %s... → %s...", query[:30], hypo[:60])
            return hypo
    except Exception as e:
        logger.warning("HyDE generation failed: %s", e)

    return query


# ── Strategy: QueryFusion ────────────────────────────────────────────

async def query_fusion(query: str, llm_client: Any | None = None) -> list[str]:
    """Query Fusion: 生成多个视角的查询变体，并行检索后融合。

    Returns:
        查询变体列表。如果 LLM 调用失败则只返回原 query。
    """
    if not query.strip():
        return [query]

    from kb_core.llm.client import LLMClient

    client = llm_client or LLMClient()
    try:
        result = await client.chat_json(
            prompt=f"用户问题：{query}\n\n请从不同角度生成多个检索查询：",
            system_prompt=QUERY_FUSION_SYSTEM_PROMPT,
        )
        if isinstance(result, list):
            variants = [str(q).strip().strip('"') for q in result if isinstance(q, str) and q.strip()]
            if variants:
                # 把原文也加入，保证不丢失原意
                all_queries = [query] + [v for v in variants if v != query]
                logger.info("QueryFusion: %s → %d variants", query[:30], len(all_queries))
                return all_queries
    except Exception as e:
        logger.warning("QueryFusion failed: %s", e)

    return [query]


# ── Strategy: StepDecomp ─────────────────────────────────────────────

async def step_decomp(query: str, llm_client: Any | None = None) -> list[str]:
    """Step Decomposition: 将复杂问题拆解为多个子问题依次检索。

    Returns:
        子问题列表（原问题 + 子问题）。如果无需分解则只返回原 query。
    """
    if not query.strip():
        return [query]

    from kb_core.llm.client import LLMClient

    client = llm_client or LLMClient()
    try:
        result = await client.chat_json(
            prompt=f"用户问题：{query}\n\n请分析是否需要分解为子问题：",
            system_prompt=DECOMP_SYSTEM_PROMPT,
        )
        if isinstance(result, list) and len(result) > 0:
            sub_queries = [str(q).strip().strip('"') for q in result if isinstance(q, str) and q.strip()]
            if sub_queries:
                all_queries = [query] + sub_queries
                logger.info("StepDecomp: %s → %d sub-queries", query[:30], len(all_queries))
                return all_queries
    except Exception as e:
        logger.warning("StepDecomp failed: %s", e)

    return [query]
