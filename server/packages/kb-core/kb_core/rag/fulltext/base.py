from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    """检索结果统一模型，所有检索器共享."""
    chunk_id: str
    doc_id: str
    dept_id: str
    content: str
    heading_path: str = ""
    page_range: str = ""
    score: float
    source: str  # "vector" / "fulltext" / "graph"
    sources: list[str] = []  # all contributing channel sources after fusion
    visibility: str = "dept"  # "private" / "dept" / "public"
