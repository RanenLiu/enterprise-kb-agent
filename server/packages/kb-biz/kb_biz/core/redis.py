from __future__ import annotations

import logging

from redis.asyncio import Redis

from kb_biz.config.settings import settings

logger = logging.getLogger("app")

_redis: Redis | None = None


async def get_redis() -> Redis | None:
    """Get the singleton Redis client. Returns None if not available."""
    global _redis
    if _redis is None:
        try:
            _redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning("Redis not available: %s", e)
            return None
    return _redis


async def close_redis():
    """Close the Redis connection on shutdown."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
        logger.info("Redis connection closed")
