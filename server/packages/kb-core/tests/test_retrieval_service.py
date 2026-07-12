"""Tests for RetrievalService — mocked channels."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kb_core.rag.service import RetrievalService


@pytest.fixture
def mock_service():
    vector = AsyncMock()
    fulltext = AsyncMock()
    fusion = MagicMock()
    reranker = AsyncMock()
    svc = RetrievalService(vector, fulltext, fusion, reranker)
    return svc, vector, fulltext, fusion, reranker


@pytest.mark.asyncio
async def test_empty_query(mock_service):
    svc, *_ = mock_service
    assert await svc.search("") == []
    assert await svc.search("   ") == []


@pytest.mark.asyncio
async def test_calls_both_channels(mock_service):
    svc, vector, fulltext, fusion, reranker = mock_service
    vector.search.return_value = []
    fulltext.search.return_value = []
    fusion.merge.return_value = []
    reranker.rerank = AsyncMock(return_value=[])

    await svc.search("test query", dept_ids=["d1"])
    vector.search.assert_called_once()
    fulltext.search.assert_called_once()


@pytest.mark.asyncio
async def test_passes_dept_ids(mock_service):
    svc, vector, fulltext, fusion, reranker = mock_service
    vector.search.return_value = []
    fulltext.search.return_value = []
    fusion.merge.return_value = []
    reranker.rerank = AsyncMock(return_value=[])

    await svc.search("test", dept_ids=["d1", "d2"])
    _, v_kwargs = vector.search.call_args
    _, f_kwargs = fulltext.search.call_args
    assert vector.search.call_args[0][1] == ["d1", "d2"]
    assert fulltext.search.call_args[0][1] == ["d1", "d2"]


@pytest.mark.asyncio
async def test_rerank_called_with_top_k(mock_service):
    svc, vector, fulltext, fusion, reranker = mock_service
    mock_result = MagicMock()
    mock_result.doc_id = "doc-1"
    mock_result.model_dump.return_value = {"doc_id": "doc-1"}
    vector.search.return_value = [mock_result]
    fulltext.search.return_value = []
    fusion.merge.return_value = [mock_result]
    reranker.rerank = AsyncMock(return_value=[mock_result])

    await svc.search("test", dept_ids=["d1"], top_k=5)
    reranker.rerank.assert_called_once()
    assert reranker.rerank.call_args[1].get("top_k") == 5


@pytest.mark.asyncio
async def test_vector_channel_timeout(mock_service):
    svc, vector, fulltext, fusion, reranker = mock_service
    vector.search.side_effect = Exception("timeout")
    fulltext.search.return_value = []
    fusion.merge.return_value = []
    reranker.rerank = AsyncMock(return_value=[])

    # Should not raise; timeout is caught and logged
    result = await svc.search("test", dept_ids=["d1"])
    assert result == []


@pytest.mark.asyncio
async def test_hybrid_search_alias(mock_service):
    svc, vector, fulltext, fusion, reranker = mock_service
    vector.search.return_value = []
    fulltext.search.return_value = []
    fusion.merge.return_value = []
    reranker.rerank = AsyncMock(return_value=[])

    result = await svc.hybrid_search("test", dept_ids=["d1"])
    assert result == []
    vector.search.assert_called_once()
