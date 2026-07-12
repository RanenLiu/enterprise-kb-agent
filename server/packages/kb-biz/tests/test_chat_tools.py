"""Tests for kb-biz chat tools — mocked DB session."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kb_biz.modules.chat.tools import query_documents


def _make_row(**kwargs):
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


@pytest.fixture
def mock_db():
    with patch("kb_adapter_postgres.session.async_session_factory") as factory:
        mock_session = AsyncMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__.return_value = mock_session
        factory.return_value = mock_cm
        yield factory, mock_session


@pytest.mark.asyncio
async def test_query_documents_by_keyword(mock_db):
    _, mock_session = mock_db
    mock_session.execute.return_value = [
        _make_row(
            id="doc-123",
            file_name="Java后端核心高频面试题.md",
            status="ready",
            created_at="2026-07-09",
            updated_at=None,
            dept_id="dept-1",
            chunk_count=55,
            visibility="dept",
        )
    ]

    result = await query_documents(keyword="java面试")
    assert len(result["documents"]) == 1
    assert result["documents"][0]["file_name"] == "Java后端核心高频面试题.md"


@pytest.mark.asyncio
async def test_query_documents_empty_result(mock_db):
    _, mock_session = mock_db
    mock_session.execute.return_value = []

    result = await query_documents(keyword="nonexistent")
    assert len(result["documents"]) == 0
    assert result["documents"] == []


@pytest.mark.asyncio
async def test_query_documents_by_status(mock_db):
    _, mock_session = mock_db
    mock_session.execute.return_value = [
        _make_row(
            id="doc-456",
            file_name="test.md",
            status="ready",
            created_at="2026-07-09",
            updated_at=None,
            dept_id="dept-1",
            chunk_count=10,
            visibility="public",
        )
    ]

    result = await query_documents(status="ready")
    assert len(result["documents"]) == 1
    assert result["documents"][0]["status"] == "ready"


@pytest.mark.asyncio
async def test_query_documents_invalid_status(mock_db):
    _, mock_session = mock_db
    mock_session.execute.return_value = []

    result = await query_documents(status="invalid_status")
    assert len(result["documents"]) == 0


@pytest.mark.asyncio
async def test_query_documents_pagination(mock_db):
    _, mock_session = mock_db
    mock_session.execute.return_value = [
        _make_row(
            id=f"doc-{i}",
            file_name=f"doc{i}.md",
            status="ready",
            created_at="2026-07-09",
            updated_at=None,
            dept_id="dept-1",
            chunk_count=i,
            visibility="dept",
        )
        for i in range(5)
    ]

    result = await query_documents(limit=5)
    assert len(result["documents"]) == 5
