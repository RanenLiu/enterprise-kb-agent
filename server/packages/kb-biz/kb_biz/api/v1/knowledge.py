from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.core.auth.deps import PermissionChecker, get_current_user
from kb_biz.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from kb_biz.core.limits import MAX_DOCUMENTS, MAX_DOCUMENT_SIZE_MB
from kb_biz.core.operation_log import record_operation
from kb_adapter_postgres.session import get_session
from kb_biz.models.document import Document
from kb_biz.models.role import Role, UserRole
from kb_biz.models.user import User
from kb_biz.modules.knowledge import knowledge_service
# from app.modules.rag.retrieval.graph import get_doc_graph  # Phase 2: kb-enterprise Neo4j
from kb_biz.services.instances import rag_service
from kb_biz.schemas.common import PaginationMeta, Response
from kb_biz.schemas.knowledge import (
    DocumentResponse,
    ReindexResponse,
    UploadResponse,
    VisibilityUpdate,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents", response_model=Response[list[DocumentResponse]])
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    file_type: Optional[str] = None,
    keyword: Optional[str] = None,
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    _: User = Depends(PermissionChecker(["document.read"])),
    session: AsyncSession = Depends(get_session),
):
    """List documents scoped to the current user's tenant/department."""
    is_super = await _is_super_admin(session, current_user)
    is_tenant = await _is_tenant_admin(session, current_user)
    is_admin = is_super or is_tenant
    project_id_uuid = uuid.UUID(project_id) if project_id else None

    # Get documents with visibility filter
    docs, total = await knowledge_service.list_documents(
        tenant_id=current_user.tenant_id if not is_super else None,
        dept_id=current_user.dept_id if not is_super and not is_tenant else None,
        page=page,
        page_size=page_size,
        status=status,
        file_type=file_type,
        keyword=keyword,
        project_id=project_id_uuid,
        session=session,
        visibility_filter_func=lambda q: _apply_visibility_filter(q, current_user, is_admin),
    )
    return Response(
        data=[_doc_to_response(d) for d in docs],
        meta=PaginationMeta(total=total, page=page, page_size=page_size).model_dump(),
    )


@router.post("/upload", response_model=Response[UploadResponse])
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    _: User = Depends(PermissionChecker(["document.create"])),
    session: AsyncSession = Depends(get_session),
):
    """Upload a document, store raw file, and enqueue parsing/indexing.

    Requires document.create permission. For project-scoped documents,
    use the projects/{id}/upload endpoint instead.
    """
    if not current_user.dept_id:
        role_ids = await session.execute(
            select(UserRole.role_id).where(UserRole.user_id == current_user.id)
        )
        role_codes = await session.execute(
            select(Role.code).where(Role.id.in_([r[0] for r in role_ids.all()]))
        )
        user_role_codes = {r[0] for r in role_codes.all()}
        if "super_admin" not in user_role_codes and "tenant_admin" not in user_role_codes:
            raise ValidationException(
                "User must belong to a department to upload documents"
            )
    # Check document count limit for department
    doc_count = await session.execute(
        select(func.count()).select_from(Document).where(Document.dept_id == current_user.dept_id)
    )
    if doc_count.scalar() >= MAX_DOCUMENTS:
        raise ValidationException(f"已达文档数量上限（{MAX_DOCUMENTS} 个）")

    content = await file.read()

    # Check file size limit
    if len(content) > MAX_DOCUMENT_SIZE_MB * 1024 * 1024:
        raise ValidationException(f"单文档大小不能超过 {MAX_DOCUMENT_SIZE_MB}MB")

    doc = await rag_service.upload_document(
        file_content=content,
        file_name=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        dept_id=current_user.dept_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        session=session,
    )
    await record_operation(
        session, current_user, "upload", "document", str(doc.id), doc.file_name
    )
    return Response(
        data=UploadResponse(
            id=str(doc.id),
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
        )
    )


@router.get("/documents/{doc_id}", response_model=Response[DocumentResponse])
async def get_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _: User = Depends(PermissionChecker(["document.read"])),
    session: AsyncSession = Depends(get_session),
):
    """Get a single document by ID."""
    doc = await knowledge_service.get_document(doc_id, session)
    if not doc:
        raise NotFoundException("Document")
    await _check_document_visibility(doc, current_user, session)
    return Response(data=_doc_to_response(doc))


@router.delete("/documents/{doc_id}", response_model=Response[None])
async def delete_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _: User = Depends(PermissionChecker(["document.delete"])),
    session: AsyncSession = Depends(get_session),
):
    """Delete a document and its associated vectors/indices."""
    doc = await knowledge_service.get_document(doc_id, session)
    if not doc:
        raise NotFoundException("Document")
    await _check_document_visibility(doc, current_user, session)
    file_name = doc.file_name
    success = await knowledge_service.delete_document(doc_id, session)
    if not success:
        raise NotFoundException("Document")
    await record_operation(
        session, current_user, "delete", "document", str(doc_id), file_name
    )
    return Response(data=None)


@router.put("/documents/{doc_id}/visibility", response_model=Response[DocumentResponse])
async def update_document_visibility(
    doc_id: uuid.UUID,
    body: VisibilityUpdate,
    current_user: User = Depends(get_current_user),
    _: User = Depends(PermissionChecker(["document.update"])),
    session: AsyncSession = Depends(get_session),
):
    """Update document visibility: private / dept / public."""
    doc = await knowledge_service.get_document(doc_id, session)
    if not doc:
        raise NotFoundException("Document")
    await _check_document_visibility(doc, current_user, session)

    if body.visibility not in ("private", "dept", "public"):
        raise ValidationException("Visibility must be private, dept, or public")

    # Only super_admin and tenant_admin can set to or change from public
    if body.visibility == "public" or doc.visibility == "public":
        is_admin = await _is_super_admin(session, current_user) or await _is_tenant_admin(session, current_user)
        if not is_admin:
            raise ForbiddenException("只有超级管理员或租户管理员可以管理租户级别可见性")

    old_vis = doc.visibility
    doc.visibility = body.visibility
    session.add(doc)
    await record_operation(
        session,
        current_user,
        "update",
        "document",
        str(doc_id),
        f"{doc.file_name}: visibility {old_vis}→{body.visibility}",
    )
    return Response(data=_doc_to_response(doc))


@router.post("/documents/{doc_id}/reindex", response_model=Response[ReindexResponse])
async def reindex_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _: User = Depends(PermissionChecker(["document.reindex"])),
    session: AsyncSession = Depends(get_session),
):
    """Re-trigger indexing for a document."""
    doc = await knowledge_service.get_document(doc_id, session)
    if not doc:
        raise NotFoundException("Document")
    await _check_document_visibility(doc, current_user, session)
    doc = await knowledge_service.reindex_document(doc_id, session)
    await record_operation(
        session, current_user, "reindex", "document", str(doc_id), doc.file_name
    )
    return Response(data=ReindexResponse(id=str(doc.id), status=doc.status))


@router.get("/status/events")
async def document_status_events():
    """SSE endpoint: pushes document status changes to connected clients."""
    import asyncio

    async def event_stream():
        from kb_biz.core.events import subscribe_document_status

        async for data in subscribe_document_status():
            yield f"event: status_change\ndata: {json.dumps(data)}\n\n"

    return StreamingResponse(
        event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/documents/{doc_id}/graph", response_model=Response)
async def get_document_graph(
    doc_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(PermissionChecker(["document.read"])),
):
    """Get document's Neo4j knowledge graph data (entities + relations)."""
    # Phase 2: kb-enterprise Neo4j graph
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=501,
        content={"code": 501, "message": "Knowledge graph is not yet implemented (Phase 2: kb-enterprise Neo4j)", "data": None},
    )


async def _is_super_admin(session: AsyncSession, user: User) -> bool:
    """Check whether the user has the super_admin role."""
    result = await session.execute(
        select(Role)
        .join(UserRole)
        .where(UserRole.user_id == user.id, Role.code == "super_admin")
    )
    return result.scalar_one_or_none() is not None


async def _is_tenant_admin(session: AsyncSession, user: User) -> bool:
    """Check whether the user has the tenant_admin role."""
    result = await session.execute(
        select(Role)
        .join(UserRole)
        .where(UserRole.user_id == user.id, Role.code == "tenant_admin")
    )
    return result.scalar_one_or_none() is not None


async def _check_document_visibility(doc: Document, current_user: User, session: AsyncSession) -> None:
    """Raise NotFoundException if the user cannot access this document due to visibility rules."""
    is_super = await _is_super_admin(session, current_user)
    is_tenant = await _is_tenant_admin(session, current_user)
    if not (is_super or is_tenant):
        if doc.visibility == "private" and str(doc.uploaded_by) != str(current_user.id):
            raise NotFoundException("Document")
        if doc.visibility == "dept" and str(doc.dept_id) != str(current_user.dept_id):
            raise NotFoundException("Document")


def _apply_visibility_filter(
    query: Any,
    current_user: User,
    is_admin: bool,
) -> Any:
    """Add visibility + dept_id filter to a Document query.

    - super_admin/tenant_admin: no visibility filter (see all)
    - Others:
        - visibility=private AND uploaded_by=current_user
        - OR visibility=dept AND dept_id=current_user.dept_id
        - OR visibility=public
    """
    if is_admin:
        return query
    from sqlalchemy import or_, and_
    return query.where(
        or_(
            and_(Document.visibility == "private", Document.uploaded_by == current_user.id),
            and_(Document.visibility == "dept", Document.dept_id == current_user.dept_id),
            Document.visibility == "public",
        )
    )


@router.get("/preview-text/{doc_id}")
async def preview_office_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _: User = Depends(PermissionChecker(["document.read"])),
    session: AsyncSession = Depends(get_session),
):
    """Extract plain text from an office document for local preview.

    Supports .docx, .xlsx, .pptx. Downloads the file from object storage
    and returns extracted text content. Falls back to a download hint
    if text extraction is not possible.
    """
    from kb_biz.services.instances import storage_client
    from kb_biz.services.preview import extract_html, extract_text, OFFICE_EXTENSIONS

    doc = await session.get(Document, doc_id)
    if not doc:
        raise NotFoundException("Document")

    ext = "." + (doc.file_name.rsplit(".", 1)[-1].lower() if "." in doc.file_name else "")
    PREVIEW_EXTENSIONS = OFFICE_EXTENSIONS | frozenset({".eml", ".msg"})
    if ext not in PREVIEW_EXTENSIONS:
        raise NotFoundException("Preview not available for this file type")

    try:
        data = await storage_client.download_file(doc.file_path)
    except Exception as e:
        raise NotFoundException(f"File content not found in storage: {e}")

    # Construct download URL for the banner link
    from urllib.parse import quote
    path_segments = doc.file_path.split("/")
    download_url = "/api/v1/admin/files/" + "/".join(quote(s, safe="") for s in path_segments)

    # Try HTML conversion first (docx/pptx/xlsx → styled HTML), fallback to plain text
    html = extract_html(doc.file_name, data, download_url=download_url)
    if html:
        return Response(data=f"__HTML__:{html}")

    text = extract_text(doc.file_name, data)
    if text is None:
        # Try email parser for .eml files
        ext = "." + (doc.file_name.rsplit(".", 1)[-1].lower() if "." in doc.file_name else "")
        if ext in (".eml", ".msg"):
            try:
                from email import policy
                from email.parser import BytesParser
                msg = BytesParser(policy=policy.default).parsebytes(data)
                if msg.is_multipart():
                    parts = []
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            text = part.get_content()
                            if text:
                                parts.append(text)
                    text = "\n".join(parts) if parts else msg.get_body(preferencelist=("plain",)).get_content()
                else:
                    text = msg.get_content() or ""
            except Exception:
                pass
        if not text:
            raise NotFoundException("Could not extract text from this document")

    return Response(data=text)


def _doc_to_response(d: Document) -> DocumentResponse:
    """Convert an ORM Document instance to a Pydantic DocumentResponse."""
    return DocumentResponse(
        id=str(d.id),
        dept_id=str(d.dept_id),
        title=d.title,
        file_name=d.file_name,
        file_type=d.file_type,
        file_size=d.file_size,
        md5=d.md5,
        visibility=d.visibility,
        status=d.status,
        error_message=d.error_message,
        file_path=d.file_path,
        chunk_count=d.chunk_count,
        project_id=str(d.project_id) if d.project_id else None,
        uploaded_by=str(d.uploaded_by) if d.uploaded_by else None,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )
