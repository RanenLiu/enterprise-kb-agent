"""LlamaIndex-powered retrieval service.

Replaces the custom RetrievalService with a LlamaIndex-backed implementation.
Vector search uses LlamaIndex's MilvusVectorStore + VectorIndexRetriever.
Reranking uses LlamaIndex's SentenceTransformerRerank.
Fulltext search (PGSearch) and RRF fusion remain custom (no adequate LlamaIndex replacement).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from kb_core.config import settings
from kb_core.rag.fusion import RRFMerge
from kb_core.rag.vector_li import LlamaIndexVectorSearch
from kb_core.rag.fulltext.pg import PGSearch
from kb_core.rag.fulltext.base import SearchResult
from kb_core.rag import strategies

logger = logging.getLogger("kb_core.rag.retrieval_li")

CHANNEL_TIMEOUT = 15  # seconds


def _rerank_sync(
    query: str,
    candidates: list[SearchResult],
    top_k: int,
) -> list[SearchResult]:
    """Cross-Encoder reranking via LlamaIndex's SentenceTransformerRerank."""
    if not candidates:
        return []

    from llama_index.core.postprocessor import SentenceTransformerRerank
    from llama_index.core.schema import NodeWithScore, TextNode

    reranker = SentenceTransformerRerank(
        model=settings.rerank_model,
        top_n=top_k,
    )

    nodes = [
        NodeWithScore(
            node=TextNode(text=r.content, metadata={
                "chunk_id": r.chunk_id, "doc_id": r.doc_id,
                "dept_id": r.dept_id, "heading_path": r.heading_path,
                "page_range": r.page_range, "source": r.source,
                "sources": r.sources, "visibility": r.visibility,
            }),
            score=r.score,
        )
        for r in candidates
    ]

    try:
        reranked = reranker.postprocess_nodes(nodes, query_str=query)
    except Exception as e:
        logger.warning("Reranker failed: %s", e)
        return candidates[:top_k]

    result_map = {r.chunk_id: r for r in candidates}
    results: list[SearchResult] = []
    for node in reranked:
        chunk_id = node.node.metadata.get("chunk_id", "")
        if chunk_id in result_map:
            result = result_map[chunk_id]
            result.score = float(node.score) if node.score is not None else result.score
            results.append(result)
    return results


class LlamaIndexRetrievalService:
    """Multi-channel retrieval with pluggable strategies.

    Pipeline:
      [HyDE → query expansion] → [vector + fulltext] → RRF → BM25 → Reranker

    Strategies (controlled by config or constructor):
      - HyDE: generate hypothetical answer for better vector matching
      - QueryFusion: multi-perspective query expansion
      - StepDecomp: complex question decomposition

    Same public interface as the original RetrievalService:
      search() -> list[dict]
      hybrid_search() -> list[dict]
    """

    def __init__(
        self,
        vector_search: LlamaIndexVectorSearch | None = None,
        fulltext_search: PGSearch | None = None,
        fusion: RRFMerge | None = None,
        use_hyde: bool | None = None,
        use_query_fusion: bool | None = None,
        use_step_decomp: bool | None = None,
    ):
        self._vector = vector_search or LlamaIndexVectorSearch()
        self._fulltext = fulltext_search
        self._fusion = fusion or RRFMerge()
        # Strategy flags: constructor arg > config default
        self._use_hyde = use_hyde if use_hyde is not None else settings.use_hyde
        self._use_query_fusion = use_query_fusion if use_query_fusion is not None else settings.use_query_fusion
        self._use_step_decomp = use_step_decomp if use_step_decomp is not None else settings.use_step_decomp

    async def search(
        self,
        query: str,
        dept_ids: list[str] | None = None,
        project_ids: list[str] | None = None,
        top_k: int = 20,
        query_embedding: list[float] | None = None,
        doc_ids: list[str] | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Multi-channel search: vector + fulltext, RRF fusion, rerank.

        Args:
            query: User question.
            dept_ids: Visible department IDs.
            project_ids: Visible project IDs.
            top_k: Final result count.
            query_embedding: Ignored (compat). LlamaIndex handles embedding internally.
            doc_ids: Optional, restrict to specific document IDs.

        Returns:
            Reranked top-k results as dicts.
        """
        if not query.strip():
            return []

        # ── Strategy: HyDE ──
        # 生成假设答案用于向量检索（语义更接近文档），全文检索仍用原 query
        vector_query = query
        if self._use_hyde and query_embedding is None:
            hyde_query = await strategies.hyde(query)
            if hyde_query != query:
                vector_query = hyde_query
                logger.info("Vector search using HyDE query: %s...", hyde_query[:60])

        tasks = []

        async def _vector_channel():
            try:
                return await asyncio.wait_for(
                    self._vector.search(vector_query, dept_ids, project_ids, top_k, doc_ids=doc_ids),
                    timeout=CHANNEL_TIMEOUT,
                )
            except Exception as e:
                logger.warning("Vector search failed: %s", e)
                return []

        async def _fulltext_channel():
            if not self._fulltext:
                return []
            try:
                return await asyncio.wait_for(
                    self._fulltext.search(query, dept_ids, top_k, doc_ids=doc_ids),
                    timeout=CHANNEL_TIMEOUT,
                )
            except Exception as e:
                logger.warning("Fulltext search failed: %s", e)
                return []

        # ── Strategy: QueryFusion ──
        # 多视角查询变体并行检索后融合（当前仅多路，后续可扩展为多变体）
        if self._use_query_fusion and query_embedding is None:
            f_queries = await strategies.query_fusion(query)
            if len(f_queries) > 1:
                tasks = []
                for fq in f_queries[:3]:  # 最多 3 个变体
                    tasks.append(self._vector.search(fq, dept_ids, project_ids, top_k, doc_ids=doc_ids))
                    if self._fulltext:
                        tasks.append(self._fulltext.search(fq, dept_ids, top_k, doc_ids=doc_ids))
                all_results = await asyncio.gather(*tasks, return_exceptions=True)
                vector_results = [r for r in all_results[:len(f_queries)] if not isinstance(r, Exception)]
                fulltext_results = [r for r in all_results[len(f_queries):] if not isinstance(r, Exception)]
                # Flatten all channel results
                all_chunks = []
                for vr in vector_results:
                    all_chunks.extend(vr if isinstance(vr, list) else [])
                for fr in fulltext_results:
                    all_chunks.extend(fr if isinstance(fr, list) else [])
                fused = self._fusion.merge([all_chunks], weights=[1.0])
                if not fused:
                    return []
                # 跳过正常双路流程，直接进入 BM25
                return await self._bm25_and_rerank(query, fused, top_k)

        # 标准双路并行
        tasks.append(_vector_channel())
        tasks.append(_fulltext_channel())
        vector_results, fulltext_results = await asyncio.gather(*tasks)

        # RRF fusion
        fused = self._fusion.merge(
            [vector_results, fulltext_results],
            weights=[0.5, 0.5],
        )
        if not fused:
            return []

        return await self._bm25_and_rerank(query, fused, top_k)

    async def _bm25_and_rerank(
        self, query: str, fused: list[SearchResult], top_k: int,
    ) -> list[dict[str, Any]]:
        """BM25 rescore + Cross-Encoder rerank."""
        if not fused:
            return []

        # BM25 rescore on fused (top 30)
        from kb_core.rag.bm25 import bm25_scores
        try:
            candidates = fused[:30]
            bm25 = bm25_scores(query, [{"content": r.content} for r in candidates])
            if bm25 and max(bm25) > 0:
                max_b = max(bm25)
                for r, s in zip(candidates, bm25):
                    r.score = s / max_b
            candidates.sort(key=lambda r: r.score, reverse=True)
            fused = candidates
        except Exception as e:
            logger.warning("BM25 rescore failed: %s", e)

        # Cross-Encoder rerank (top-30 → top-k)
        reranked = await asyncio.to_thread(_rerank_sync, query, fused[:30], top_k)
        return [r.model_dump() for r in reranked]

    async def hybrid_search(
        self,
        query: str,
        dept_ids: list[str] | None = None,
        top_k: int = 20,
        user_id: str | None = None,
        doc_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Compatibility alias. Calls self.search()."""
        return await self.search(
            query=query, dept_ids=dept_ids, top_k=top_k, doc_ids=doc_ids,
        )
