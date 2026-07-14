"""Tests for LlamaIndexVectorSearch — filter building and search interface."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from kb_core.rag.vector_li import LlamaIndexVectorSearch, _build_filter_expr


class TestBuildFilters:
    """Unit tests for the Milvus boolean expression filter builder."""

    def test_empty(self):
        assert _build_filter_expr(None) is None
        assert _build_filter_expr([]) is None

    def test_dept_ids_only(self):
        expr = _build_filter_expr(["d1", "d2"])
        assert expr is not None
        assert "d1" in expr
        assert "d2" in expr
        assert "visibility == 'public'" in expr

    def test_empty_project_ids(self):
        expr = _build_filter_expr(["d1"], project_ids=[])
        assert expr is not None
        assert 'project_id == ""' in expr

    def test_project_ids(self):
        expr = _build_filter_expr(["d1"], project_ids=["p1", "p2"])
        assert expr is not None
        assert "p1" in expr
        assert "p2" in expr

    def test_doc_ids(self):
        expr = _build_filter_expr(["d1"], doc_ids=["doc1", "doc2"])
        assert expr is not None
        assert "doc1" in expr
        assert "doc2" in expr

    def test_all_filters(self):
        expr = _build_filter_expr(["d1"], project_ids=["p1"], doc_ids=["doc1"])
        assert expr is not None
        assert "dept_id" in expr
        assert "project_id" in expr
        assert "doc_id" in expr
        # Verify logical AND between conditions
        assert "and" in expr.lower()


@pytest.mark.asyncio
async def test_search_empty_query():
    svc = LlamaIndexVectorSearch()
    result = await svc.search("")
    assert result == []


@pytest.mark.asyncio
async def test_search_blank_query():
    svc = LlamaIndexVectorSearch()
    result = await svc.search("   ")
    assert result == []


@pytest.mark.asyncio
async def test_search_calls_retrieve():
    """Verify search() attempts to run retrieval (mocked at asyncio.to_thread)."""
    svc = LlamaIndexVectorSearch()
    with patch("kb_core.rag.vector_li.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = []
        result = await svc.search("hello", dept_ids=["d1"])
        assert result == []
        mock_thread.assert_called_once()
