"""Tests for VectorSearch — mocked Milvus collection."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kb_core.rag.vector import VectorSearch


@pytest.fixture
def mock_collection():
    col = MagicMock()
    col.num_entities = 100
    return col


@pytest.mark.asyncio
@patch("kb_core.rag.vector.get_milvus_collection")
async def test_vector_search_empty_embedding(mock_get_col):
    vs = VectorSearch()
    result = await vs.search("query", dept_ids=["dept-1"])
    assert result == []


@pytest.mark.asyncio
@patch("kb_core.rag.vector.get_milvus_collection")
async def test_vector_search_with_embedding(mock_get_col, mock_collection):
    # Mock a search result hit
    mock_hit = MagicMock()
    mock_hit.id = 1
    mock_hit.score = 0.95
    mock_hit.fields = {
        "doc_id": "doc-1",
        "dept_id": "dept-1",
        "content": "test content",
        "heading_path": "",
        "page_range": "",
        "visibility": "public",
    }

    mock_collection.search.return_value = [[mock_hit]]
    mock_collection.num_entities = 100
    mock_get_col.return_value = mock_collection

    vs = VectorSearch()
    result = await vs.search(
        "query",
        dept_ids=["dept-1"],
        top_k=10,
        query_embedding=[0.1] * 1024,
    )

    assert len(result) == 1
    assert result[0].doc_id == "doc-1"
    assert result[0].score == 0.95
    assert result[0].source == "vector"
    mock_collection.search.assert_called_once()


@pytest.mark.asyncio
@patch("kb_core.rag.vector.get_milvus_collection")
async def test_vector_search_empty_collection(mock_get_col):
    col = MagicMock()
    col.num_entities = 0
    mock_get_col.return_value = col

    vs = VectorSearch()
    result = await vs.search(
        "query",
        dept_ids=["dept-1"],
        query_embedding=[0.1] * 1024,
    )
    assert result == []
