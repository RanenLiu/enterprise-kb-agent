"""Tests for LlamaIndexRetrievalService — mocked channels."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kb_core.rag.fulltext.base import SearchResult
from kb_core.rag.retrieval_li import LlamaIndexRetrievalService


def _make_result(chunk_id: str = "c1") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id, doc_id="doc-1", dept_id="d1",
        content="test content", score=0.9, source="vector",
    )


@pytest.fixture
def mock_service():
    vector = AsyncMock()
    fulltext = AsyncMock()
    fusion = MagicMock()
    svc = LlamaIndexRetrievalService(
        vector_search=vector,
        fulltext_search=fulltext,
        fusion=fusion,
    )
    return svc, vector, fulltext, fusion


@pytest.mark.asyncio
async def test_empty_query(mock_service):
    svc, *_ = mock_service
    assert await svc.search("") == []
    assert await svc.search("   ") == []


@pytest.mark.asyncio
async def test_calls_both_channels(mock_service):
    svc, vector, fulltext, fusion = mock_service
    vector.search.return_value = []
    fulltext.search.return_value = []
    fusion.merge.return_value = []

    with patch("kb_core.rag.retrieval_li._rerank_sync", return_value=[]):
        await svc.search("test query", dept_ids=["d1"])

    vector.search.assert_called_once()
    fulltext.search.assert_called_once()


@pytest.mark.asyncio
async def test_passes_dept_ids(mock_service):
    svc, vector, fulltext, fusion = mock_service
    vector.search.return_value = []
    fulltext.search.return_value = []
    fusion.merge.return_value = []

    await svc.search("test", dept_ids=["d1", "d2"])

    vector.search.assert_called_once()
    # dept_ids is 2nd positional arg
    args, _ = vector.search.call_args
    assert args[1] == ["d1", "d2"]


@pytest.mark.asyncio
async def test_rerank_called(mock_service):
    """Verify _rerank_sync is called when results are non-empty."""
    svc, vector, fulltext, fusion = mock_service
    result = _make_result()
    vector.search.return_value = [result]
    fulltext.search.return_value = []
    fusion.merge.return_value = [result]

    with patch("kb_core.rag.retrieval_li._rerank_sync", return_value=[result]) as mock_rerank:
        results = await svc.search("test", dept_ids=["d1"], top_k=5)
        mock_rerank.assert_called_once()
        assert len(results) > 0


@pytest.mark.asyncio
async def test_vector_channel_timeout(mock_service):
    svc, vector, fulltext, fusion = mock_service
    vector.search.side_effect = Exception("timeout")
    fulltext.search.return_value = []
    fusion.merge.return_value = []

    with patch("kb_core.rag.retrieval_li._rerank_sync", return_value=[]):
        result = await svc.search("test", dept_ids=["d1"])
    assert result == []


@pytest.mark.asyncio
async def test_hybrid_search_alias(mock_service):
    svc, vector, fulltext, fusion = mock_service
    vector.search.return_value = []
    fulltext.search.return_value = []
    fusion.merge.return_value = []

    with patch("kb_core.rag.retrieval_li._rerank_sync", return_value=[]):
        result = await svc.hybrid_search("test", dept_ids=["d1"])
    assert result == []
    vector.search.assert_called_once()
