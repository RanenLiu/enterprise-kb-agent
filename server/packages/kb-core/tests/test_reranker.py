"""Tests for Cross-Encoder reranker — mocked model."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from kb_core.rag.fulltext.base import SearchResult
from kb_core.rag.reranker import Reranker


def _r(doc_id: str, content: str = "test content") -> SearchResult:
    return SearchResult(
        chunk_id=f"chunk-{doc_id}",
        doc_id=doc_id,
        dept_id="dept-1",
        content=content,
        heading_path="",
        page_range="",
        score=0.5,
        source="vector",
    )


class TestReranker:
    @pytest.mark.asyncio
    async def test_rerank_empty(self):
        r = Reranker()
        results = await r.rerank("query", [])
        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_no_model(self):
        """When model is not available, returns top_k from input."""
        r = Reranker()
        inputs = [_r(f"doc{i}") for i in range(5)]
        results = await r.rerank("query", inputs, top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rerank_top_k_limit(self):
        r = Reranker()
        inputs = [_r(f"doc{i}") for i in range(10)]
        results = await r.rerank("query", inputs, top_k=3)
        assert len(results) == 3
