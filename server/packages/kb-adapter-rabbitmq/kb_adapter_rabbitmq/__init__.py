"""kb-adapter-rabbitmq: RabbitMQ adapter for document processing queue."""

from kb_adapter_rabbitmq.consumer import QUEUE_NAME, ensure_queue, get_connection
from kb_adapter_rabbitmq.producer import close_connection, publish

__all__ = ["QUEUE_NAME", "close_connection", "ensure_queue", "get_connection", "publish"]
