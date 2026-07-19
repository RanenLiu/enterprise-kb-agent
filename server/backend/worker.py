"""
Worker process: consumes RabbitMQ document processing messages.
Pipeline: parse → chunk → indexing (summary + HQG + embedding + Milvus).

OS edition only.

Start with: python -m worker
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import signal
import uuid

import aio_pika
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from kb_adapter_postgres.session import async_session_factory
from kb_adapter_rabbitmq.consumer import QUEUE_NAME, ensure_queue, get_connection
from kb_biz.config.settings import settings
from kb_biz.models.chunk import Chunk
from kb_biz.models.document import Document
from kb_core.indexing.service import (
    delete_milvus_vectors,
    embed_texts,
    generate_hypothetical_questions,
    generate_summary,
    index_to_milvus,
)
from kb_core.parser.chunker import chunk_text
from kb_core.parser.service import parse_document
from kb_core.storage.minio_client import MinioClient
from kb_biz.core.events import publish_document_status

logger = logging.getLogger("worker")
running = True

semaphore = asyncio.Semaphore(settings.rag_worker_concurrency)
_minio_client = MinioClient()


async def update_doc_status(
    session: AsyncSession, doc_id: str, status: str, error: str | None = None
) -> None:
    doc = await session.get(Document, uuid.UUID(doc_id))
    if doc:
        doc.status = status
        if error:
            doc.error_message = error
        session.add(doc)
        await session.flush()


async def process_document(msg: aio_pika.IncomingMessage) -> None:
    """Process a single document through the full indexing pipeline.

    Returns normally -> msg.process() context manager auto-acks.
    Exception propagates -> context manager auto-nacks, message returns to queue.
    """
    async with semaphore:
        body = json.loads(msg.body.decode())
        doc_id = body["doc_id"]
        dept_id = body["dept_id"] or None
        logger.info("Processing document %s (dept=%s)", doc_id, dept_id)

        async with async_session_factory() as session:
            try:
                # 1. Read file from MinIO
                doc = await session.get(Document, uuid.UUID(doc_id))
                if not doc:
                    logger.warning("Document %s not found, skipping", doc_id)
                    return

                file_content = await _minio_client.download_file(doc.file_path)

                # 2. Parse document
                await update_doc_status(session, doc_id, "parsing")
                result = await asyncio.to_thread(
                    parse_document,
                    content=file_content,
                    file_name=doc.file_name,
                    file_type=doc.file_type,
                )
                text = result.text

                # Clean up old chunks (may remain from a previous interrupted reindex)
                await session.execute(sa_delete(Chunk).where(Chunk.doc_id == doc_id))

                if not text:
                    await update_doc_status(session, doc_id, "failed", "解析结果为空")
                    await session.commit()
                    return

                # 3. Chunk text
                await update_doc_status(session, doc_id, "chunking")
                chunks = chunk_text(text)

                if not chunks:
                    await update_doc_status(session, doc_id, "failed", "分块结果为空")
                    await session.commit()
                    return

                # 4. Index (summary + HQG + embedding + Milvus)
                await update_doc_status(session, doc_id, "indexing")

                # 4a. LLM summary + HQG (parallel)
                summary_tasks = [generate_summary(c["content"]) for c in chunks]
                hqg_tasks = [generate_hypothetical_questions(c["content"]) for c in chunks]
                summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)
                hqgs = await asyncio.gather(*hqg_tasks, return_exceptions=True)

                for i, chunk in enumerate(chunks):
                    chunk["summary"] = (
                        summaries[i] if not isinstance(summaries[i], Exception) else ""
                    )
                    chunk["questions"] = hqgs[i] if not isinstance(hqgs[i], Exception) else []
                    chunk["doc_id"] = doc_id
                    chunk["dept_id"] = dept_id if dept_id and dept_id != "None" else ""

                # 4b. Embedding + Milvus
                milvus_ids: list[str] = []
                pg = 1
                has_pages = False
                for chunk in chunks:
                    raw = chunk.get("content", "")
                    chunk["_raw"] = raw
                    pages_in = re.findall(r"〖page:(\d+)〗", raw)
                    if pages_in:
                        has_pages = True
                        pg = int(pages_in[-1])
                    chunk["content"] = re.sub(r"〖page:\d+〗\s*", "", raw)
                    chunk["heading_path"] = (
                        f"{doc.file_name} > {chunk.get('heading_path','')}"
                        if chunk.get("heading_path") else doc.file_name
                    )
                    chunk["_pg"] = pg

                for i, chunk in enumerate(chunks):
                    if not has_pages:
                        chunk["page_range"] = ""
                        continue
                    pg = chunk["_pg"]
                    prev_pg = chunks[i - 1]["_pg"] if i > 0 else pg
                    if pg > prev_pg and i > 0:
                        if re.search(r"〖page:\d+〗\s*$", chunk.get("_raw", "")):
                            pg = prev_pg
                    chunk["page_range"] = f"{prev_pg}-{pg}" if pg > prev_pg else str(pg)

                try:
                    for chunk in chunks:
                        if doc.title:
                            chunk["content"] = f"[{doc.title}] {chunk['content']}"
                    texts_to_embed = [
                        (c.get("summary", "") or c["content"]) for c in chunks
                    ]
                    embeddings = await asyncio.to_thread(embed_texts, texts_to_embed)
                    milvus_ids = index_to_milvus(
                        doc_id, dept_id or "", doc.visibility, chunks, embeddings,
                        str(doc.project_id) if doc.project_id else "",
                    )
                except Exception as e:
                    logger.warning("Embedding/Milvus failed for %s: %s", doc_id, e)

                # 4c. Write chunks to PostgreSQL
                for i, chunk in enumerate(chunks):
                    content = chunk["content"][:8192]
                    page_range = chunk.get("page_range", "")

                    pg_chunk = Chunk(
                        doc_id=uuid.UUID(doc_id),
                        dept_id=uuid.UUID(dept_id) if dept_id else None,
                        chunk_index=chunk["chunk_index"],
                        content=content,
                        summary=chunk.get("summary", "")[:1000] if chunk.get("summary") else None,
                        hypothetical_questions=chunk.get("questions"),
                        chunk_metadata={
                            "heading_path": chunk.get("heading_path", ""),
                            "headings": chunk.get("headings", []),
                            "file_name": doc.file_name,
                            "page_range": page_range,
                        },
                        milvus_id=milvus_ids[i] if i < len(milvus_ids) else None,
                        embedding_model=settings.embedding_model,
                    )
                    session.add(pg_chunk)

                # 5. Done - commit transaction; msg.process() context auto-acks
                doc.status = "ready"
                doc.chunk_count = len(chunks)
                session.add(doc)
                await session.commit()
                await publish_document_status(doc_id, "ready")
                logger.info("Document %s indexed successfully (%d chunks)", doc_id, len(chunks))

            except Exception as e:
                logger.exception("Failed to process document %s", doc_id)
                await session.rollback()
                # Write failure status (new transaction, unaffected by rollback)
                doc = await session.get(Document, uuid.UUID(doc_id))
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(e)[:500]
                    session.add(doc)
                    await session.commit()
                    await publish_document_status(doc_id, "failed")
                raise  # Propagate -> on_message's msg.process() auto-nacks


async def handle_delete_message(body: dict) -> None:
    """Handle document deletion (clean up Milvus)."""
    doc_id = body["doc_id"]
    logger.info("Cleaning up document %s", doc_id)
    try:
        delete_milvus_vectors(doc_id)
    except Exception as e:
        logger.warning("Milvus delete failed for %s: %s", doc_id, e)


async def on_message(msg: aio_pika.IncomingMessage) -> None:
    """RabbitMQ message callback."""
    async with msg.process(ignore_processed=True):
        body = json.loads(msg.body.decode())
        action = body.get("action", "process")

        if action in ("process", "reindex"):
            await process_document(msg)
        elif action == "delete":
            await handle_delete_message(body)
            await msg.ack()
        else:
            logger.warning("Unknown action: %s", action)
            await msg.ack()


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Worker starting...")

    connection = await get_connection()
    await ensure_queue(connection)

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=settings.rag_worker_concurrency)

    queue = await channel.declare_queue(QUEUE_NAME, durable=True, passive=True)
    logger.info("Worker listening on queue %s", QUEUE_NAME)

    tasks: set[asyncio.Task] = set()

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            if not running:
                break
            task = asyncio.create_task(on_message(message))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    # Wait for in-flight tasks to complete before closing
    if tasks:
        logger.info("Waiting for %d in-flight tasks to complete...", len(tasks))
        await asyncio.gather(*tasks, return_exceptions=True)

    await connection.close()


def shutdown_handler(sig, frame):
    global running
    logger.info("Received signal %s, shutting down...", sig)
    running = False


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    asyncio.run(main())
