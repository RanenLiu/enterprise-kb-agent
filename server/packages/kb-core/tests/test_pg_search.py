"""Tests for PGSearch — mocked async session."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kb_core.rag.fulltext.pg import PGSearch, _extract_terms


class TestExtractTerms:
    def test_empty_query(self):
        # Empty string returns fallback terms, not an empty list
        assert isinstance(_extract_terms(""), list)

    def test_short_query(self):
        terms = _extract_terms("hi")
        assert len(terms) <= 2

    def test_chinese_query(self):
        terms = _extract_terms("java面试题")
        assert any("java" in t.lower() for t in terms)
        assert any("面试" in t for t in terms)

    def test_english_query(self):
        terms = _extract_terms("hello world test")
        assert len(terms) >= 1

    def test_stop_words_removed(self):
        terms = _extract_terms("的 了 是 在 有 important")
        # Stop words should be filtered out
        assert all(len(t) >= 2 for t in terms)


class TestPGSearch:
    @pytest.fixture
    def search(self):
        mock_factory = MagicMock()
        return PGSearch(async_session_factory=mock_factory)

    @pytest.mark.asyncio
    async def test_empty_query(self, search):
        result = await search.search("", dept_ids=["d1"])
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_dept_ids(self, search):
        """Should not crash when dept_ids is empty."""
        result = await search.search("test", dept_ids=[])
        assert result == []

    @pytest.mark.asyncio
    async def test_tsvector_success(self, search):
        """Should return tsvector results when available."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.doc_id = "doc-1"
        mock_row.dept_id = "dept-1"
        mock_row.content = "test content"
        mock_row.heading_path = ""
        mock_row.visualization = "dept"
        mock_row.score = 0.95
        mock_row.visibility = "dept"

        mock_session = AsyncMock()
        mock_session.execute.return_value = [mock_row]

        mock_cm = MagicMock()
        mock_cm.__aenter__.return_value = mock_session
        search._async_session_factory.return_value = mock_cm

        results = await search.search("test", dept_ids=["dept-1"])
        assert len(results) == 1
        assert results[0].doc_id == "doc-1"
        assert results[0].source == "fulltext"

    @pytest.mark.asyncio
    async def test_tsvector_fallback_to_ilike(self, search):
        """When tsvector returns nothing, it should fall back to ILIKE."""
        # First call (tsvector) returns empty
        mock_session = AsyncMock()
        mock_session.execute.side_effect = [[], []]

        mock_cm = MagicMock()
        mock_cm.__aenter__.return_value = mock_session
        search._async_session_factory.return_value = mock_cm

        results = await search.search("test", dept_ids=["dept-1"])
        assert results == []
