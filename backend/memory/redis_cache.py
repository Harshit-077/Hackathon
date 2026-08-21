"""Hot session context in Redis with in-memory fallback and TTLs."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from backend.engine.fallback import fallback_manager

logger = logging.getLogger("intent_memory")

DEFAULT_TTL = int(os.getenv("REDIS_TTL_SECONDS", "600"))
KEY_PREFIX = "intentui:session:"


class RedisCache:
    """Cache-aside hot context. Never raises to callers."""

    def __init__(self, client: Any | None = None, ttl: int = DEFAULT_TTL) -> None:
        self.ttl = ttl
        self._mem: dict[str, tuple[float, dict[str, Any]]] = {}
        self._client = client
        self._disabled = os.getenv("REDIS_DISABLED", "").lower() in {"1", "true", "yes"}
        if self._disabled:
            fallback_manager.redis_failed()
            return
        if self._client is None:
            self._client = self._connect()

    def _connect(self) -> Any | None:
        url = os.getenv("REDIS_URL")
        if not url:
            return None
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(url, socket_connect_timeout=0.4, socket_timeout=0.4)
            client.ping()
            return client
        except Exception as exc:
            logger.warning("Redis unavailable, using in-memory hot cache: %s", exc)
            fallback_manager.redis_failed()
            return None

    def disable(self) -> None:
        self._disabled = True
        self._client = None
        fallback_manager.redis_failed()

    def enable_memory_only(self) -> None:
        """Test helper: keep working without Redis."""
        self._disabled = True
        self._client = None

    @property
    def redis_ok(self) -> bool:
        return bool(self._client) and not self._disabled

    def _key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}{session_id}"

    def get_hot(self, session_id: str) -> dict[str, Any] | None:
        if self._disabled:
            return self._mem_get(session_id)
        if self._client is not None:
            try:
                raw = self._client.get(self._key(session_id))
                if raw:
                    data = json.loads(raw)
                    self._mem_set(session_id, data)
                    return data
            except Exception as exc:
                logger.warning("Redis get failed: %s", exc)
                fallback_manager.redis_failed()
                self._client = None
        return self._mem_get(session_id)

    def set_hot(self, session_id: str, payload: dict[str, Any], ttl: int | None = None) -> None:
        data = dict(payload)
        data["updated_at"] = time.time()
        self._mem_set(session_id, data)
        if self._disabled or self._client is None:
            return
        try:
            self._client.setex(self._key(session_id), ttl or self.ttl, json.dumps(data, default=str))
        except Exception as exc:
            logger.warning("Redis set failed: %s", exc)
            fallback_manager.redis_failed()
            self._client = None

    def _mem_get(self, session_id: str) -> dict[str, Any] | None:
        item = self._mem.get(session_id)
        if not item:
            return None
        expires, data = item
        if expires < time.time():
            self._mem.pop(session_id, None)
            return None
        return data

    def _mem_set(self, session_id: str, data: dict[str, Any]) -> None:
        self._mem[session_id] = (time.time() + self.ttl, data)


_cache: RedisCache | None = None


def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def reset_cache_for_tests(cache: RedisCache | None = None) -> RedisCache:
    global _cache
    _cache = cache if cache is not None else RedisCache(client=None)
    _cache.enable_memory_only()
    return _cache
