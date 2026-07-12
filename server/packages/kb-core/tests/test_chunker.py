"""Tests for text chunker — pure logic, no dependencies."""
from __future__ import annotations

from kb_core.parser.chunker import chunk_text


class TestChunker:
    def test_chunk_empty_text(self):
        result = chunk_text("")
        assert result == []

    def test_chunk_short_text(self):
        result = chunk_text("Hello world")
        assert len(result) == 1
        assert result[0]["content"] == "Hello world"
        assert result[0]["chunk_index"] == 0

    def test_chunk_with_headings(self):
        text = "# Title\n\nSome content here.\n\n## Subtitle\n\nMore content."
        result = chunk_text(text)
        assert len(result) >= 1

    def test_chunk_index_increments(self):
        """Each chunk should have an incrementing chunk_index."""
        text = "\n\n".join([f"Paragraph {i} content." for i in range(20)])
        result = chunk_text(text)
        for i, chunk in enumerate(result):
            assert chunk["chunk_index"] == i

    def test_chunk_heading_path(self):
        text = "# Main\n\nContent\n\n## Sub\n\nSub content"
        result = chunk_text(text)
        # Chunks should have heading_path for context
        for chunk in result:
            if "Sub" in chunk.get("content", ""):
                assert "Sub" in chunk.get("heading_path", "")
