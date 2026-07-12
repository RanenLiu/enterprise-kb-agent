from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from kb_core.config import settings

if TYPE_CHECKING:
    from kb_core.rag.fulltext.base import SearchResult

logger = logging.getLogger("kb_core.rag.reranker")

_reranker = None


def _get_reranker():
    """Lazy-load Cross-Encoder 模型."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(
                settings.rerank_model,
                trust_remote_code=True,
            )
            logger.info("Cross-Encoder model loaded: %s", settings.rerank_model)
        except Exception as e:
            logger.warning("Failed to load Cross-Encoder model '%s': %s", settings.rerank_model, e)
            return None
    return _reranker


def rerank(
    query: str,
    candidates: list[SearchResult],
    top_k: int = 5,
) -> list[SearchResult]:
    """Cross-Encoder 对 query+chunk 逐对打分，取 Top-K.

    Args:
        query: 用户原始问题
        candidates: RRF 融合后的候选列表
        top_k: 最终返回条数

    Returns:
        按 Cross-Encoder 分数降序排列的 Top-K 结果
    """
    if not candidates:
        return []

    model = _get_reranker()
    if model is None:
        # 模型加载失败时降级: 原序返回 Top-K
        logger.warning("Reranker unavailable, returning candidates in original order")
        return candidates[:top_k]

    pairs = [(query, c.content[:2048]) for c in candidates]  # 截断长文本
    try:
        scores = model.predict(pairs, show_progress_bar=False)
        scored = list(zip(scores, candidates))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
        for score, item in top:
            item.score = float(score)
        return [item for _, item in top]
    except Exception as e:
        logger.warning("Reranker prediction failed: %s", e)
        return candidates[:top_k]


class Reranker:
    """Cross-Encoder 重排序器的可注入包装."""

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_k: int = 5,
    ) -> list[SearchResult]:
        return await asyncio.to_thread(rerank, query, candidates, top_k=top_k)
