"""LangGraph Agent graph: build, route, and run the Q&A pipeline."""

from __future__ import annotations

import logging
import re as _re
import time
import uuid
from typing import Any, AsyncGenerator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from kb_biz.modules.chat.guardrail import should_skip_retrieval
from kb_biz.modules.chat.memory import get_redis, match_retrieval_cache, push_retrieval_cache
from kb_core.rag.fulltext.base import SearchResult
from kb_biz.modules.chat.nodes import (
    context_assembly,
    intent_recognition,
    llm_stream,
    memory_load,
    question_rewriting,
    retrieval,
    tool_selector,
)

from kb_biz.modules.chat.post_process import post_process
from kb_biz.modules.chat.state import AgentState
from kb_core.llm.client import LLMClient

logger = logging.getLogger("kb_biz.chat.graph")


def route_after_guardrail(state: AgentState) -> str:
    """Conditional route: skip retrieval based on intent."""
    if should_skip_retrieval(state.intent):
        return "skip_retrieval"
    return "do_retrieval"


def build_graph() -> StateGraph:
    """Build and compile a LangGraph StateGraph for the Q&A pipeline.

    Registers all pipeline nodes (intent_recognition, retrieval, memory_load,
    context_assembly) and compiles with MemorySaver checkpointing.
    Reserved for future use when LangGraph's built-in execution
    (astream_events) is preferred. Currently, run_agent() uses
    explicit orchestration to insert SSE events between nodes.

    Returns:
        A compiled StateGraph instance.
    """
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("intent_recognition", intent_recognition)
    builder.add_node("retrieval", retrieval)
    builder.add_node("memory_load", memory_load)
    builder.add_node("context_assembly", context_assembly)

    # Add edges: START -> intent -> (conditional) retrieval -> memory -> context -> END
    builder.add_edge(START, "intent_recognition")
    builder.add_conditional_edges(
        "intent_recognition",
        route_after_guardrail,
        {"do_retrieval": "retrieval", "skip_retrieval": "memory_load"},
    )
    builder.add_edge("retrieval", "memory_load")
    builder.add_edge("memory_load", "context_assembly")
    builder.add_edge("context_assembly", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph


async def run_agent(
    session_id: str,
    user_id: str,
    dept_ids: list[str],
    query: str,
    llm: LLMClient,
    deep_thinking: bool = False,
    timezone: str = "+08:00",
) -> AsyncGenerator[dict[str, Any], None]:
    """Run the full Q&A agent pipeline, yielding SSE event dicts.

    Orchestrates: intent recognition -> (conditional) retrieval ->
    memory load -> context assembly -> LLM streaming -> post-process.

    Args:
        session_id: Current conversation session ID.
        user_id: Authenticated user ID.
        dept_ids: Department IDs the user has access to.
        query: User's question text.
        llm: LLMClient instance for intent classification and generation.
        deep_thinking: Enable chain-of-thought reasoning in the system prompt.

    Yields:
        Dicts representing SSE events: {"event": str, "data": dict}.
    """
    state = AgentState(
        session_id=session_id,
        user_id=user_id,
        dept_ids=dept_ids,
        metadata={"query": query, "deep_thinking": deep_thinking, "timezone": timezone},
    )

    # Load previous turn's document context from Redis
    try:
        r = await get_redis()
        raw_doc_ctx = await r.get(f"session:{session_id}:doc_context")
        if raw_doc_ctx:
            import json as _json
            parsed = _json.loads(raw_doc_ctx)
            if parsed:
                state.metadata["doc_context"] = parsed
                logger.info("Loaded doc context for session %s: %d docs", session_id, len(parsed))
    except Exception:
        logger.warning("Failed to load doc context from Redis")

    # Step 1: Intent recognition
    intent_result = await intent_recognition(state, llm)
    intent_reasoning = intent_result.get("metadata", {}).get("intent_reasoning", "")
    logger.info("Intent: %s | reasoning: %s", intent_result["intent"], intent_reasoning)
    yield {
        "event": "intent",
        "data": {
            "intent": intent_result["intent"],
            "reasoning": intent_reasoning,
        },
    }

    # Merge intent result into state
    state_data = state.model_dump()
    state_data.update(intent_result)
    state = AgentState(**state_data)

    # Confidence threshold: if intent confidence < 0.7, ask user for clarification instead of guessing.
    intent_confidence = state.metadata.get("intent_confidence", 1.0)
    if intent_confidence < 0.7:
        logger.info("Low intent confidence (%.2f), asking clarification", intent_confidence)
        clarify_prompt = (
            f"用户问题：{query}\n\n"
            f"意图识别结果：{intent_result['intent']}（{intent_reasoning}）\n"
            "置信度较低，不确定用户意图。请用一句话追问用户确认："
            "ta是想查询知识库中的相关文档内容，还是想了解一般性的知识？"
            "直接输出追问，不要解释。"
        )
        clarify_response = ""
        async for event in llm.chat_stream_detailed(clarify_prompt, system_prompt="你是一个友好的确认助手。"):
            if event["type"] == "content":
                clarify_response += event["text"]
                yield {"event": "token", "data": {"text": event["text"]}}
        yield {"event": "done", "data": {"message_id": str(uuid.uuid4()), "session_id": session_id, "usage": {}}}
        # Save the clarification to session history so user's reply has context
        state.metadata["response"] = clarify_response
        await post_process(state, llm)
        return  # skip rest of pipeline

    # Step 2: Question rewriting (pronoun resolution)
    rewrite_result = await question_rewriting(state, llm)
    state_data = state.model_dump()
    state_data.update(rewrite_result)
    state = AgentState(**state_data)

    # Step 2.5: Check retrieval cache for pronoun resolution
    cache_hit = None
    try:
        _t0 = time.time()
        from kb_core.indexing.service import embed_texts

        q = state.metadata.get("query", "")
        original_q = state.metadata.get("original_query", "")
        was_rewritten = bool(original_q) and original_q != q

        if q:
            emb = embed_texts([q])[0]
            logger.info("Embedding computed in %.1fs", time.time() - _t0)
            state.metadata["query_embedding"] = emb.tolist() if hasattr(emb, 'tolist') else emb
            cache_entry = await match_retrieval_cache(
                session_id,
                state.metadata["query_embedding"],
            )
            if cache_entry:
                cache_hit = cache_entry
                state.metadata["cache_chunks"] = cache_entry["chunks"]
                logger.info("Retrieval cache hit: score=%.3f query=%s", cache_entry.get("_match_score", 0), q[:50])

        # When pronouns were resolved (query was rewritten), also try the
        # original query against cache. If still no match, fall back to
        # injecting the most recent cache entry anyway — the user is clearly
        # referring to the previous turn's topic.
        if not cache_hit and was_rewritten:
            fallback_cache = await match_retrieval_cache(
                session_id,
                state.metadata["query_embedding"],
                threshold_low=0.3,  # very permissive for follow-ups
            )
            if not fallback_cache:
                # Get the most recent entry directly
                r_cache = await get_redis()
                raw = await r_cache.get(f"session:{session_id}:retrieval_cache")
                if raw:
                    import json
                    all_entries = json.loads(raw)
                    if all_entries:
                        fallback_cache = all_entries[-1]
            if fallback_cache:
                cache_hit = fallback_cache
                state.metadata["cache_chunks"] = fallback_cache["chunks"]
                logger.info("Retrieval cache fallback hit (pronoun follow-up)")
    except Exception:
        logger.debug("Retrieval cache check failed")

    # Step 3: Tool selection (skip retrieval for chitchat etc.)
    query_text = state.metadata.get("query", "")
    skip_intent = should_skip_retrieval(state.intent)
    # 置信度低时越过意图拦截，强制检索（避免"模型微调方式有哪些"被误判为闲聊）
    if state.metadata.get("low_confidence"):
        skip_intent = False
        logger.info("Low confidence override: forcing retrieval")
    # general_chat 意图下，用 embedding 语义匹配判断是否真的是闲聊。
    # 如果 embedding 接近已知闲聊查询的质心 → 确实闲聊，跳过检索。
    # 如果 embedding 远离质心 → 可能是 LLM 误分类（实际是知识查询），走 tool_selector 二次确认。
    is_general_chat = state.intent == "general_chat"
    if is_general_chat:
        query_emb = state.metadata.get("query_embedding")
        if query_emb is not None:
            try:
                from kb_biz.modules.chat.intent_classifier import is_chat_embedding

                has_content = not is_chat_embedding(query_emb)
            except Exception:
                has_content = True
        else:
            has_content = True  # 无 embedding，安全起见走 tool_selector
    else:
        has_content = True
    logger.info("Tool selection: intent=%s skip=%s general_chat=%s has_content=%s query=%s", state.intent, skip_intent, is_general_chat, has_content, query_text[:50])
    if skip_intent and not (is_general_chat and has_content):
        tool_result = {"tool_results": []}
    else:
        tool_result = await tool_selector(state, llm)
    state_data = state.model_dump()
    state_data.update(tool_result)
    state = AgentState(**state_data)

    # Step 4: Extract retrieval results from tool outputs for downstream nodes
    search_results_list: list[SearchResult] = []
    # Collect query_documents doc_ids first (for source filtering in the retrieval event)
    queried_doc_ids: set[str] = set()
    for tr in state.tool_results:
        if tr["tool"] == "query_documents":
            docs = tr["result"].get("documents", [])
            state.metadata["document_query_results"] = docs
            queried_doc_ids = {d["id"] for d in docs if d.get("id")}
    state.metadata["queried_doc_ids"] = list(queried_doc_ids)
    # Apply MMR to selection: pick diverse, relevant chunks for source display.
    # File-ref queries skip MMR (they use exact doc_id matching below).
    q = state.metadata.get("query", "")
    oq = state.metadata.get("original_query", "") or q
    has_file_ref = any(ext in q or ext in oq for ext in [".xlsx", ".docx", ".pptx", ".md", ".txt", ".pdf", ".xls", ".ppt"])
    for tr in state.tool_results:
        if tr["tool"] == "retrieve_knowledge":
            raw = tr["result"].get("results", [])
            if raw and not has_file_ref:
                # Source dedup: keep only the top document's chunks (by total BM25 score)
                raw.sort(key=lambda r: r.get("score", 0), reverse=True)
                # Pick the doc with the highest total BM25 score across all its chunks
                # (not just the single highest-scoring chunk, which can be an outlier)
                doc_totals: dict[str, float] = {}
                for r in raw:
                    did = r.get("doc_id", "")
                    if did:
                        doc_totals[did] = doc_totals.get(did, 0.0) + r.get("score", 0)
                if not doc_totals:
                        continue  # no valid doc_ids, skip filter
                top_doc = max(doc_totals, key=doc_totals.get)
                tr["result"]["results"] = [r for r in raw if r.get("doc_id", "") == top_doc]
    # Filter chunks: only show sources matching the file the user explicitly asked about.
    if has_file_ref:
        # When LLM called retrieve_knowledge without query_documents, try to infer
        # the target doc_id from heading_path of retrieved chunks.
        if not queried_doc_ids:
            lower_q = q.lower()
            for tr in state.tool_results:
                if tr["tool"] == "retrieve_knowledge":
                    for r in tr["result"].get("results", []):
                        heading = (r.get("heading_path") or "").lower()
                        if heading and heading.split(" > ")[0] in lower_q:
                            queried_doc_ids.add(r.get("doc_id", ""))
            state.metadata["queried_doc_ids"] = list(queried_doc_ids)
        if not queried_doc_ids:
            # User asked about a specific file by name+extension, but no queried doc IDs
            # could be determined. Suppress ALL chunks to avoid source pollution.
            logger.info("Source filter: file query without matching doc, suppressing all chunks")
            for tr in state.tool_results:
                if tr["tool"] == "retrieve_knowledge":
                    tr["result"]["results"] = []
            # Skip the rest of the filter logic (queried_doc_ids is empty)
            # but let the rest of the pipeline (graph, cache, etc.) continue.
        if len(queried_doc_ids) > 1:
            # query_documents with jieba is too fuzzy; narrow to the best match.
            doc_results = state.metadata.get("document_query_results", [])
            q_lower = q.lower()
            best_ids = set()
            for d in doc_results:
                fname = (d.get("file_name") or "").lower()
                base = fname.rsplit(".", 1)[0] if "." in fname else fname
                if base in q_lower:
                    best_ids.add(d.get("id", ""))
            if best_ids:
                queried_doc_ids = best_ids
                state.metadata["queried_doc_ids"] = list(queried_doc_ids)
                logger.info("Source filter narrowed: %d → %d docs", len(doc_results), len(best_ids))
        if queried_doc_ids:
            for tr in state.tool_results:
                if tr["tool"] == "retrieve_knowledge":
                    raw = tr["result"].get("results", [])
                    filtered = [r for r in raw if r.get("doc_id", "") in queried_doc_ids]
                    tr["result"]["results"] = filtered
                    logger.info("Source filter: %d raw → %d filtered", len(raw), len(filtered))
    for tr in state.tool_results:
        if tr["tool"] == "retrieve_knowledge":
            for r in tr["result"].get("results", []):
                search_results_list.append(SearchResult(**r))
            # Emit retrieval SSE event (only for knowledge_query, otherwise suppress sources)
            raw_chunks = tr["result"].get("results", [])
            show_sources = state.intent == "knowledge_query"
            # Filter chunks by score threshold for knowledge_query
            display_chunks = [
                {
                    "doc_id": r.get("doc_id", ""),
                    "content": r.get("content", "")[:200],
                    "heading_path": r.get("heading_path", ""),
                    "page_range": r.get("page_range", ""),
                    "score": r.get("score", 0),
                    "source": r.get("source", ""),
                }
                for r in raw_chunks
            ] if show_sources else []
            yield {
                "event": "retrieval",
                "data": {
                    "chunks": display_chunks,
                    "queried_doc_ids": list(queried_doc_ids),
                },
            }
            # Store to metadata for persistence
            if raw_chunks:
                state.metadata["search_chunks"] = [
                    {
                        "doc_id": r.get("doc_id", ""),
                        "content": r.get("content", "")[:200],
                        "heading_path": r.get("heading_path", ""),
                        "page_range": r.get("page_range", ""),
                        "score": r.get("score", 0),
                        "source": r.get("source", ""),
                    }
                    for r in raw_chunks
                ]
        elif tr["tool"] == "query_documents":
            pass  # handled in the collect pass above

    state.search_results = search_results_list

    # Store retrieval results in cache for pronoun resolution
    if search_results_list:
        try:
            q = state.metadata.get("query", "")
            if q:
                # Reuse the cached embedding if available (computed in step 2.5)
                emb = state.metadata.get("query_embedding")
                if emb is None:
                    from kb_core.indexing.service import embed_texts
                    emb = embed_texts([q])[0]
                    emb = emb.tolist() if hasattr(emb, 'tolist') else emb
                cache_chunks = [
                    {
                        "doc_id": r.doc_id,
                        "chunk_id": r.chunk_id,
                        "dept_id": r.dept_id,
                        "content": r.content[:500],
                        "score": r.score,
                        "source": r.source or "",
                    }
                    for r in search_results_list[:5]
                ]
                await push_retrieval_cache(session_id, q, emb, cache_chunks)
        except Exception:
            logger.debug("Retrieval cache write skipped")

    # Save document context (from query_documents) to Redis for next turn
    doc_query_results = state.metadata.get("document_query_results", [])
    if doc_query_results:
        try:
            r = await get_redis()
            import json as _json
            await r.set(f"session:{session_id}:doc_context", _json.dumps(doc_query_results), ex=3600)
            logger.info("Saved doc context for session %s: %d docs", session_id, len(doc_query_results))
        except Exception:
            logger.debug("Doc context save skipped")

    # Extract graph entity relations from search results (no extra LLM call)
    graph_relations: list[dict] = []
    graph_entities: list[str] = []
    # Neo4j graph extraction is in kb-enterprise (Phase 2)
    matched_doc_ids = list({r.doc_id for r in search_results_list})
    if matched_doc_ids:
        try:
            try:
                from app.modules.rag.indexing import _get_neo4j_driver
            except ImportError:
                logger.debug("Neo4j driver not available (Phase 2: kb-enterprise)")
                _get_neo4j_driver = None

            driver = None
            if _get_neo4j_driver:
                driver = _get_neo4j_driver()
            if driver:
                with driver.session() as ns:
                    # All entities
                    ents = ns.run(
                        "MATCH (e:Entity) WHERE e.doc_id IN $doc_ids RETURN DISTINCT e.name AS name",
                        doc_ids=matched_doc_ids,
                    )
                    graph_entities = [r["name"] for r in ents if r["name"]]

                    if graph_entities:
                        rels = ns.run(
                            """
                            MATCH (e:Entity)-[r]-(related:Entity)
                            WHERE e.doc_id IN $doc_ids AND related.doc_id IN $doc_ids
                            RETURN DISTINCT e.name AS source, type(r) AS relation, related.name AS target
                            """,
                            doc_ids=matched_doc_ids,
                        )
                        seen = set()
                        graph_relations = []
                        for r in rels:
                            s, t = r["source"], r["target"]
                            key = tuple(sorted([s, t])) + (r["relation"],)
                            if key not in seen:
                                seen.add(key)
                                graph_relations.append({"source": s, "relation": r["relation"], "target": t})

            if graph_relations:
                yield {"event": "graph", "data": {"entities": graph_entities, "relations": graph_relations}}
                state.metadata["graph_entities"] = graph_entities
                state.metadata["graph_relations"] = graph_relations
        except Exception:
            logger.warning("Graph relation fetch failed")

    # Inject cached retrieval chunks (for pronoun resolution)
    if cache_hit and cache_hit.get("chunks"):
        for cc in cache_hit["chunks"]:
            state.search_results.insert(0, SearchResult(
                doc_id=cc.get("doc_id", ""),
                chunk_id=cc.get("chunk_id", ""),
                dept_id=cc.get("dept_id", ""),
                content=cc.get("content", ""),
                heading_path=cc.get("heading_path", ""),
                page_range=cc.get("page_range", ""),
                score=cc.get("score", 0.5),
                source=cc.get("source", ""),
            ))
        logger.info("Injected %d cached chunks for pronoun resolution", len(cache_hit["chunks"]))

    # Step 5: Memory load (summary + long-term)
    memory_result = await memory_load(state)
    state_data = state.model_dump()
    state_data.update(memory_result)
    state = AgentState(**state_data)

    # Step 5: Context assembly
    context_result = await context_assembly(state)
    state_data = state.model_dump()
    state_data.update(context_result)
    state = AgentState(**state_data)

    # Step 7: LLM streaming generation
    collected_response = ""
    deep = state.metadata.get("deep_thinking", False)
    # Strict mode: knowledge_query 无有效检索结果时不依赖 LLM 自有知识
    max_score = max((r.score for r in state.search_results), default=0) if state.search_results else 0
    if state.intent in ("knowledge_query", "out_of_scope") and max_score < 0.2:
        no_result_msg = "知识库中未找到相关信息。"
        collected_response = no_result_msg
        yield {"event": "token", "data": {"text": no_result_msg}}
        state.search_results = []  # 清空低分结果，前端不会显示来源
    else:
        async for event in llm_stream(state, llm):
            if event["type"] == "reasoning":
                if deep:
                    yield {"event": "thinking", "data": {"text": event["text"]}}
            elif event["type"] == "content":
                collected_response += event["text"]
                yield {"event": "token", "data": {"text": event["text"]}}

    # Log total time
    logger.info("Chat response generated in %.1fs", time.time() - _t0)

    # Classify chunks: cited vs related
    cited_ids: set[str] = set()
    chunks_meta = state.metadata.get("search_chunks", [])
    if chunks_meta and collected_response:
        resp_lower = collected_response.lower()
        for c in chunks_meta:
            c_text = c.get("content", "").lower()
            # Strip [filename] prefix and normalize spaces
            c_clean = _re.sub(r"^\[.*?\]\s*", "", c_text)
            c_clean = _re.sub(r"\s+", " ", c_clean).strip()
            # Keyword overlap matching: extract significant terms from chunk
            # (CJK words >= 2 chars, English words >= 3 chars)
            keywords = set(_re.findall(r"[一-鿿]{2,}|[a-z]{3,}", c_clean))
            if not keywords:
                if len(c_clean) > 10 and c_clean[:min(60, len(c_clean))] in resp_lower:
                    cited_ids.add(c.get("doc_id", ""))
            else:
                hits = sum(1 for kw in keywords if kw in resp_lower)
                if hits >= max(2, len(keywords) * 0.6):
                    cited_ids.add(c.get("doc_id", ""))
    if chunks_meta:
        cited = [c for c in chunks_meta if c.get("doc_id", "") in cited_ids]
        related = [c for c in chunks_meta if c.get("doc_id", "") not in cited_ids]
        yield {"event": "citations", "data": {"cited": cited, "related": related}}

    # Step 8: Generate session title on first message (write to PG before done event)
    r = await get_redis()
    title_key = f"session:{session_id}:title"
    if not await r.exists(title_key):
        from sqlalchemy import text
        from kb_adapter_postgres.session import async_session_factory

        async with async_session_factory() as db:
            row = (await db.execute(
                text("SELECT title FROM conversation_sessions WHERE id = :sid"),
                {"sid": session_id},
            )).fetchone()
            pg_title = row[0] if row else None
            if pg_title and pg_title != "New conversation":
                await r.set(title_key, pg_title, ex=3600)
            else:
                # No title yet → generate via LLM
                q = state.metadata.get("query", "")
                if q:
                    try:
                        title = (await llm.chat(
                            prompt=f"请用中文短语总结该问题的主题，不超过10个字，不要用问句句式：\n\n{q}",
                            system_prompt="你是一个简洁的标题生成器。始终输出中文短语，不要用问句。只输出标题，不要解释。",
                        )).strip().strip('"').strip("'").strip("'").strip("'")[:50]
                        if title:
                            await r.set(title_key, title, ex=3600)
                            async with async_session_factory() as db2:
                                await db2.execute(
                                    text("UPDATE conversation_sessions SET title = :title WHERE id = :sid"),
                                    {"title": title, "sid": session_id},
                                )
                                await db2.commit()
                    except Exception:
                        logger.exception("Session title generation failed")

    # Step 9: Emit completion event
    yield {
        "event": "done",
        "data": {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        },
    }

    # Step 10: Post-processing (persist/summary/title/memory/audit)
    state.metadata["response"] = collected_response
    await post_process(state, llm)
