"""RabbitMQ message producer for document processing."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from kb_biz.config.settings import settings
from kb_biz.services.queue import DocumentMessage

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "document.topic"

_publish_connection: aio_pika.Connection | None = None


async def _get_connection() -> aio_pika.Connection:
    """Lazy-initialize and return the shared RabbitMQ connection."""
    global _publish_connection
    if _publish_connection is None or _publish_connection.is_closed:
        _publish_connection = await aio_pika.connect_robust(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            login=settings.rabbitmq_user,
            password=settings.rabbitmq_pass,
        )
    return _publish_connection


async def publish(msg: DocumentMessage) -> bool:
    """Publish a document processing message via RabbitMQ.

    Returns True on success. Raises on connection/messaging failure.
    """
    connection = await _get_connection()
    channel = await connection.channel()
    try:
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        message = Message(
            body=json.dumps(asdict(msg)).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        routing_key = f"doc.process.{msg.action}"
        await exchange.publish(message, routing_key=routing_key)
        logger.debug("Published message to %s, doc_id=%s", EXCHANGE_NAME, msg.doc_id)
    finally:
        await channel.close()
    return True


async def close_connection() -> None:
    """Shut down the RabbitMQ connection."""
    global _publish_connection
    if _publish_connection and not _publish_connection.is_closed:
        await _publish_connection.close()
    _publish_connection = None
