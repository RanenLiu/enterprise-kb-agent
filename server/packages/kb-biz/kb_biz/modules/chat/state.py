"""LangGraph Agent 状态定义。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from kb_core.rag.fulltext.base import SearchResult


class AgentState(BaseModel):
    """LangGraph Agent 状态，保存问答流程中所有节点间的数据传递。

    使用 Pydantic BaseModel 支持属性访问（state.session_id）和字典访问两种方式。
    """

    model_config = {"arbitrary_types_allowed": True}

    # 会话元数据
    session_id: str = ""
    user_id: str = ""
    dept_ids: list[str] = Field(default_factory=list)
    is_super_admin: bool = False

    # 意图与安全
    intent: str = ""
    guardrail_flags: list[str] = Field(default_factory=list)

    # 检索结果
    search_results: list[SearchResult] = Field(default_factory=list)

    # 记忆
    short_term_summary: str = ""
    long_term_memories: str = ""

    # 工具调用
    tool_calls: list[dict] = Field(default_factory=list)  # [{"tool": "...", "args": {...}}]
    tool_results: list[dict] = Field(default_factory=list)  # [{"tool": "...", "result": {...}}]

    # 其他
    llm_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
