from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.core.exceptions import ConflictException, NotFoundException
from kb_biz.services.instances import rag_service
from kb_biz.models.chunk import Chunk
from kb_biz.models.document import Document

logger = logging.getLogger("kb_biz.knowledge.service")


class KnowledgeService:
    """知识库 CRUD 业务逻辑."""

    async def list_documents(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        dept_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        file_type: Optional[str] = None,
        keyword: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None,
        visibility_filter_func=None,
    ) -> tuple[list[Document], int]:
        query = select(Document)
        count_query = select(func.count(Document.id))

        if tenant_id:
            query = query.where(Document.tenant_id == tenant_id)
            count_query = count_query.where(Document.tenant_id == tenant_id)
        elif dept_id:
            query = query.where(Document.dept_id == dept_id)
            count_query = count_query.where(Document.dept_id == dept_id)
        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)
        if file_type:
            query = query.where(Document.file_type == file_type)
            count_query = count_query.where(Document.file_type == file_type)
        if project_id:
            query = query.where(Document.project_id == project_id)
            count_query = count_query.where(Document.project_id == project_id)
        else:
            # Knowledge base list: exclude project-scoped documents
            query = query.where(Document.project_id.is_(None))
            count_query = count_query.where(Document.project_id.is_(None))
        if keyword:
            like = f"%{keyword}%"
            query = query.where(Document.file_name.ilike(like) | Document.title.ilike(like))
            count_query = count_query.where(
                Document.file_name.ilike(like) | Document.title.ilike(like)
            )

        if visibility_filter_func:
            query = visibility_filter_func(query)
            count_query = visibility_filter_func(count_query)

        # 总数
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
        result = await session.execute(query)
        docs = result.scalars().all()

        return list(docs), total

    async def get_document(self, doc_id: uuid.UUID, session: AsyncSession) -> Optional[Document]:
        return await session.get(Document, doc_id)

    async def delete_document(self, doc_id: uuid.UUID, session: AsyncSession) -> bool:

        return await rag_service.delete_document(doc_id, session)

    async def reindex_document(self, doc_id: uuid.UUID, session: AsyncSession) -> Document:

        from kb_core.indexing.service import delete_milvus_vectors
        # delete_neo4j_triples removed — Phase 2: kb-enterprise Neo4j

        doc = await session.get(Document, doc_id)
        if not doc:
            raise NotFoundException("Document")
        if doc.status in ("parsing", "chunking", "indexing"):
            raise ConflictException("Document is being indexed")

        # 清理旧索引数据
        try:
            delete_milvus_vectors(str(doc_id))
        except Exception as e:
            logger.warning("Milvus cleanup failed during reindex: %s", e)
        # delete_neo4j_triples removed — Phase 2: kb-enterprise Neo4j
        await session.execute(sa_delete(Chunk).where(Chunk.doc_id == doc_id))

        doc.status = "pending"
        doc.error_message = None
        doc.chunk_count = 0
        session.add(doc)
        await session.commit()  # 先提交，再发消息，避免与 worker 死锁

        from kb_biz.services.queue import publish_document_message
        try:
            await publish_document_message(doc_id, "reindex", doc.dept_id)
        except Exception as e:
            logger.warning(
                "Failed to publish reindex message for %s: %s", doc_id, e
            )

        return doc


knowledge_service = KnowledgeService()
