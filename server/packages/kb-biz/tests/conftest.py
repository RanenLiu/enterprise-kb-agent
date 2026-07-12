"""Test configuration with mock Redis for retrieval cache tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def redis_client():
    """Provide a mock Redis client for testing.

    The retrieval cache functions call get_redis() from kb_biz.modules.chat.memory,
    which creates a real Redis connection.  For tests we monkey-patch
    get_redis to return a fake redis-like object backed by a dict.
    """
    import kb_biz.modules.chat.memory as mem

    store: dict[str, str] = {}

    class FakeRedis:
        """Minimal fake Redis that stores string keys in a dict."""

        async def get(self, key: str) -> str | None:
            return store.get(key)

        async def set(self, key: str, value: str, ex: int | None = None) -> None:
            store[key] = value

        async def delete(self, key: str) -> None:
            store.pop(key, None)

        async def exists(self, key: str) -> bool:
            return key in store

        async def rpush(self, key: str, value: str) -> None:
            store.setdefault(key, [])
            store[key].append(value)

        async def lrange(self, key: str, start: int, end: int) -> list[str]:
            return store.get(key, [])

        async def expire(self, key: str, ttl: int) -> None:
            pass

    fake = FakeRedis()
    original_get_redis = mem.get_redis

    async def mock_get_redis():
        return fake  # type: ignore[return-value]

    mem.get_redis = mock_get_redis  # type: ignore[assignment]
    yield fake
    mem.get_redis = original_get_redis
