"""Document processing queue — delegates to adapter or in-memory queue."""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from kb_biz.config.settings import settings

logger = logging.getLogger("kb_biz.services.queue")

# Determine which queue backend to use.
USE_ROCKETMQ = os.getenv("USE_ROCKETMQ", "").lower() in ("true", "1", "yes")
USE_MEMORY_QUEUE = os.getenv("USE_MEMORY_QUEUE", "").lower() in ("true", "1", "yes")


@dataclass
class DocumentMessage:
    doc_id: str
    action: str  # "process" | "delete" | "reindex"
    dept_id: str
    published_at: str = ""


# Lazy adapter imports (avoid circular dependency with kb_adapter_rabbitmq)
async def _publish_via_rabbitmq(msg: DocumentMessage) -> bool:
    from kb_adapter_rabbitmq.producer import publish
    return await publish(msg)


async def _publish_via_rocketmq(msg: DocumentMessage) -> bool:
    try:
        from kb_adapter_rocketmq.producer import publish
        return await publish(msg)
    except ImportError:
        logger.warning("kb-adapter-rocketmq not installed, falling back to memory queue")
        return await _publish_via_memory(msg)


# In-memory queue
_memory_queue: asyncio.Queue | None = None


async def _publish_via_memory(msg: DocumentMessage) -> bool:
    global _memory_queue
    if _memory_queue is None:
        _memory_queue = asyncio.Queue()
    await _memory_queue.put(msg)
    return True


if USE_MEMORY_QUEUE:
    _publish = _publish_via_memory
elif USE_ROCKETMQ:
    _publish = _publish_via_rocketmq
else:
    _publish = _publish_via_rabbitmq


async def publish_document_message(doc_id: str, action: str, dept_id: str | None) -> bool:
    """Publish a document processing message.

    Priority: memory queue > RocketMQ > RabbitMQ.
    """
    msg = DocumentMessage(
        doc_id=str(doc_id),
        action=action,
        dept_id=str(dept_id) if dept_id else "",
        published_at=datetime.now(timezone.utc).isoformat(),
    )
    return await _publish(msg)
