from __future__ import annotations

import asyncio
import logging
from typing import Any

from kb_core.rag.vector import VectorSearch
from kb_core.rag.fulltext.pg import PGSearch
from kb_core.rag.fulltext.base import SearchResult
from kb_core.rag.fusion import RRFMerge
from kb_core.rag.reranker import Reranker

logger = logging.getLogger("kb_core.rag.service")

# Per-channel timeout to prevent any one retriever from hanging the pipeline
CHANNEL_TIMEOUT = 15  # seconds


class RetrievalService:
    """多路并行检索：向量 + 全文（图谱检索在 kb-enterprise 中扩展）"""

    def __init__(
        self,
        vector_search: VectorSearch,
        fulltext_search: PGSearch,
        fusion: RRFMerge,
        reranker: Reranker,
    ):
        self._vector = vector_search
        self._fulltext = fulltext_search
        self._fusion = fusion
        self._reranker = reranker

    async def search(
        self,
        query: str,
        dept_ids: list[str] | None = None,
        top_k: int = 20,
        query_embedding: list[float] | None = None,
        doc_ids: list[str] | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """双路搜索 + RRF 融合 + 重排序。

        Args:
            query: 用户问题原文。
            dept_ids: 用户可见部门 ID 列表。
            top_k: 最终返回条数。
            query_embedding: 预计算查询向量（可选，如不提供则跳过向量检索）。
            doc_ids: 可选，限定检索的文档 ID 列表。用于跨轮对话中指定特定文档。

        Returns:
            list[dict]: 精排后的 Top-K 结果。
        """
        if not query.strip():
            return []
        if not dept_ids:
            pass

        # 双路并行召回
        tasks = []

        async def _vector_channel():
            try:
                return await asyncio.wait_for(
                    self._vector.search(query, dept_ids, top_k, query_embedding=query_embedding, doc_ids=doc_ids),
                    timeout=CHANNEL_TIMEOUT,
                )
            except Exception as e:
                logger.warning("Vector search failed: %s", e)
                return []

        async def _fulltext_channel():
            try:
                return await asyncio.wait_for(
                    self._fulltext.search(query, dept_ids, top_k, doc_ids=doc_ids),
                    timeout=CHANNEL_TIMEOUT,
                )
            except Exception as e:
                logger.warning("Fulltext search failed: %s", e)
                return []

        tasks.append(_vector_channel())
        tasks.append(_fulltext_channel())
        vector_results, fulltext_results = await asyncio.gather(*tasks)

        # RRF 融合
        fused = self._fusion.merge(
            [vector_results, fulltext_results],
            weights=[0.5, 0.5],
        )

        if not fused:
            return []

        # BM25 rescore on fused results (top 30) — pure Python, no GPU needed
        from kb_core.rag.bm25 import bm25_scores
        try:
            candidates = fused[:30]
            bm25 = bm25_scores(query, [{"content": r.content} for r in candidates])
            # Normalize BM25 scores to [0, 1] range for consistent fusion
            if bm25 and max(bm25) > 0:
                max_b = max(bm25)
                for r, s in zip(candidates, bm25):
                    r.score = s / max_b
            candidates.sort(key=lambda r: r.score, reverse=True)
        except Exception as e:
            logger.warning("BM25 rescore failed: %s", e)
            candidates = fused[:30]

        # Cross-Encoder 精排（Top-30 → Top-K）
        reranked = await self._reranker.rerank(query, candidates[:30], top_k=top_k)
        return [r.model_dump() for r in reranked]

    async def hybrid_search(
        self,
        query: str,
        dept_ids: list[str] | None = None,
        top_k: int = 20,
        user_id: str | None = None,
        doc_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Compatibility alias for legacy callers. Calls self.search()."""
        return await self.search(query=query, dept_ids=dept_ids, top_k=top_k, doc_ids=doc_ids)
