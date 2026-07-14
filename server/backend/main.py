"""Enterprise KB Backend -- Open Source Entry Point.

Assembles kb-biz routes with kb-adapter-postgres session.
Enterprise features (monitoring, projects, login logs, rate limiting, menu CRUD,
user import) live in kb-enterprise and are NOT registered here.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_adapter_postgres.session import async_session_factory, get_session
from kb_biz.core.auth.deps import PermissionChecker, RoleChecker, get_current_user
from kb_biz.models.user import User
from kb_biz.api.v1 import (
    admin as admin_router,
    auth as auth_router,
    chat as chat_router,
    knowledge as knowledge_router,
    logs as logs_router,
)
from kb_biz.config.settings import settings
from kb_biz.core.logging import setup_logging
from kb_biz.core.exception_handlers import global_exception_handler, validation_exception_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize services, cleanup on shutdown."""
    setup_logging()
    logger.info("Starting Enterprise KB (Open Source) backend")

    # Wire up storage client (reads config from kb_core.config.settings)
    from kb_core.storage.minio_client import MinioClient
    import kb_biz.services.instances as di

    di.storage_client = MinioClient()
    try:
        await di.storage_client.ensure_bucket()
    except Exception as e:
        logger.warning("Bucket ensure failed (may be already created): %s", e)
    logger.info("Storage client initialized")

    # Wire up RAG pipeline (LlamaIndex)
    from kb_core.rag.vector_li import LlamaIndexVectorSearch
    from kb_core.rag.fulltext.pg import PGSearch
    from kb_core.rag.fusion import RRFMerge
    from kb_core.rag.retrieval_li import LlamaIndexRetrievalService

    vector_search = LlamaIndexVectorSearch()
    fulltext_search = PGSearch(async_session_factory=async_session_factory)
    fusion = RRFMerge()

    di.retrieval_service = LlamaIndexRetrievalService(
        vector_search=vector_search,
        fulltext_search=fulltext_search,
        fusion=fusion,
    )
    logger.info("RAG pipeline initialized (LlamaIndex)")

    # Wire up rag_service for document upload/delete
    from uuid import uuid4
    from datetime import datetime, timezone
    from pathlib import Path
    from kb_biz.models.document import Document
    from kb_biz.services.queue import publish_document_message

    class _RagServiceStub:
        async def upload_document(
            self,
            file_content,
            file_name,
            content_type,
            dept_id,
            user_id,
            session,
            tenant_id=None,
            project_id=None,
        ):
            import hashlib, uuid
            from kb_core.storage.minio_client import MinioClient

            md5 = hashlib.md5(file_content).hexdigest()
            doc_id = uuid.uuid4()
            file_type = Path(file_name).suffix.lstrip(".")
            object_path = f"raw/{dept_id or 'no-dept'}/{doc_id}/{file_name}"
            try:
                await di.storage_client.upload_file(
                    object_path, file_content, content_type
                )
            except Exception as e:
                logger.error("MinIO upload failed: %s", e)
                raise
            doc = Document(
                id=doc_id,
                tenant_id=tenant_id,
                dept_id=dept_id,
                title=file_name,
                file_name=file_name,
                file_type=file_type,
                file_size=len(file_content),
                file_path=object_path,
                md5=md5,
                status="pending",
                uploaded_by=user_id,
                project_id=project_id,
            )
            session.add(doc)
            await session.commit()
            _dept = str(dept_id) if dept_id else ""
            try:
                await publish_document_message(str(doc_id), "process", _dept)
            except Exception as e:
                logger.warning("Queue publish failed: %s", e)
            return doc

        async def delete_document(self, doc_id, session):
            from kb_core.indexing.service import delete_milvus_vectors

            doc = await session.get(Document, doc_id)
            if not doc:
                return False
            try:
                if doc.file_path:
                    await di.storage_client.delete_file(doc.file_path)
            except Exception as e:
                logger.warning("MinIO delete failed: %s", e)
            try:
                delete_milvus_vectors(str(doc_id))
            except Exception as e:
                logger.warning("Milvus delete failed: %s", e)
            await session.delete(doc)
            await session.commit()
            return True

    di.rag_service = _RagServiceStub()
    # Also update the module-level reference in knowledge.py (imported at module level)
    import kb_biz.api.v1.knowledge as _knowledge_mod
    import kb_biz.modules.knowledge.service as _knowledge_svc_mod

    _knowledge_mod.rag_service = di.rag_service
    _knowledge_svc_mod.rag_service = di.rag_service
    logger.info("RAG service initialized")

    yield

    logger.info("Shutting down Enterprise KB backend")

    logger.info("Shutting down Enterprise KB backend")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise KB (Open Source)",
        version="0.1.0",
        lifespan=lifespan,
    )

    # App state for exception handler
    app.state.logger = logger

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(Exception, global_exception_handler)

    from fastapi.exceptions import RequestValidationError
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Register routes
    app.include_router(auth_router.router, prefix="/api/v1")
    app.include_router(admin_router.router, prefix="/api/v1")
    app.include_router(chat_router.router, prefix="/api/v1")
    app.include_router(knowledge_router.router, prefix="/api/v1")
    app.include_router(logs_router.router, prefix="/api/v1")

    # Sidebar tenant info stub (frontend requests this on every page)
    from fastapi import APIRouter
    from kb_biz.schemas.common import Response

    _stub = APIRouter()

    @_stub.get("/admin/tenant", response_model=Response)
    async def _stub_tenant(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ):
        from kb_biz.models.tenant import Tenant
        tenant = await session.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = tenant.scalar_one_or_none()
        if tenant:
            return Response(data={"name": tenant.name, "logo": tenant.logo})
        return Response(data={"name": "企业知识库", "logo": None})

    @_stub.put("/admin/tenant", response_model=Response)
    async def _stub_update_tenant(
        body: dict,
        current_user: User = Depends(get_current_user),
        _: User = Depends(RoleChecker(["super_admin", "tenant_admin"])),
        session: AsyncSession = Depends(get_session),
    ):
        """Update tenant name and logo (open source stub)."""
        from kb_biz.models.tenant import Tenant

        name = body.get("name", "企业知识库")
        logo = body.get("logo")

        tenant = await session.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = tenant.scalar_one_or_none()
        if tenant:
            tenant.name = name
            if logo is not None:
                tenant.logo = logo
            session.add(tenant)
            await session.commit()
        return Response(data={"name": name, "logo": logo})

    @_stub.get("/admin/tenants", response_model=Response)
    async def _stub_tenants():
        return Response(
            data=[
                {"id": "default", "name": "企业知识库", "code": "default", "status": 1}
            ],
            meta={"total": 1, "page": 1, "page_size": 20},
        )

    app.include_router(_stub, prefix="/api/v1")

    return app


app = create_app()
