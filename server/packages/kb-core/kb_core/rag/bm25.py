"""Pure Python BM25 scorer — no external dependencies.

Uses jieba for Chinese tokenization. Designed for post-retrieval reranking
of ILIKE results when the Cross-Encoder reranker is unavailable.

BM25 formula (Okapi):
    score(q, d) = Σ IDF(qᵢ) × TF(qᵢ, d) × (k₁ + 1) / (TF(qᵢ, d) + k₁ × (1 - b + b × |d| / avgdl))
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Any

logger = logging.getLogger("kb_core.rag.bm25")

_WORD_CACHE: dict[str, list[str]] = {}


def _tokenize(text: str) -> list[str]:
    """Tokenize Chinese text, return meaningful words (len >= 2, not stop words)."""
    if text in _WORD_CACHE:
        return _WORD_CACHE[text]
    try:
        from kb_core.rag.fulltext.pg import _STOP_WORDS
    except ImportError:
        _STOP_WORDS = frozenset()
    try:
        import jieba
        words = [w for w in jieba.lcut(text) if len(w) >= 2 and w not in _STOP_WORDS]
    except Exception:
        words = [text[i:i+2] for i in range(len(text) - 1) if text[i:i+2].strip()]
    _WORD_CACHE[text] = words
    return words


def bm25_scores(
    query: str,
    documents: list[dict[str, Any]],
    content_key: str = "content",
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """Compute BM25 scores for each document against the query.

    Args:
        query: The user's query text.
        documents: List of dicts, each containing the document text.
        content_key: The dict key for document text (default "content").
        k1: BM25 term frequency saturation parameter.
        b: BM25 length normalization parameter.

    Returns:
        List of BM25 scores, aligned 1:1 with the input documents list.
        Higher = more relevant.
    """
    if not query or not documents:
        return [0.0] * len(documents)

    query_tokens = _tokenize(query)
    if not query_tokens:
        return [0.0] * len(documents)

    doc_tokens_list = [_tokenize(d.get(content_key, "") or "") for d in documents]
    N = len(doc_tokens_list)
    if N == 0:
        return [0.0] * len(documents)
    avgdl = sum(len(t) for t in doc_tokens_list) / N
    if avgdl == 0:
        return [0.0] * len(documents)

    # IDF per query term
    doc_term_sets = [set(t) for t in doc_tokens_list]
    idf: dict[str, float] = {}
    for qt in set(query_tokens):
        n = sum(1 for s in doc_term_sets if qt in s)
        idf[qt] = math.log((N - n + 0.5) / (n + 0.5) + 1.0)

    # Score each document
    scores: list[float] = []
    for doc_tokens in doc_tokens_list:
        doc_len = len(doc_tokens)
        tf_counter = Counter(doc_tokens)
        score = 0.0
        for qt in query_tokens:
            tf = tf_counter.get(qt, 0)
            if tf == 0:
                continue
            score += idf.get(qt, 0.0) * (
                tf * (k1 + 1.0) / (tf + k1 * (1.0 - b + b * doc_len / avgdl))
            )
        scores.append(score)

    logger.debug(
        "BM25 scored %d docs (avgdl=%.1f, terms=%s)",
        N, avgdl, query_tokens,
    )
    return scores
