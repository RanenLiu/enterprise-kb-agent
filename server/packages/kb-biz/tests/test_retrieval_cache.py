"""Tests for the multi-round retrieval cache."""

import json

import pytest
from kb_biz.modules.chat.memory import (
    _retrieval_cache_key,
    clear_retrieval_cache,
    match_retrieval_cache,
    push_retrieval_cache,
)


@pytest.mark.asyncio
async def test_push_and_match_cache(redis_client):
    """Test that pushing a cache entry and matching it works."""
    session_id = "test-session-123"
    query = "销售报告"
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    chunks = [{"doc_id": "doc1", "content": "Q3销售数据", "score": 0.95}]

    await clear_retrieval_cache(session_id)
    await push_retrieval_cache(session_id, query, embedding, chunks)

    result = await match_retrieval_cache(session_id, embedding)
    assert result is not None
    assert result["query"] == query


@pytest.mark.asyncio
async def test_cache_lru_eviction(redis_client):
    """Test that cache maintains at most 3 rounds (LRU eviction)."""
    session_id = "test-session-lru"
    # Use non-parallel vectors so cosine similarity distinguishes them
    for i in range(5):
        emb = [1.0 if j == i else 0.0 for j in range(5)]
        await push_retrieval_cache(session_id, f"query-{i}", emb, [])

    # Verify only 3 entries remain after 5 pushes (max 3)
    key = _retrieval_cache_key(session_id)
    raw = await redis_client.get(key)
    cache = json.loads(raw) if raw else []
    queries = [entry["query"] for entry in cache]
    assert len(cache) == 3, f"Expected 3 cached entries, got {len(cache)}"
    assert "query-0" not in queries, "Oldest entry query-0 should have been evicted"
    assert "query-1" not in queries, "Oldest entry query-1 should have been evicted"
    assert queries == ["query-2", "query-3", "query-4"], (
        f"Expected newest 3 entries, got {queries}"
    )

    # Best match should be query-4 (one-hot at index 4, cos sim = 1.0)
    search_emb = [0.0, 0.0, 0.0, 0.0, 1.0]
    result = await match_retrieval_cache(session_id, search_emb, threshold_low=0.6)
    assert result is not None
    assert result["query"] == "query-4", f"Expected query-4, got {result['query']}"


@pytest.mark.asyncio
async def test_cache_no_match(redis_client):
    """Test that unrelated queries don't match."""
    session_id = "test-session-nomatch"
    await clear_retrieval_cache(session_id)
    await push_retrieval_cache(session_id, "销售报告", [1.0, 0.0, 0.0], [])

    result = await match_retrieval_cache(session_id, [0.0, 1.0, 0.0])
    assert result is None


@pytest.mark.asyncio
async def test_cache_clear(redis_client):
    """Test that clearing the cache works."""
    session_id = "test-session-clear"
    await push_retrieval_cache(session_id, "test", [0.1, 0.2], [])
    await clear_retrieval_cache(session_id)

    result = await match_retrieval_cache(session_id, [0.1, 0.2], threshold_low=0.1)
    assert result is None


@pytest.mark.asyncio
async def test_cache_key_format(redis_client):
    """Test that the cache key follows the expected format."""
    key = _retrieval_cache_key("my-session-456")
    assert key == "session:my-session-456:retrieval_cache"
