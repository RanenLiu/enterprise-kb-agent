from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from redis.asyncio import Redis as AsyncRedis

from kb_biz.config.settings import settings

logger = logging.getLogger("kb_biz.chat.memory")
_MESSAGE_TTL = 1800


def _msg_key(session_id: str) -> str:
    return f"session:{session_id}:messages"


def _summary_key(session_id: str) -> str:
    return f"session:{session_id}:summary"


def _title_key(session_id: str) -> str:
    return f"session:{session_id}:title"


_redis: AsyncRedis | None = None


async def get_redis() -> AsyncRedis:
    global _redis
    if _redis is None:
        _redis = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def push_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    r = await get_redis()
    msg = json.dumps({"role": role, "content": content, "metadata": metadata})
    key = _msg_key(session_id)
    await r.rpush(key, msg)
    await r.expire(key, _MESSAGE_TTL)


async def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    r = await get_redis()
    key = _msg_key(session_id)
    exists = await r.exists(key)
    if not exists:
        return []
    raw = await r.lrange(key, 0, -1)
    return [json.loads(m) for m in raw]


async def set_session_summary(session_id: str, summary: str) -> None:
    r = await get_redis()
    await r.set(_summary_key(session_id), summary, ex=_MESSAGE_TTL)


async def get_session_summary(session_id: str) -> str | None:
    r = await get_redis()
    return await r.get(_summary_key(session_id))


async def set_session_title(session_id: str, title: str) -> None:
    r = await get_redis()
    await r.set(_title_key(session_id), title, ex=_MESSAGE_TTL)


async def get_session_title(session_id: str) -> str | None:
    r = await get_redis()
    return await r.get(_title_key(session_id))


# ── Retrieval cache (multi-round, for pronoun resolution) ──

_RETRIEVAL_CACHE_MAX_ROUNDS = 3
_RETRIEVAL_CACHE_TTL = 1800


def _retrieval_cache_key(session_id: str) -> str:
    return f"session:{session_id}:retrieval_cache"


async def push_retrieval_cache(
    session_id: str,
    query: str,
    query_embedding: list[float],
    chunks: list[dict],
    timestamp: float | None = None,
) -> None:
    """Push a retrieval round into the session's multi-round cache.

    Maintains at most _RETRIEVAL_CACHE_MAX_ROUNDS entries (LRU eviction).
    """
    import time

    r = await get_redis()
    key = _retrieval_cache_key(session_id)

    entry = {
        "query": query,
        "query_embedding": query_embedding,
        "chunks": chunks[:5],  # Keep top 5 chunks per round
        "timestamp": timestamp or time.time(),
    }

    # Get existing cache
    raw = await r.get(key)
    cache: list[dict] = json.loads(raw) if raw else []

    # Append new entry
    cache.append(entry)

    # Trim to max rounds (remove oldest if over limit)
    if len(cache) > _RETRIEVAL_CACHE_MAX_ROUNDS:
        cache = cache[-_RETRIEVAL_CACHE_MAX_ROUNDS:]

    await r.set(key, json.dumps(cache), ex=_RETRIEVAL_CACHE_TTL)


async def match_retrieval_cache(
    session_id: str,
    query_embedding: list[float],
    threshold_low: float = 0.6,
) -> dict | None:
    """Find the best matching cached retrieval round for a query embedding.

    Returns None if no match exceeds threshold_low.
    Returns the cached entry dict if a match is found.
    """
    import math

    r = await get_redis()
    key = _retrieval_cache_key(session_id)
    raw = await r.get(key)
    if not raw:
        return None

    cache: list[dict] = json.loads(raw)
    if not cache:
        return None

    best_score = 0.0
    best_entry = None

    for entry in cache:
        emb = entry.get("query_embedding")
        if not emb:
            continue
        # Cosine similarity
        dot = sum(a * b for a, b in zip(query_embedding, emb))
        norm_a = math.sqrt(sum(a * a for a in query_embedding))
        norm_b = math.sqrt(sum(b * b for b in emb))
        if norm_a == 0 or norm_b == 0:
            continue
        score = dot / (norm_a * norm_b)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score >= threshold_low and best_entry:
        best_entry["_match_score"] = best_score
        return best_entry

    return None


async def clear_retrieval_cache(session_id: str) -> None:
    """Clear the retrieval cache for a session (e.g., on conversation delete)."""
    r = await get_redis()
    key = _retrieval_cache_key(session_id)
    await r.delete(key)


async def save_long_term_memory(
    user_id: uuid.UUID,
    content: str,
    session_id: uuid.UUID,
) -> None:
    from kb_adapter_postgres.session import async_session_factory
    from kb_biz.models.long_term_memory import UserMemory
    from kb_core.indexing.service import embed_texts

    embedding = embed_texts([content])[0] if content.strip() else None
    memory = UserMemory(
        user_id=user_id,
        content=content,
        source_session_id=session_id,
        embedding=embedding,
    )
    async with async_session_factory() as db:
        db.add(memory)
        await db.commit()


async def get_relevant_memories(
    user_id: str,
    top_k: int = 3,
) -> list[str]:
    from kb_adapter_postgres.session import async_session_factory
    from kb_biz.models.long_term_memory import UserMemory
    from sqlalchemy import select

    async with async_session_factory() as db:
        stmt = (
            select(UserMemory.content)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.created_at.desc())
            .limit(top_k)
        )
        result = await db.execute(stmt)
        return [row[0] for row in result]
