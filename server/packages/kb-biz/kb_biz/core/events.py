"""Real-time event publishing (Redis pub/sub).

Used by the worker to notify the API about document status changes,
and by the SSE endpoint to push those events to connected clients.
"""
from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger("kb_biz.core.events")

STATUS_CHANNEL = "document:status"


async def publish_document_status(doc_id: str, status: str) -> None:
    """Publish a document status change event via Redis."""
    from kb_biz.core.redis import get_redis

    redis = await get_redis()
    if redis is None:
        return
    try:
        payload = json.dumps({"doc_id": doc_id, "status": status})
        await redis.publish(STATUS_CHANNEL, payload)
    except Exception as e:
        logger.warning("Failed to publish status event: %s", e)


async def subscribe_document_status():
    """Async generator yielding SSE events for document status changes.

    Yields dicts with ``doc_id`` and ``status`` keys.
    """
    from kb_biz.core.redis import get_redis

    redis = await get_redis()
    if redis is None:
        return

    pubsub = redis.pubsub()
    await pubsub.subscribe(STATUS_CHANNEL)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            if msg is None:
                # Timeout — yield nothing, keep alive; EventSource auto-reconnects
                continue
            try:
                data = json.loads(msg["data"])
                yield data
            except Exception as e:
                logger.warning("Invalid status event: %s", e)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(STATUS_CHANNEL)
        await pubsub.close()
