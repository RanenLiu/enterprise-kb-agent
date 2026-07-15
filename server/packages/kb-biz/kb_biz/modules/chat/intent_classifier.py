"""Embedding-based intent pre-classification for fast-path general_chat detection.

替代 jieba 实体词判断的意图二次校验方案。
使用 KNN（最近邻匹配）：逐条比对用户 query embedding 与已知闲聊样例的余弦相似度，
任一匹配即判为闲聊。比单一质心方案更准确保留了各类闲聊的语义方向。

使用条件：
- graph.py Step 3：general_chat 是否真的跳过检索
- nodes.py tool_selector：LLM 返回空工具时是否强制检索
"""

from __future__ import annotations

import logging

from kb_core.indexing.service import embed_texts

logger = logging.getLogger("kb_biz.chat.intent_classifier")

# ── 代表性闲聊查询 ──────────────────────────────────────────────────
# 覆盖问候、感谢、肯定、寒暄、告别等无需检索的场景。
# 这些 query 的 embedding 用于 KNN（最近邻）余弦相似度匹配。
_CHAT_EXAMPLES = [
    # 中文问候
    "你好",
    "您好",
    "你好呀",
    "您好啊",
    "大家好",
    "早上好",
    "下午好",
    "晚上好",
    "hello",
    "hi",
    "嗨",
    "hey",
    # 感谢
    "谢谢",
    "谢谢你",
    "非常感谢",
    "感谢",
    "thanks",
    "thank you",
    # 自我介绍/询问能力
    "你是谁",
    "你能做什么",
    "你有什么功能",
    "你可以干什么",
    # 告别
    "再见",
    "拜拜",
    "明天见",
    "see you",
    # 肯定/确认
    "好的",
    "明白了",
    "知道了",
    "没问题",
    "可以的",
    "不错",
    "真棒",
    "厉害",
    "哈哈",
    # 其他常见闲聊
    "在吗",
    "在不在",
    # 接地气问候/寒暄（实测补充）
    "你吃了吗",
    "在干嘛",
    "辛苦了",
]

# ── 缓存的闲聊样例 embedding ──────────────────────────────────────
_chat_embeddings: list[list[float]] | None = None


def _l2_normalize(v: list[float]) -> list[float]:
    """L2 归一化。"""
    norm = sum(x * x for x in v) ** 0.5
    if norm > 0:
        return [x / norm for x in v]
    return v


def _dot(a: list[float], b: list[float]) -> float:
    """向量点积。"""
    return sum(x * y for x, y in zip(a, b))


def _compute_chat_embeddings() -> list[list[float]]:
    """计算所有闲聊样例的 embedding（_CHAT_EXAMPLES 的 embed_texts 结果）。"""
    embs = embed_texts(_CHAT_EXAMPLES)
    if not embs:
        logger.warning("Chat embeddings: embed_texts returned empty")
        return []
    logger.info("Chat embeddings computed (count=%d, dim=%d)", len(embs), len(embs[0]))
    return embs  # embed_texts 已返回 L2 归一化向量


def get_chat_embeddings() -> list[list[float]]:
    """获取缓存的闲聊样例 embedding（首次调用时计算并缓存）。"""
    global _chat_embeddings
    if _chat_embeddings is None:
        try:
            _chat_embeddings = _compute_chat_embeddings()
        except Exception:
            logger.exception("Failed to compute chat embeddings")
            _chat_embeddings = []
    return _chat_embeddings


def is_chat_embedding(embedding: list[float], threshold: float = 0.82) -> bool:
    """判断 query embedding 是否属于闲聊类。

    使用 KNN（最近邻）：将 query embedding 与所有已知闲聊样例做余弦相似度比较，
    若任一匹配度 >= threshold 则判为闲聊。

    Args:
        embedding: 用户 query 的嵌入向量。
        threshold: 余弦相似度阈值。越高则只匹配最明显的闲聊。

    Returns:
        True 表示该 query 语义上接近闲聊，应跳过检索。
    """
    embs = get_chat_embeddings()
    if not embs:
        return False
    emb = _l2_normalize(embedding)
    return any(_dot(emb, e) >= threshold for e in embs)


def reset_centroid() -> None:
    """重置缓存，下次调用时重新计算（仅测试用）。"""
    global _chat_embeddings
    _chat_embeddings = None
