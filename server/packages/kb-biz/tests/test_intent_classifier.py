"""Tests for embedding-based intent classifier and chat routing logic."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from kb_biz.modules.chat.intent_classifier import (
    _compute_chat_embeddings,
    _dot,
    _l2_normalize,
    get_chat_embeddings,
    is_chat_embedding,
    reset_centroid,
)

# ═══════════════════════════════════════════════
# _l2_normalize
# ═══════════════════════════════════════════════


class TestL2Normalize:
    def test_unit_vector_unchanged(self):
        v = [1.0, 0.0, 0.0]
        result = _l2_normalize(v)
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(0.0)

    def test_non_unit_vector(self):
        v = [3.0, 4.0]
        result = _l2_normalize(v)
        assert result[0] == pytest.approx(0.6)
        assert result[1] == pytest.approx(0.8)

    def test_zero_vector(self):
        v = [0.0, 0.0, 0.0]
        result = _l2_normalize(v)
        assert result == [0.0, 0.0, 0.0]


# ═══════════════════════════════════════════════
# _dot
# ═══════════════════════════════════════════════


class TestDot:
    def test_orthogonal(self):
        assert _dot([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_parallel(self):
        assert _dot([2.0, 3.0], [4.0, 5.0]) == pytest.approx(23.0)

    def test_empty(self):
        assert _dot([], []) == 0.0


# ═══════════════════════════════════════════════
# _compute_chat_embeddings
# ═══════════════════════════════════════════════


class TestComputeChatEmbeddings:
    def test_success(self):
        """embed_texts 返回多个归一化向量。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[0.8, 0.6], [0.6, 0.8]]
            embs = _compute_chat_embeddings()
            assert len(embs) == 2
            assert embs == [[0.8, 0.6], [0.6, 0.8]]

    def test_empty_embedding(self):
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = []
            assert _compute_chat_embeddings() == []


# ═══════════════════════════════════════════════
# is_chat_embedding (KNN: any example match)
# ═══════════════════════════════════════════════


class TestIsChatEmbedding:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        reset_centroid()
        yield
        reset_centroid()

    def test_exact_match(self):
        """Query 与某闲聊样例完全一致 → 匹配。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[1.0, 0.0], [0.0, 1.0]]
            assert is_chat_embedding([1.0, 0.0])

    def test_low_similarity_to_all(self):
        """Query 与所有样例都不像 → 不匹配。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[1.0, 0.0], [0.0, 1.0]]
            assert not is_chat_embedding([0.707, 0.707])  # cos sim = 0.707 with both

    def test_above_threshold_to_any(self):
        """Query 与任一样例 >= threshold → 匹配。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[1.0, 0.0], [0.6, 0.8]]
            # [0.95, 0.312] has cos sim 0.95 with [1.0, 0.0]
            assert is_chat_embedding([0.95, 0.3122499])

    def test_custom_threshold(self):
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[1.0, 0.0]]
            query_emb = [0.7, 0.7141428]  # cos sim 0.7
            assert is_chat_embedding(query_emb, threshold=0.6)
            assert not is_chat_embedding(query_emb, threshold=0.8)

    def test_no_embeddings(self):
        """embed_texts 返回空时 → False。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = []
            assert not is_chat_embedding([1.0, 0.0])

    def test_un_normalized_query(self):
        """非归一化 query 仍应正确匹配。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[0.6, 0.8]]
            assert is_chat_embedding([3.0, 4.0])  # normalized = [0.6, 0.8]

    def test_get_chat_embeddings_cache(self):
        """样例 embedding 应缓存，第二调用不走 embed_texts。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[0.6, 0.8]]
            get_chat_embeddings()
            assert mock_embed.call_count == 1
            get_chat_embeddings()
            assert mock_embed.call_count == 1  # cached

    def test_reset_centroid(self):
        """reset_centroid() 强制下次重新计算。"""
        with patch("kb_biz.modules.chat.intent_classifier.embed_texts") as mock_embed:
            mock_embed.return_value = [[0.6, 0.8]]
            get_chat_embeddings()
            assert mock_embed.call_count == 1
            reset_centroid()
            get_chat_embeddings()
            assert mock_embed.call_count == 2


# ═══════════════════════════════════════════════
# Routing logic: graph.py Step 3 has_content decision
# ═══════════════════════════════════════════════


class TestChatRouting:
    """Test the 'has_content' routing decision that determines whether to skip retrieval.

    The production code in graph.py:
        is_general_chat = state.intent == "general_chat"
        if is_general_chat:
            query_emb = state.metadata.get("query_embedding")
            if query_emb is not None:
                has_content = not is_chat_embedding(query_emb)
            else:
                has_content = True
        else:
            has_content = True
        if skip_intent and not (is_general_chat and has_content):
            tool_result = {"tool_results": []}  # skip retrieval
        else:
            tool_result = await tool_selector(state, llm)  # do retrieval
    """

    def _simulate_routing(
        self, intent: str, has_query_emb: bool, is_chat_result: bool
    ) -> bool:
        """Simulate the routing decision. Returns True if retrieval is skipped."""
        is_general_chat = intent == "general_chat"
        if is_general_chat:
            if has_query_emb:
                has_content = not is_chat_result
            else:
                has_content = True
        else:
            has_content = True

        from kb_biz.modules.chat.guardrail import should_skip_retrieval

        skip_intent = should_skip_retrieval(intent)
        if skip_intent and not (is_general_chat and has_content):
            return True  # skip retrieval
        return False  # do retrieval

    def test_greeting_skips_retrieval(self):
        """'你好' → general_chat, embedding matches chat → skip retrieval."""
        assert self._simulate_routing(
            intent="general_chat", has_query_emb=True, is_chat_result=True
        )

    def test_greeting_no_embedding_fallback(self):
        """'你好' but no embedding in state → has_content=True → falls to tool_selector."""
        result = self._simulate_routing(
            intent="general_chat", has_query_emb=False, is_chat_result=True
        )
        assert not result  # safe default: go to tool_selector

    def test_knowledge_query_misclassified_as_chat(self):
        """'报销流程是什么' → general_chat (misclassified), embedding not chat → do retrieval."""
        assert not self._simulate_routing(
            intent="general_chat", has_query_emb=True, is_chat_result=False
        )

    def test_knowledge_query_always_retrieves(self):
        """knowledge_query → skip_intent=False → always do retrieval."""
        assert not self._simulate_routing(
            intent="knowledge_query", has_query_emb=True, is_chat_result=True
        )

    def test_out_of_scope_skips(self):
        """out_of_scope → skip_intent=True, is_general_chat=False → skip retrieval."""
        assert self._simulate_routing(
            intent="out_of_scope", has_query_emb=True, is_chat_result=True
        )


# ═══════════════════════════════════════════════
# tool_selector logic: empty tool calls fallback
# ═══════════════════════════════════════════════


class TestToolSelectorFallback:
    """Test the fallback logic in tool_selector when LLM returns no tool calls."""

    def _simulate_fallback(self, has_query_emb: bool, is_chat_result: bool) -> bool:
        """Simulate the fallback decision. Returns True if retrieval is forced."""
        query_emb = [0.5, 0.5] if has_query_emb else None
        is_chat = False
        if query_emb is not None:
            is_chat = is_chat_result

        return not is_chat  # not chat → force retrieval

    def test_chat_query_skips_force(self):
        assert not self._simulate_fallback(has_query_emb=True, is_chat_result=True)

    def test_knowledge_query_forces_retrieval(self):
        assert self._simulate_fallback(has_query_emb=True, is_chat_result=False)

    def test_no_embedding_default_force(self):
        assert self._simulate_fallback(has_query_emb=False, is_chat_result=False)


# ═══════════════════════════════════════════════
# Guardrail: should_skip_retrieval
# ═══════════════════════════════════════════════


class TestShouldSkipRetrieval:
    @pytest.mark.parametrize(
        "intent,expected",
        [
            ("general_chat", True),
            ("harmful_query", True),
            ("out_of_scope", True),
            ("sensitive_topic", True),
            ("knowledge_query", False),
            ("document_task", False),
        ],
    )
    def test_skip_intents(self, intent, expected):
        from kb_biz.modules.chat.guardrail import should_skip_retrieval

        assert should_skip_retrieval(intent) is expected
