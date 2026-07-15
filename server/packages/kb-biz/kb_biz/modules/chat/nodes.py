"""LangGraph Agent 节点：意图识别、问题重写、工具选择、记忆加载、上下文组装、LLM 流式生成。"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from kb_biz.modules.chat.guardrail import (
    check_guardrail,
    classify_intent,
)
from kb_biz.modules.chat.memory import (
    get_relevant_memories,
    get_session_summary,
)
from kb_biz.modules.chat.state import AgentState
from kb_core.llm.client import LLMClient
from kb_biz.services.instances import retrieval_service

logger = logging.getLogger("kb_biz.chat.nodes")

SYSTEM_PROMPT_BASE = """你是企业知识库的智能助手。请基于以下上下文和自身知识回答用户问题。

回答原则：
- 如果提供了知识库检索结果，必须基于检索结果回答，不要编造不存在的内容
- 知识库结果不足以回答时，如实告知用户
- 超出知识库范围的常识问题可以直接回答
- 安全：拒绝回答有害、越权或涉及敏感信息的问题
- 简洁：只回答用户问的具体内容，不要罗列全部信息，不要补充无关内容"""


async def intent_recognition(state: AgentState, llm: LLMClient) -> dict[str, Any]:
    """意图识别节点。

    用 LLM 将用户问题分类为预定义的意图标签，然后执行 guardrail 检查。
    """
    result = await classify_intent(llm, state.metadata.get("query", ""))
    return {
        "intent": result["intent"],
        "guardrail_flags": check_guardrail(result["intent"]),
        "metadata": {
            **state.metadata,
            "intent_reasoning": result.get("reasoning", ""),
            "intent_confidence": result.get("confidence", 0.0),
        },
    }


async def question_rewriting(state: AgentState, llm: LLMClient) -> dict[str, Any]:
    """问题重写节点：根据对话历史消解当前问题的代词指代。

    例如：历史="汇丰老旧系统数据迁移方案里写了什么？"
         当前="它的适用场景是什么？"
         重写后="汇丰老旧系统数据迁移方案的适用场景是什么？"
    """
    query = state.metadata.get("query", "")

    # 从 Redis 获取最近对话历史
    try:
        from kb_biz.modules.chat.memory import get_session_messages

        msgs = await get_session_messages(state.session_id)
        # 取最近 4 轮对话
        recent = msgs[-8:] if len(msgs) > 8 else msgs
    except Exception:
        recent = []

    history_text = ""
    if recent:
        history_text = "\n".join(
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
            for m in recent
        )

    # 只有有历史时才重写
    rewritten = query
    if history_text:
        try:
            rewritten = await llm.chat(
                prompt=(
                    f"以下是对话历史：\n{history_text}\n\n"
                    f"当前用户问题：{query}\n\n"
                    "请根据对话历史，将当前问题重写为一个不依赖上下文的独立问题。"
                    "消解其中的代词（它、这、那、它们等），补充缺失的指代信息。"
                    "直接输出重写后的问题，不要解释。"
                ),
                system_prompt="你擅长对话指代消解和问题重写。",
            )
            rewritten = rewritten.strip().strip('"').strip("'") or query
        except Exception:
            logger.warning("Question rewriting failed, using original query")
            rewritten = query

    return {
        "metadata": {
            **state.metadata,
            "query": rewritten,
            "original_query": query,
        }
    }


async def tool_selector(state: AgentState, llm: LLMClient) -> dict[str, Any]:
    """LLM 根据用户问题决定调用哪些工具。

    取代之前的硬编码 retrieval 节点。LLM 输出 JSON 工具调用列表，
    系统执行后结果注入 context_assembly。
    """
    from kb_biz.modules.chat.tools import execute_tool, get_tool_definitions

    query = state.metadata.get("query", "")

    prompt = (
        f"用户问题：{query}\n\n"
        "判断是否需要调用工具来回答。工具列表：\n"
        f"{json.dumps(get_tool_definitions(), ensure_ascii=False, indent=2)}\n\n"
        "根据问题选择合适的工具，注意看每个工具的描述和参数说明。\n"
        "如果用户问文档内容/业务知识，应该先用 query_documents 查文档名，再调 retrieve_knowledge。\n"
        "闲聊问候不需要工具。\n\n"
        "输出 JSON：{\"tool_calls\": [{\"tool\": \"工具名\", \"args\": {...}}]} 或 {\"tool_calls\": []}"
    )

    try:
        result = await llm.chat_json(prompt, system_prompt="你负责判断需要调用哪些工具来回答问题。")
    except Exception:
        logger.warning("Tool selector LLM call failed, defaulting to knowledge retrieval")
        result = {"tool_calls": [{"tool": "retrieve_knowledge", "args": {"query": query}}]}

    tool_calls = result.get("tool_calls", [])
    logger.info("Tool selector result: tool_calls=%s", tool_calls)

    # Inject doc_ids from previous turn's doc context when follow-up query
    # references a known document (e.g. "里边讲了什么内容" → "面试问题.md里边讲了什么内容")
    doc_context = state.metadata.get("doc_context", [])
    if doc_context and tool_calls:
        query_lower = query.lower()
        for tc in tool_calls:
            if tc["tool"] == "retrieve_knowledge":
                referenced = [d for d in doc_context if d.get("file_name", "").lower() in query_lower]
                if referenced:
                    doc_ids = [d["id"] for d in referenced if d.get("id")]
                    if doc_ids:
                        tc["args"]["doc_ids"] = doc_ids
                        logger.info("Injected doc_ids into retrieve_knowledge: %s", doc_ids)

    if not tool_calls:
        # LLM 认为不需要工具。用 embedding 语义匹配判断是否明显是闲聊。
        # 不是明显闲聊 → 可能是有文档查询意图 → 强制检索。
        query_emb = state.metadata.get("query_embedding")
        is_chat = False
        if query_emb is not None:
            try:
                from kb_biz.modules.chat.intent_classifier import is_chat_embedding

                is_chat = is_chat_embedding(query_emb)
            except Exception:
                is_chat = False
        if not is_chat:
            logger.info("Force retrieve_knowledge for query (embedding not chat): %s", query[:60])
            force_args = {"query": query}
            # 强制路径也注入跨轮 doc_context
            if doc_context:
                query_lower = query.lower()
                referenced = [d for d in doc_context if d.get("file_name", "").lower() in query_lower]
                if referenced:
                    ids = [d["id"] for d in referenced if d.get("id")]
                    if ids:
                        force_args["doc_ids"] = ids
                        logger.info("Injected doc_ids into force path: %s", ids)
            tool_calls = [{"tool": "retrieve_knowledge", "args": force_args}]
        else:
            return {"tool_calls": [], "tool_results": []}

    # 执行所有被调用的工具
    tool_results = []
    has_docs = False
    has_search = False
    current_query_doc_ids: list[str] = []  # doc IDs from this turn's query_documents
    user_tz = state.metadata.get("timezone", "+08:00")  # 从前端传入的时区
    for tc in tool_calls:
        tool_name = tc.get("tool", "")
        tool_args = tc.get("args", {})
        # 自动注入用户时区到 get_current_time 工具
        if tool_name == "get_current_time" and "timezone" not in tool_args:
            tool_args["timezone"] = user_tz
        try:
            res = await execute_tool(tool_name, tool_args, state.dept_ids, state.user_id)
            tool_results.append({"tool": tool_name, "args": tool_args, "result": res})
            logger.info("Tool %s called with args=%s, dept_ids=%s, result keys: %s", tool_name, tool_args, state.dept_ids, list(res.keys()))
            if tool_name == "retrieve_knowledge":
                has_search = True
                logger.info("retrieve_knowledge returned %d results", len(res.get("results", [])))
            elif tool_name == "query_documents":
                docs = res.get("documents", [])
                has_docs = len(docs) > 0
                if has_docs:
                    current_query_doc_ids = [d["id"] for d in docs if d.get("id")]
                logger.info("query_documents returned %d documents", len(docs))
        except Exception as e:
            logger.exception("Tool %s execution failed", tool_name)
            tool_results.append({"tool": tool_name, "args": tool_args, "result": {"error": str(e)}})

    # 兜底：LLM 只查了文档名但没检索内容时，补调 retrieve_knowledge
    if not has_search:
        _is_chat = False
        query_emb = state.metadata.get("query_embedding")
        if query_emb is not None:
            try:
                from kb_biz.modules.chat.intent_classifier import is_chat_embedding

                _is_chat = is_chat_embedding(query_emb)
            except Exception:
                _is_chat = False
        if has_docs or not _is_chat:
            logger.info("Fallback retrieve_knowledge (has_docs=%s is_chat=%s)", has_docs, _is_chat)
            fallback_args: dict[str, Any] = {"query": query}
            # 优先使用当前轮 query_documents 查到的 doc_ids（新对话第一轮）
            if current_query_doc_ids:
                fallback_args["doc_ids"] = current_query_doc_ids
                logger.info("Using current-turn doc_ids: %s", current_query_doc_ids)
            else:
                # 其次使用跨轮文档上下文（跟进轮次）
                doc_context = state.metadata.get("doc_context", [])
                if doc_context:
                    query_lower = query.lower()
                    referenced = [d for d in doc_context if d.get("file_name", "").lower() in query_lower]
                    if referenced:
                        doc_ids = [d["id"] for d in referenced if d.get("id")]
                        if doc_ids:
                            fallback_args["doc_ids"] = doc_ids
                            logger.info("Injected cross-turn doc_ids: %s", doc_ids)
            try:
                res = await execute_tool("retrieve_knowledge", fallback_args, state.dept_ids, state.user_id)
                tool_results.append({"tool": "retrieve_knowledge", "args": dict(fallback_args), "result": res})
                logger.info("Fallback retrieve_knowledge returned %d results", len(res.get("results", [])))
            except Exception as e:
                logger.exception("Fallback retrieve_knowledge failed")

    return {"tool_calls": tool_calls, "tool_results": tool_results}


async def memory_load(state: AgentState) -> dict[str, Any]:
    """记忆加载节点。

    加载当前会话的短期摘要（Redis）和用户长期记忆（PG）。
    """
    summary = await get_session_summary(state.session_id) or ""
    memories = await get_relevant_memories(state.user_id, top_k=3)
    return {
        "short_term_summary": summary,
        "long_term_memories": "\n".join(memories) if memories else "",
    }


async def retrieval(state: AgentState) -> dict[str, Any]:
    """知识检索节点（保留向后兼容，当前已由 tool_selector 替代）。"""
    query = state.metadata.get("query", "")
    if not query.strip():
        return {"search_results": []}
    try:
        results = await retrieval_service.hybrid_search(
            query=query,
            dept_ids=state.dept_ids,
            top_k=5,
        )
        return {"search_results": results}
    except Exception:
        logger.warning("Retrieval failed, continuing without search results")
        return {"search_results": []}


async def context_assembly(state: AgentState) -> dict[str, Any]:
    """上下文组装节点。

    组装最终 system prompt，包含：
    - 基础系统提示 + 深度思考指令（可选）
    - 工具执行结果（时间/文档查询等）
    - Guardrail 安全指令（仅当无工具结果时）
    - 短期摘要 + 长期记忆
    - 检索结果（带来源标注）
    """
    query = state.metadata.get("original_query") or state.metadata.get("query", "")
    parts = [SYSTEM_PROMPT_BASE]

    # 用户项目上下文

    # 深度思考模式：添加链式推理指令
    if state.metadata.get("deep_thinking"):
        parts.append("\n请逐步推理（chain-of-thought），先分析问题，再给出答案。")

    # 工具结果优先于 guardrail，有结果时跳过安全拒绝
    for tr in state.tool_results:
        if tr["tool"] == "get_current_time":
            local = tr["result"].get("local_time", "")
            if local:
                parts.append(f"\n当前日期时间（已转换为用户本地时间）：{local}")
        elif tr["tool"] == "query_documents":
            docs = tr["result"].get("documents", [])
            if docs:
                lines = [f"- {d.get('file_name','')} ({d.get('status','')}, 上传于{(d.get('created_at') or '')[:10]})" for d in docs]
                parts.append(f"\n文档查询结果（仅文档名，不包含具体内容）：\n" + "\n".join(lines))

    # 意图置信度低时提示 LLM 谨慎处理
    if state.metadata.get("low_confidence"):
        parts.append("\n注意：用户意图不确定，请结合检索结果判断。若检索结果与问题相关则基于结果回答；若不相关则如实告知用户未找到相关信息。")

    # Guardrail: 有工具结果时跳过，没有时根据标记给出提示
    has_tool_results = bool(state.tool_results)
    if state.guardrail_flags and not has_tool_results:
        flag_str = ", ".join(state.guardrail_flags)
        if "harmful" in flag_str:
            parts.append(f"\n[安全标记: harmful] 用户输入涉及安全风险，请礼貌拒绝。")
        elif "out_of_scope" in flag_str:
            parts.append(f"\n[安全标记: out_of_scope] 问题不在知识库范围内，可根据自己的知识回答，无需拒绝。")

    # Short-term summary
    if state.short_term_summary:
        parts.append(f"\n当前对话摘要：\n{state.short_term_summary}")

    # 长期记忆
    if state.long_term_memories:
        parts.append(f"\n用户相关记忆：\n{state.long_term_memories}")

    # 检索结果（带来源标注）
    if state.search_results:
        queried_ids = state.metadata.get("queried_doc_ids", [])
        context_parts = []
        for i, r in enumerate(state.search_results):
            label = f"[来源 {i + 1}]"
            if queried_ids and r.doc_id and r.doc_id not in queried_ids:
                label += " (来自其他文档，仅供参考)"
            context_parts.append(f"{label} {r.content}")
        context = "\n\n".join(context_parts)
        parts.append(f"\n知识库检索结果：\n{context}")
    else:
        parts.append("\n注意：当前没有检索到与问题相关的文档内容。请如实告知用户未找到，不要编造文档内容。")

    system_prompt = "\n\n".join(parts)
    return {"metadata": {**state.metadata, "system_prompt": system_prompt}}


async def llm_stream(
    state: AgentState, llm: LLMClient
) -> AsyncGenerator[dict, None]:
    """LLM 流式生成节点。

    使用组装好的 system prompt，流式生成 LLM 回答。
    yield {"type": "reasoning"|"content", "text": str}
    """
    system_prompt = state.metadata.get("system_prompt", SYSTEM_PROMPT_BASE)
    query = state.metadata.get("original_query") or state.metadata.get("query", "")
    async for event in llm.chat_stream_detailed(query, system_prompt=system_prompt):
        yield event
