from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

import jieba
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kb_core.rag.fulltext.base import SearchResult

logger = logging.getLogger("kb_core.rag.fulltext.pg")

_STOP_WORDS = frozenset({
    "的", "了", "是", "在", "有", "和", "与", "及", "或",
    "被", "把", "让", "给", "为", "所", "得", "地", "过",
    "吧", "呢", "啊", "呀", "哈", "嗯", "哦", "嘛",
    "这", "那", "哪", "你", "我", "他", "她", "它",
    "什么", "怎么", "如何", "怎样", "哪些", "哪里",
    "一个", "这个", "那个", "这些", "那些",
    "以及", "它们", "之间", "可以", "进行",
})


def _is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


def _extract_terms(query: str) -> list[str]:
    words = jieba.lcut(query)
    meaningful = [w for w in words if len(w) >= 2 and w not in _STOP_WORDS]
    meaningful.sort(key=len, reverse=True)
    terms: list[str] = []
    if meaningful:
        first_idx = next(i for i, w in enumerate(words) if len(w) >= 2 and w not in _STOP_WORDS)
        last_idx = next(
            i for i, w in reversed(list(enumerate(words)))
            if len(w) >= 2 and w not in _STOP_WORDS
        )
        phrase = "".join(words[first_idx : last_idx + 1])
        if phrase not in terms:
            terms.append(phrase)
        for w in meaningful:
            if w not in terms:
                terms.append(w)
    if not terms and len(query) > 4:
        terms.append(query[:10])
    elif not terms:
        terms.append(query[:6])
    return terms


def _dept_filter(dept_ids: list[str]) -> str:
    if not dept_ids:
        return "TRUE"
    placeholders = ", ".join(f"'{d}'" for d in dept_ids)
    return f"c.dept_id IN ({placeholders}) OR d.visibility = 'public'"


class PGSearch:
    def __init__(
        self,
        async_session_factory: Callable[[], AsyncSession],
    ):
        self._async_session_factory = async_session_factory

    async def search(
        self,
        query: str,
        dept_ids: list[str],
        top_k: int = 20,
        doc_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        if not query.strip():
            return []

        dept_cond = _dept_filter(dept_ids)
        if doc_ids:
            # Validate UUIDs to prevent SQL injection from untrusted Redis data
            valid_ids = [d for d in doc_ids if _is_valid_uuid(d)]
            id_list = ", ".join(f"'{d}'" for d in valid_ids)
            doc_cond = f"AND c.doc_id = ANY(ARRAY[{id_list}]::uuid[])" if valid_ids else ""
        else:
            doc_cond = ""

        async with self._async_session_factory() as session:
            # Primary: tsvector fulltext search
            sql = rf"""
                SELECT c.id, c.doc_id, c.dept_id, c.content, COALESCE(c.metadata->>'heading_path', '') AS heading_path,
                       COALESCE(c.metadata->>'page_range', '') AS page_range, d.visibility,
                       ts_rank(c.content_tsv, plainto_tsquery('simple', :query)) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.doc_id
                WHERE c.content_tsv @@ plainto_tsquery('simple', :query)
                  AND ({dept_cond})
                  {doc_cond}
                ORDER BY score DESC
                LIMIT :top_k
            """
            try:
                rows = await session.execute(
                    text(sql), {"query": query, "top_k": top_k},
                )
            except Exception:
                await session.rollback()
                rows = []
            results = []
            if rows:
                for row in rows:
                    results.append(SearchResult(
                        chunk_id=str(row.id),
                        doc_id=str(row.doc_id),
                        dept_id=str(row.dept_id),
                        content=row.content,
                        heading_path=row.heading_path or "",
                        page_range=row.page_range or "",
                        score=float(row.score),
                        visibility=row.visibility,
                        source="fulltext",
                    ))

            # ILIKE fallback for Chinese: use BM25 for scoring after retrieval
            if not results:
                terms = _extract_terms(query)
                term_conditions = " OR ".join(
                    f"c.content ILIKE :t{i}" for i in range(len(terms))
                )
                params = {f"t{i}": f"%{t}%" for i, t in enumerate(terms)}
                params["top_k"] = top_k * 2
                sql2 = rf"""
                    SELECT c.id, c.doc_id, c.dept_id, c.content, COALESCE(c.metadata->>'heading_path', '') AS heading_path,
                           COALESCE(c.metadata->>'page_range', '') AS page_range, d.visibility
                    FROM chunks c
                    JOIN documents d ON d.id = c.doc_id
                    WHERE ({term_conditions})
                      AND ({dept_cond})
                      {doc_cond}
                    LIMIT :top_k
                """
                try:
                    rows2 = await session.execute(text(sql2), params)
                except Exception:
                    await session.rollback()
                    rows2 = []
                seen = set()
                for row in rows2:
                    if row.id not in seen:
                        seen.add(row.id)
                        results.append(SearchResult(
                            chunk_id=str(row.id),
                            doc_id=str(row.doc_id),
                            dept_id=str(row.dept_id),
                            content=row.content,
                            heading_path=row.heading_path or "",
                            page_range=row.page_range or "",
                            score=0.5,  # BM25 rescore at service.py level
                            source="fulltext",
                        ))

            return results
