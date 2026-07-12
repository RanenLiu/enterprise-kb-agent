"""MMR (Maximal Marginal Relevance) for RAG source diversity selection.

Usage:
    selected = mmr_select(chunks, query, lambda_param=0.7)

MMR selects chunks that are both relevant to the query AND diverse from each other.
This avoids showing multiple nearly-identical chunks while surfacing different angles.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("kb_core.rag.mmr")

# ── lightweight Chinese text tokenizer (jieba-based, no ML model needed) ──

_CHINESE_PUNCTUATION = frozenset("，。、；：？！""''（）【】《》——……··,\\.;:!?\"'()[]{}")

_WORD_CACHE: dict[str, list[str]] = {}


def _tokenize(text: str) -> list[str]:
    """Tokenize Chinese text into words using jieba."""
    if text in _WORD_CACHE:
        return _WORD_CACHE[text]
    try:
        import jieba
        words = [w for w in jieba.lcut(text) if len(w) >= 2 and w not in _CHINESE_PUNCTUATION]
    except Exception:
        # Fallback: character bigrams
        words = [text[i:i+2] for i in range(len(text) - 1) if text[i:i+2].strip()]
    _WORD_CACHE[text] = words
    return words


def _jaccard(a: list[str], b: list[str]) -> float:
    """Jaccard similarity between two token lists."""
    if not a or not b:
        return 0.0
    set_a, set_b = set(a), set(b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def mmr_select(
    chunks: list[dict[str, Any]],
    query: str | None = None,
    lambda_param: float = 0.7,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Select diverse, relevant chunks using MMR.

    Args:
        chunks: List of chunk dicts, each with "content" and "score".
        query: Optional query text (used for relevance, not required if scores are pre-computed).
        lambda_param: Balance between relevance (λ) and diversity (1-λ). Default 0.7.
            0.0 = pure diversity, 1.0 = pure relevance.
        min_score: Minimum absolute score to include a chunk (post-MMR filter).

    Returns:
        Selected chunks in MMR order (most relevant+diverse first).
    """
    if not chunks:
        return []

    # Sort by score descending first
    sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)

    # Pre-compute content tokenization for diversity comparisons
    tokenized: dict[int, list[str]] = {
        i: _tokenize(c.get("content", ""))
        for i, c in enumerate(sorted_chunks)
    }

    # Pre-compute relevance score for each chunk (use existing score)
    # The "score" field should come from reranker or retriever

    # MMR selection
    selected_indices = [0]  # Always pick the highest-scoring chunk first
    remaining_indices = list(range(1, len(sorted_chunks)))

    while remaining_indices:
        mmr_scores = []
        for r_idx in remaining_indices:
            relevance = sorted_chunks[r_idx].get("score", 0)
            # Diversity: max similarity to any already-selected chunk
            max_sim = max(
                _jaccard(tokenized[r_idx], tokenized[s_idx])
                for s_idx in selected_indices
            ) if selected_indices else 0.0
            mmr_val = lambda_param * relevance - (1 - lambda_param) * max_sim
            mmr_scores.append((mmr_val, r_idx))

        if not mmr_scores:
            break

        # Pick the chunk with highest MMR score
        mmr_scores.sort(key=lambda x: x[0], reverse=True)
        best_val, best_idx = mmr_scores[0]

        # Stop if no remaining chunk adds positive value
        if best_val <= 0:
            break

        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)

    # Return selected chunks in original score order (highest first)
    result = [sorted_chunks[i] for i in selected_indices]

    # Filter by minimum score
    if min_score > 0:
        result = [r for r in result if r.get("score", 0) >= min_score]

    logger.info(
        "MMR: %d input → %d selected (λ=%.1f, min_score=%.2f)",
        len(chunks), len(result), lambda_param, min_score,
    )
    return result
