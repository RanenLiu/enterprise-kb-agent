"""Tests for execute_tool and tool registry."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from kb_biz.modules.chat.tools import execute_tool, get_tool_definitions, _tool_registry


class TestToolRegistry:
    def test_get_definitions(self):
        """Should return registered tools with schema."""
        defs = get_tool_definitions()
        assert isinstance(defs, list)
        names = [t["name"] for t in defs]
        assert "get_current_time" in names
        assert "query_documents" in names

    def test_definitions_have_schema(self):
        defs = get_tool_definitions()
        for t in defs:
            assert "name" in t
            assert "description" in t
            assert "parameters" in t
            assert "type" in t["parameters"]
            assert "properties" in t["parameters"]


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    result = await execute_tool("non_existent", {}, dept_ids=[])
    assert "error" in result


@pytest.mark.asyncio
async def test_execute_time_tool():
    """get_current_time should return time data."""
    result = await execute_tool("get_current_time", {"timezone": "+08:00"}, dept_ids=[])
    assert "error" not in result
    assert "utc_time" in result
    assert "local_time" in result


@pytest.mark.asyncio
async def test_execute_time_tool_default_timezone():
    """Should default to +08:00 timezone."""
    result = await execute_tool("get_current_time", {}, dept_ids=[])
    assert "utc_time" in result
    assert "local_time" in result


@pytest.mark.asyncio
async def test_execute_injects_dept_ids():
    """execute_tool should inject dept_ids into tools that accept it."""

    async def _test_tool(query: str, dept_ids: list[str] | None = None):
        return {"dept_ids": dept_ids}

    _tool_registry["_test_dept"] = {"name": "_test_dept", "fn": _test_tool, "parameters": {}}
    try:
        result = await execute_tool("_test_dept", {"query": "test"}, dept_ids=["d1", "d2"])
        assert result["dept_ids"] == ["d1", "d2"]
    finally:
        del _tool_registry["_test_dept"]


@pytest.mark.asyncio
async def test_execute_tool_error_handling():
    """Should return error dict when tool raises."""

    async def _broken_tool():
        raise ValueError("something broke")

    _tool_registry["_broken"] = {"name": "_broken", "fn": _broken_tool, "parameters": {}}
    try:
        result = await execute_tool("_broken", {}, dept_ids=[])
        assert "error" in result
    finally:
        del _tool_registry["_broken"]
