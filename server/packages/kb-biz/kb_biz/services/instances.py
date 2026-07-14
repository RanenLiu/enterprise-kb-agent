"""Module-level service instances for backward compatibility.

These are initialized to None and will be wired at app startup.
See the FastAPI app lifespan for actual wiring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kb_core.rag.retrieval_li import LlamaIndexRetrievalService
    from kb_core.storage.minio_client import MinioClient

# Singleton stubs — wired at app startup
rag_service: Any = None  # will be kb_biz.modules.knowledge.KnowledgeService or old rag_service
retrieval_service: "LlamaIndexRetrievalService | None" = None  # wired at app startup
storage_client: "MinioClient | None" = None  # MinioClient instance

__all__ = ["rag_service", "retrieval_service", "storage_client"]
