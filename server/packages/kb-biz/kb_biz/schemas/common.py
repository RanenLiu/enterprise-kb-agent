from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
    meta: Optional[dict[str, Any]] = None


class PaginationMeta(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20
