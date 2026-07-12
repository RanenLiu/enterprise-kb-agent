"""RabbitMQ message consumer primitives for document processing worker."""
from __future__ import annotations

import aio_pika
from aio_pika import ExchangeType

from kb_biz.config.settings import settings

EXCHANGE_NAME = "document.topic"
QUEUE_NAME = "doc.processing"
DLX_NAME = "document.dlx"
DLQ_NAME = "doc.failed"


async def get_connection() -> aio_pika.Connection:
    """Create a new RabbitMQ consumer connection."""
    return await aio_pika.connect_robust(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        login=settings.rabbitmq_user,
        password=settings.rabbitmq_pass,
    )


async def ensure_queue(connection: aio_pika.Connection) -> None:
    """Declare exchange, queue, and dead-letter infrastructure."""
    channel = await connection.channel()

    # Main exchange + queue
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, ExchangeType.TOPIC, durable=True,
    )
    queue = await channel.declare_queue(
        QUEUE_NAME, durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_NAME,
            "x-dead-letter-routing-key": "doc.failed",
        },
    )
    await queue.bind(exchange, routing_key="doc.process.*")

    # Dead-letter exchange + queue
    dlx = await channel.declare_exchange(DLX_NAME, ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(DLQ_NAME, durable=True)
    await dlq.bind(dlx, routing_key="doc.failed")

    await channel.close()
