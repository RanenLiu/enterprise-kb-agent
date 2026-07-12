"""Post-processing: persist conversation data after LLM generation."""

from __future__ import annotations

import logging
import uuid

from kb_biz.modules.chat.memory import push_message, set_session_summary
from kb_biz.modules.chat.state import AgentState
from kb_core.llm.client import LLMClient

logger = logging.getLogger("kb_biz.chat.post_process")

MAX_TOKENS = 4096  # Context token upper bound (determined by LLM config)
SUMMARY_THRESHOLD = 0.75  # Trigger summary when 75% of MAX_TOKENS is reached


async def post_process(state: AgentState, llm: LLMClient) -> None:
    """Persist conversation data after LLM generation.

    Writes user/assistant messages to Redis and PostgreSQL,
    checks if a conversation summary is needed, and writes
    an audit log to PostgreSQL.

    Args:
        state: Final agent state after generation.
        llm: LLMClient instance (used for summary generation).
    """
    await _do_post_process(state, llm)


async def _do_post_process(state: AgentState, llm: LLMClient) -> None:
    """Actual post-processing logic.

    NOTE: This function must NOT be decorated with @retry from tenacity.
    Errors are caught, logged, and not propagated (non-critical path).
    """
    try:
        from kb_biz.modules.chat.memory import get_redis

        r = await get_redis()

        # Use original query (not rewritten) for persistence
        query = state.metadata.get("original_query") or state.metadata.get("query", "")
        response = state.metadata.get("response", "")

        # 1. Write user message to Redis
        await push_message(state.session_id, "user", query)

        # 2. Write assistant response to Redis
        await push_message(state.session_id, "assistant", response)

        # 2.5. Persist messages to PostgreSQL and update session counters
        await _persist_messages_to_pg(state, query, response)

        # 2.7. Extract and save long-term memory
        await _extract_long_term_memory(state, query, response, llm)

        # 3. Check if summary generation is needed (token threshold exceeded)
        # Simple heuristic: estimate ~200 tokens per message for Chinese
        msg_key = f"session:{state.session_id}:messages"
        msg_count = await r.llen(msg_key) if await r.exists(msg_key) else 0
        estimated_tokens = msg_count * 200
        if estimated_tokens > MAX_TOKENS * SUMMARY_THRESHOLD:
            summary = await _generate_conversation_summary(state.session_id, llm)
            if summary:
                await set_session_summary(state.session_id, summary)
                # Trim message list to last 10 messages
                await r.ltrim(msg_key, -10, -1)

        # 4. Write ConversationLog audit record
        await _write_audit_log(state, query, response, llm)

    except Exception:
        logger.exception("Post-process failed")


async def _persist_messages_to_pg(
    state: AgentState, query: str, response: str
) -> int:
    """Persist user/assistant messages to PostgreSQL and update session counters.

    Args:
        state: Agent state after generation.
        query: Original user query.
        response: Full generated response.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import text

    from kb_adapter_postgres.session import async_session_factory
    from kb_biz.models.conversation import ConversationMessage

    now = datetime.now(timezone.utc)

    # Build assistant message metadata from search results
    assistant_metadata: dict = {}
    chunks = state.metadata.get("search_chunks")
    if chunks:
        assistant_metadata["search_chunks"] = chunks
    graph_entities = state.metadata.get("graph_entities")
    graph_relations = state.metadata.get("graph_relations")
    if graph_entities and graph_relations:
        assistant_metadata["graph_entities"] = graph_entities
        assistant_metadata["graph_relations"] = graph_relations

    async with async_session_factory() as db:
        user_msg = ConversationMessage(
            session_id=state.session_id,
            role="user",
            content=query,
            created_at=now,
        )
        db.add(user_msg)
        assistant_msg = ConversationMessage(
            session_id=state.session_id,
            role="assistant",
            content=response,
            created_at=now + timedelta(milliseconds=1),
            metadata_=assistant_metadata or None,
        )
        db.add(assistant_msg)
        await db.execute(
            text(
                "UPDATE conversation_sessions "
                "SET message_count = message_count + 2, last_message_at = :now "
                "WHERE id = :sid"
            ),
            {"now": datetime.now(timezone.utc), "sid": state.session_id},
        )
        result = await db.execute(
            text("SELECT message_count FROM conversation_sessions WHERE id = :sid"),
            {"sid": state.session_id},
        )
        row = result.fetchone()
        await db.commit()
        return row[0] if row else 0


async def _generate_conversation_summary(
    session_id: str, llm: LLMClient
) -> str | None:
    """Generate a Chinese summary of the conversation history.

    Args:
        session_id: The session to summarize.
        llm: LLMClient instance for chat completion.

    Returns:
        A summary string, or None if no messages are available.
    """
    from kb_biz.modules.chat.memory import get_session_messages

    msgs = await get_session_messages(session_id)
    if not msgs:
        return None

    history = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
    prompt = (
        "请用中文总结以下对话的核心内容，包括：\n"
        "1. 用户提出的主要问题和需求\n"
        "2. 已经给出的回答和结论\n"
        "3. 任何重要的用户偏好或上下文信息\n\n"
        f"对话历史：\n{history}\n\n摘要："
    )
    return await llm.chat(prompt, system_prompt="你擅长简洁准确地总结对话。")


async def _extract_long_term_memory(
    state: AgentState, query: str, response: str, llm: LLMClient
) -> None:
    """用 LLM 判断本轮是否有值得长期记忆的信息，有则存储。

    LLM 输出 JSON 格式决定是否记住及记忆内容。
    """
    try:
        from kb_biz.modules.chat.memory import save_long_term_memory

        result = await llm.chat_json(
            prompt=(
                f"用户问题：{query}\n\n"
                f"助手回答：{response}\n\n"
                "判断以上对话中是否有值得长期记住的信息（用户偏好、关注话题、个人背景等）。"
                "输出 JSON：{\"should_remember\": bool, \"fact\": \"20字内的一句话事实\"}\n"
                "普通问答或闲聊 should_remember 为 false。"
            ),
            system_prompt="你负责判断哪些信息值得长期记住。",
        )
        if result.get("should_remember"):
            fact = result.get("fact", "").strip()
            if fact and len(fact) > 2:
                await save_long_term_memory(
                    user_id=state.user_id,
                    content=fact,
                    session_id=state.session_id,
                )
                logger.info("Saved long-term memory: %s", fact)
    except Exception:
        logger.exception("Long-term memory extraction failed")


async def _write_audit_log(
    state: AgentState, query: str, response: str, llm: LLMClient
) -> None:
    """Write a ConversationLog record for audit trail.

    Args:
        state: Agent state after generation.
        query: Original user query.
        response: Full generated response.
        llm: LLMClient instance (not used directly, kept for interface consistency).
    """
    from datetime import datetime, timezone

    from kb_adapter_postgres.session import async_session_factory
    try:
        from kb_enterprise.models.log import ConversationLog
    except ImportError:
        logger.debug("ConversationLog not available (kb-enterprise not installed), skipping audit log")
        return

    user_id_uuid = uuid.UUID(state.user_id) if state.user_id else None
    dept_id_uuid = uuid.UUID(state.dept_ids[0]) if state.dept_ids else None

    async with async_session_factory() as db:
        log = ConversationLog(
            session_id=state.session_id,
            user_id=user_id_uuid,
            dept_id=dept_id_uuid,
            query_text=query,
            response_text=response,
            intent=state.intent,
            retrieval_mode="hybrid" if state.search_results else "none",
            retrieved_chunks=(
                {
                    "count": len(state.search_results),
                    "sources": [r.doc_id for r in state.search_results],
                }
                if state.search_results
                else None
            ),
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.commit()
