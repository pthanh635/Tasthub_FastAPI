from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, cast

from redis.asyncio import Redis

from app.core.constants import (
    REDIS_CACHE_VERSION_KEY,
    REDIS_RECONNECT_INITIAL_DELAY_SECONDS,
    REDIS_RECONNECT_MAX_DELAY_SECONDS,
    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
    REDIS_SOCKET_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis adapter with bounded I/O and an unavailable-cache fallback."""

    def __init__(self, url: str, *, ttl_seconds: int) -> None:
        self._url = url
        self._ttl_seconds = ttl_seconds
        self._client: Redis | None = None
        self._available = False
        self._retry_delay = REDIS_RECONNECT_INITIAL_DELAY_SECONDS
        self._next_retry_at = 0.0
        self._connect_lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        return self._available and self._client is not None

    async def ensure_available(self) -> bool:
        if self.available:
            return True
        if time.monotonic() < self._next_retry_at:
            return False

        async with self._connect_lock:
            if self.available:
                return True
            if time.monotonic() < self._next_retry_at:
                return False
            client = Redis.from_url(
                self._url,
                decode_responses=False,
                socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
                socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            )
            try:
                await client.ping()
            except Exception:
                try:
                    await client.aclose()
                except Exception:
                    pass
                self._available = False
                self._client = None
                self._next_retry_at = time.monotonic() + self._retry_delay
                self._retry_delay = min(
                    self._retry_delay * 2,
                    REDIS_RECONNECT_MAX_DELAY_SECONDS,
                )
                logger.warning("Redis connection unavailable; cache requests will bypass it")
                return False

            self._client = client
            self._available = True
            self._retry_delay = REDIS_RECONNECT_INITIAL_DELAY_SECONDS
            self._next_retry_at = 0.0
            logger.info("Redis cache connected")
            return True

    async def connect(self) -> None:
        await self.ensure_available()

    async def _mark_unavailable(self) -> None:
        client = self._client
        self._client = None
        self._available = False
        self._next_retry_at = time.monotonic() + self._retry_delay
        self._retry_delay = min(
            self._retry_delay * 2,
            REDIS_RECONNECT_MAX_DELAY_SECONDS,
        )
        if client is not None:
            try:
                await client.aclose()
            except Exception:
                pass
        logger.warning("Redis operation failed; cache requests will bypass it")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None
        self._available = False
        self._next_retry_at = 0.0
        self._retry_delay = REDIS_RECONNECT_INITIAL_DELAY_SECONDS

    async def get(self, key: str) -> dict[str, Any] | None:
        if not await self.ensure_available():
            return None
        try:
            value = await self._client.get(key)  # type: ignore[union-attr]
        except Exception:
            await self._mark_unavailable()
            return None
        if value is None:
            return None
        try:
            decoded = json.loads(value)
            return cast(dict[str, Any], decoded)
        except (TypeError, ValueError):
            logger.warning("Failed to decode JSON cache value for key '%s'", key)
            return None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        if self._ttl_seconds == 0 or not await self.ensure_available():
            return
        try:
            await self._client.set(  # type: ignore[union-attr]
                key,
                json.dumps(value),
                ex=self._ttl_seconds,
            )
        except Exception:
            await self._mark_unavailable()

    async def increment_version(self) -> None:
        if not await self.ensure_available():
            return
        try:
            await self._client.incr(REDIS_CACHE_VERSION_KEY)  # type: ignore[union-attr]
        except Exception:
            await self._mark_unavailable()

    async def get_version(self) -> int:
        if not await self.ensure_available():
            return 0
        try:
            version = await self._client.get(REDIS_CACHE_VERSION_KEY)  # type: ignore[union-attr]
        except Exception:
            await self._mark_unavailable()
            return 0
        return int(version or 0)
