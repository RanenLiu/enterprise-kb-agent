"""LlamaIndex-based vector search for Milvus.

Uses LlamaIndex's HuggingFaceEmbedding for query embedding, then searches
Milvus directly via pymilvus with full filter expression control.
This avoids MetadataFilters limitations with complex boolean expressions.
"""

from __future__ import annotations

import asyncio
import logging

from kb_core.config import settings
from kb_core.rag.fulltext.base import SearchResult

logger = logging.getLogger("kb_core.rag.vector_li")

# Lazy-loaded globals
_embed_model = None
_milvus_collection = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        _embed_model = HuggingFaceEmbedding(
            model_name=settings.embedding_model,
            normalize=True,
            device="cpu",
        )
    return _embed_model


def _get_milvus_collection():
    """Get or create the Milvus collection connection."""
    global _milvus_collection
    if _milvus_collection is not None:
        return _milvus_collection

    from pymilvus import Collection, connections

    connections.connect(
        alias="default",
        host=settings.milvus_host,
        port=settings.milvus_port,
        timeout=5,
    )

    _milvus_collection = Collection("document_chunks")
    _milvus_collection.load()
    return _milvus_collection


def _build_filter_expr(
    dept_ids: list[str] | None,
    project_ids: list[str] | None = None,
    doc_ids: list[str] | None = None,
) -> str | None:
    """Build a Milvus boolean expression filter string.

    Reproduces the same filter logic as the original VectorSearch:
      (dept_id in [...] OR visibility == 'public')
      AND (project_id in [...] OR project_id == "")
      AND (doc_id in [...])
    """
    conditions: list[str] = []

    if dept_ids:
        dept_expr = ", ".join(f'"{d}"' for d in dept_ids)
        conditions.append(f"(dept_id in [{dept_expr}] or visibility == 'public')")

    if project_ids is not None:
        if not project_ids:
            conditions.append('project_id == ""')
        else:
            proj_expr = ", ".join(f'"{p}"' for p in project_ids)
            conditions.append(f"project_id in [{proj_expr}]")

    if doc_ids:
        doc_expr = ", ".join(f'"{d}"' for d in doc_ids)
        conditions.append(f"doc_id in [{doc_expr}]")

    if not conditions:
        return None

    return " and ".join(conditions)


def _search_sync(
    query: str,
    dept_ids: list[str] | None,
    project_ids: list[str] | None,
    top_k: int,
    doc_ids: list[str] | None,
) -> list[SearchResult]:
    """Synchronous vector search: embed query via LlamaIndex, search via pymilvus."""
    if not query.strip():
        return []

    # 1. Get query embedding via LlamaIndex
    embed_model = _get_embed_model()
    query_embedding = embed_model.get_query_embedding(query)

    # 2. Search Milvus directly with full filter control
    collection = _get_milvus_collection()
    if collection.num_entities == 0:
        return []

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
    expr = _build_filter_expr(dept_ids, project_ids, doc_ids)

    try:
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["doc_id", "dept_id", "visibility", "content",
                           "heading_path", "page_range", "chunk_index"],
        )
    except Exception as e:
        logger.warning("Milvus vector search failed: %s", e)
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


class LlamaIndexVectorSearch:
    """LlamaIndex-powered vector search.

    Uses HuggingFaceEmbedding for query embedding, then searches Milvus
    directly via pymilvus — preserving full filter expression control.
    """

    async def search(
        self,
        query: str,
        dept_ids: list[str] | None = None,
        project_ids: list[str] | None = None,
        top_k: int = 20,
        query_embedding: list[float] | None = None,
        doc_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        if not query.strip():
            return []

        return await asyncio.to_thread(
            _search_sync,
            query,
            dept_ids,
            project_ids,
            top_k,
            doc_ids,
        )
