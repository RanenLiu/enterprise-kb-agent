from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from kb_adapter_postgres.base import Base
from kb_biz.models.mixins import TimestampMixin, UUIDMixin


class Chunk(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chunks"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dept_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    hypothetical_questions: Mapped[Optional[list[dict]]] = mapped_column(JSONB, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    milvus_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content_tsv: Mapped[Optional[object]] = mapped_column(TSVECTOR, nullable=True)
