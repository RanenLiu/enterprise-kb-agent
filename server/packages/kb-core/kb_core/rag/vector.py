from __future__ import annotations

import logging

from kb_core.indexing.service import get_milvus_collection
from kb_core.rag.fulltext.base import SearchResult

logger = logging.getLogger("kb_core.rag.vector")


class VectorSearch:
    """Milvus 向量检索，按部门和项目 Partition 过滤."""

    async def search(
        self,
        query: str,
        dept_ids: list[str],
        project_ids: list[str] | None = None,
        top_k: int = 20,
        query_embedding: list[float] | None = None,
        doc_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        """执行向量检索。

        Args:
            query: 原始查询文本（未使用，保留为接口兼容）。
            dept_ids: 可见部门 ID 列表。
            project_ids: 可见项目 ID 列表。
            top_k: 返回条数。
            query_embedding: 预计算的查询向量（1024-dim float list）。如未提供则返回空。
            doc_ids: 可选，限定检索的文档 ID 列表。用于跨轮对话中指定特定文档。

        Returns:
            list[SearchResult]: 按相似度降序排列。
        """
        if query_embedding is None:
            logger.warning("VectorSearch called without query_embedding, returning empty")
            return []

        collection = get_milvus_collection()
        if collection.num_entities == 0:
            return []

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}

        # 构建过滤表达式: 部门文档 + 全局公有文档 + 项目文档 + 指定文档
        dept_expr = ", ".join(f'"{d}"' for d in dept_ids)
        conditions = [f"(dept_id in [{dept_expr}] or visibility == 'public')"]

        if project_ids is not None:
            if not project_ids:
                conditions.append('project_id == ""')
            else:
                proj_expr = ", ".join(f'"{p}"' for p in project_ids)
                conditions.append(f"project_id in [{proj_expr}]")

        if doc_ids:
            doc_expr = ", ".join(f'"{d}"' for d in doc_ids)
            conditions.append(f"doc_id in [{doc_expr}]")

        expr = " or ".join(conditions)

        try:
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["doc_id", "dept_id", "visibility", "content", "heading_path", "page_range", "chunk_index"],
            )
        except Exception as e:
            logger.warning("Milvus search failed: %s", e)
            return []

        search_results: list[SearchResult] = []
        for hits in results:
            for hit in hits:
                fields = hit.fields if hasattr(hit, "fields") else {}
                search_results.append(SearchResult(
                    chunk_id=str(hit.id),
                    doc_id=fields.get("doc_id", ""),
                    dept_id=fields.get("dept_id", ""),
                    content=fields.get("content", ""),
                    heading_path=fields.get("heading_path", ""),
                    page_range=fields.get("page_range", ""),
                    score=float(hit.score),
                    source="vector",
                    visibility=fields.get("visibility", "dept"),
                ))
        return search_results
