from __future__ import annotations

from kb_core.rag.fulltext.base import SearchResult


def rrf(results: list[list[SearchResult]], k: int = 60) -> list[SearchResult]:
    """Reciprocal Rank Fusion -- 多路结果按位置倒数得分融合.

    Args:
        results: 每个元素是一个检索器的结果列表（已按分数降序排列）
        k: RRF 常数，默认 60

    Returns:
        融合去重后按 RRF 分数降序排列的列表
    """
    if not results or all(len(r) == 0 for r in results):
        return []

    # 计算每个 chunk 的 RRF 总分
    score_map: dict[str, float] = {}
    items_map: dict[str, SearchResult] = {}

    for channel in results:
        for rank, item in enumerate(channel):
            chunk_id = item.chunk_id
            score_map[chunk_id] = score_map.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            # 保留第一个出现的 item，并累积所有贡献渠道的来源信息
            if chunk_id not in items_map:
                items_map[chunk_id] = item
                items_map[chunk_id].sources = [item.source]
            elif item.source not in items_map[chunk_id].sources:
                items_map[chunk_id].sources.append(item.source)

    # 按 RRF 分数降序排列
    sorted_items = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
    fused: list[SearchResult] = []
    for chunk_id, score in sorted_items:
        item = items_map[chunk_id]
        item.score = score
        fused.append(item)
    return fused


class RRFMerge:
    """RRF 融合器的可注入包装."""

    def __init__(self, k: int = 60):
        self._k = k

    def merge(
        self, results: list[list[SearchResult]], weights: list[float] | None = None
    ) -> list[SearchResult]:
        """Merge results from multiple channels.

        Args:
            results: Per-channel ranked results.
            weights: Optional per-channel weight (currently unused, kept for API compatibility).

        Returns:
            Fused list sorted by RRF score descending.
        """
        return rrf(results, k=self._k)
