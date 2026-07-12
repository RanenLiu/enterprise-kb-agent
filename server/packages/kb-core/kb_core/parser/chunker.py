from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
    min_chunk_size: int = 100,
) -> list[dict[str, Any]]:
    """
    层级感知分块: 追踪标题层级，为每个 chunk 附加完整的标题路径。

    Args:
        text: 输入文本
        chunk_size: 目标 chunk token 数 (近似字符数)
        overlap: 重叠字符数
        min_chunk_size: 最小 chunk 字符数

    Returns:
        list[dict]: [
            {
                "content": str,
                "chunk_index": int,
                "heading_path": str,          # 完整的标题路径，如 "第一维度 > 1.1 数据分级管控"
                "headings": list[str],        # 各级标题列表
                "paragraph_range": str,       # 段落范围标识
            },
            ...
        ]
    """
    # 按标题行预分割
    sections = _split_by_headings(text)

    chunks: list[dict[str, Any]] = []
    current_chunk = ""
    current_idx = 0
    heading_stack: list[str] = []  # 当前标题层级栈

    def _heading_level(line: str) -> int:
        """返回标题级别 (1-6)，非标题返回 0."""
        m = re.match(r"^(#{1,6})\s", line.strip())
        return len(m.group(1)) if m else 0

    def _flush():
        """提交当前 chunk（跳过纯页码标记的零碎内容）. """
        nonlocal current_chunk, current_idx
        if current_chunk:
            content = current_chunk.strip()
            # 跳过纯页码或空内容
            if len(content) > 10 or not re.match(r"^〖page:\d+〗\s*$", content):
                chunks.append({
                    "content": content,
                    "chunk_index": current_idx,
                    "heading_path": _heading_path(),
                    "headings": deepcopy([re.sub(r"^#{1,6}\s+", "", h) for h in heading_stack]),
                })
                current_idx += 1
        current_chunk = ""

    def _update_heading_stack(line: str):
        """根据标题行更新标题层级栈."""
        level = _heading_level(line)
        # 同层级或更高级别（# 更少）的标题出栈，子标题保留
        while heading_stack and _heading_level(heading_stack[-1]) >= level:
            heading_stack.pop()
        heading_stack.append(line.strip())

    def _heading_path() -> str:
        """从层级栈生成标题路径字符串."""
        titles = [re.sub(r"^#{1,6}\s+", "", h).replace("#", "") for h in heading_stack]
        return " > ".join(t for t in titles if t.strip())

    for section in sections:
        level = _heading_level(section)
        is_heading = level > 0

        if is_heading:
            # 遇到标题：先提交前一个 chunk，再更新层级栈
            _flush()
            # 只取标题行（\n 之前的部分），不包含正文
            heading_line = section.split("\n", 1)[0].strip()
            _update_heading_stack(heading_line)
            current_chunk = section.strip()
            continue

        # 正文内容：追加到当前 chunk
        if not current_chunk:
            current_chunk = section
        elif len(current_chunk) + len(section) <= chunk_size:
            current_chunk += section
        else:
            _flush()
            current_chunk = section

    # 提交最后一段
    _flush()

    # 后处理：合并太小的相邻 chunk（其 heading_path 相同或子标题关系）
    merged = _merge_small_chunks(chunks, min_chunk_size)

    return merged


def _merge_small_chunks(
    chunks: list[dict[str, Any]], min_size: int
) -> list[dict[str, Any]]:
    """合并太小的相邻 chunk 到前一个 chunk 中。

    规则:
    - 以 ## 开头的标题段落不合并（不同章节）
    - 正文小段落合并到前一个 chunk
    """
    if not chunks:
        return chunks

    result: list[dict[str, Any]] = [chunks[0]]
    for chunk in chunks[1:]:
        prev = result[-1]
        is_heading = chunk["content"].strip().startswith("##")
        is_small = len(chunk["content"]) < min_size

        # 标题段落不合并（不同章节）
        if is_heading:
            result.append(chunk)
        elif is_small and prev["content"]:
            # 小段正文合并到前一个 chunk
            prev["content"] += "\n" + chunk["content"]
        else:
            result.append(chunk)

    # 更新 chunk_index
    for i, chunk in enumerate(result):
        chunk["chunk_index"] = i

    return result


def _split_by_headings(text: str) -> list[str]:
    """按 Markdown 标题分割，保留标题和其下的正文。"""
    sections = re.split(r"\n(?=#{1,6}\s)", text)
    return [s.strip() for s in sections if s.strip()]


def _find_split(text: str, target: int) -> int:
    """在 target 位置附近找最近的句号/换行分割。"""
    search_start = max(0, target - 50)
    search_end = min(len(text), target + 50)

    candidates: list[int] = []
    for m in re.finditer(r"[。！？\n.!?]", text[search_start:search_end]):
        candidates.append(search_start + m.end())

    if candidates:
        return min(candidates, key=lambda x: abs(x - target))
    return target


class Chunker:
    """文档分块器的可注入包装."""

    def __init__(self, chunk_size: int = 512, overlap: int = 50, min_chunk_size: int = 100):
        self._chunk_size = chunk_size
        self._overlap = overlap
        self._min_chunk_size = min_chunk_size

    def chunk(self, text: str) -> list[dict[str, Any]]:
        return chunk_text(
            text,
            chunk_size=self._chunk_size,
            overlap=self._overlap,
            min_chunk_size=self._min_chunk_size,
        )
