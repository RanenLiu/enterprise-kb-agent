"""Tests for AgentState."""
from __future__ import annotations

import pytest

from kb_biz.modules.chat.state import AgentState


class TestAgentState:
    def test_default_fields(self):
        state = AgentState()
        assert state.session_id == ""
        assert state.user_id == ""
        assert state.dept_ids == []
        assert state.intent == ""
        assert state.search_results == []
        assert state.tool_calls == []
        assert state.tool_results == []

    def test_init_with_values(self):
        state = AgentState(
            session_id="sess-1",
            user_id="user-1",
            dept_ids=["dept-1"],
            intent="knowledge_query",
        )
        assert state.session_id == "sess-1"
        assert state.user_id == "user-1"
        assert state.dept_ids == ["dept-1"]
        assert state.intent == "knowledge_query"

    def test_model_dump_roundtrip(self):
        original = AgentState(
            session_id="sess-1",
            metadata={"query": "test"},
        )
        data = original.model_dump()
        restored = AgentState(**data)
        assert restored.session_id == "sess-1"
        assert restored.metadata.get("query") == "test"

    def test_metadata_default(self):
        state = AgentState()
        assert state.metadata == {}

    def test_guardrail_flags(self):
        state = AgentState(guardrail_flags=["harmful"])
        assert "harmful" in state.guardrail_flags
