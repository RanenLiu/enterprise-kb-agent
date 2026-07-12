"""User info Redis cache.

Strategy (Write-Through):
  - Login success → write cache (TTL 5 min)
  - User login → read cache first, fall back to DB + backfill
  - User info change → invalidate cache
  - Redis unavailable → degrade gracefully to direct DB query
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from kb_biz.core.redis import get_redis

logger = logging.getLogger("kb_biz.user_cache")

CACHE_TTL = 300  # 5 分钟
PREFIX = "user:cache:"


def _key(username: str) -> str:
    return f"{PREFIX}{username}"


async def get_cached_user(username: str) -> Optional[dict]:
    """Get cached user info; returns None on cache miss."""
    try:
        redis = await get_redis()
        if redis is None:
            return None
        data = await redis.get(_key(username))
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning("Redis cache read failed: %s", e)
        return None


async def set_cached_user(username: str, user_data: dict) -> None:
    """Write user cache (auto-expires after TTL)."""
    try:
        redis = await get_redis()
        if redis is None:
            return
        await redis.setex(_key(username), CACHE_TTL, json.dumps(user_data))
    except Exception as e:
        logger.warning("Redis cache write failed: %s", e)


async def invalidate_user(username: str) -> None:
    """Invalidate cache on user info change to ensure consistency."""
    try:
        redis = await get_redis()
        if redis is None:
            return
        await redis.delete(_key(username))
    except Exception as e:
        logger.warning("Redis cache delete failed: %s", e)
