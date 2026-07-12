"""Tests for RRF fusion — no external dependencies needed."""
from __future__ import annotations

from kb_core.rag.fulltext.base import SearchResult
from kb_core.rag.fusion import RRFMerge


def _r(doc_id: str, score: float, source: str = "vector") -> SearchResult:
    return SearchResult(
        chunk_id=f"chunk-{doc_id}",
        doc_id=doc_id,
        dept_id="dept-1",
        content=f"content of {doc_id}",
        heading_path="",
        page_range="",
        score=score,
        source=source,
    )


class TestRRFMerge:
    def test_single_channel(self):
        merger = RRFMerge(k=60)
        results = merger.merge(
            [[_r("a", 0.9), _r("b", 0.8)]],
        )
        assert len(results) == 2
        assert results[0].doc_id == "a"
        assert results[1].doc_id == "b"

    def test_two_channels_with_overlap(self):
        merger = RRFMerge(k=60)
        results = merger.merge([
            [_r("a", 0.9), _r("b", 0.8)],
            [_r("a", 0.7), _r("c", 0.9)],
        ])
        doc_ids = [r.doc_id for r in results]
        assert "a" in doc_ids
        assert "b" in doc_ids
        assert "c" in doc_ids
        # "a" appears in both channels, should rank higher
        assert doc_ids[0] == "a"

    def test_three_channels_with_weights(self):
        merger = RRFMerge(k=60)
        results = merger.merge(
            [
                [_r("a", 0.9, "vector"), _r("b", 0.8, "vector")],
                [_r("c", 0.95, "fulltext")],
                [_r("a", 0.85, "graph")],
            ],
            weights=[0.4, 0.3, 0.3],
        )
        assert len(results) >= 2
        doc_ids = [r.doc_id for r in results]
        assert "a" in doc_ids

    def test_empty_input(self):
        merger = RRFMerge()
        assert merger.merge([[], []]) == []

    def test_k_value_affects_scores(self):
        """Lower k gives more weight to rank position."""
        channels = [
            [_r("a", 0.9), _r("b", 0.8)],
            [_r("a", 0.7)],
        ]
        rrf_high = RRFMerge(k=100).merge(channels)
        rrf_low = RRFMerge(k=10).merge(channels)
        # Both should return same ordering
        assert rrf_high[0].doc_id == rrf_low[0].doc_id
