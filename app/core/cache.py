from __future__ import annotations

import json
import logging
from typing import Any, cast

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Small Redis adapter with an unavailable-cache fallback."""

    def __init__(self, url: str, *, ttl_seconds: int) -> None:
        self._url = url
        self._ttl_seconds = ttl_seconds
        self._client: Redis | None = None
        self._available = False

    @property
    def available(self) -> bool:
        return self._available and self._client is not None

    async def connect(self) -> None:
        self._client = Redis.from_url(self._url, decode_responses=False)
        try:
            await self._client.ping()
        except Exception as exc:
            logger.warning("Failed to connect to Redis at %s: %s", self._url, exc)
            await self.close()
        else:
            self._available = True

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None
        self._available = False

    async def get(self, key: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            value = await self._client.get(key)  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("Redis GET failed for key '%s': %s", key, exc)
            return None
        if value is None:
            return None
        try:
            decoded = json.loads(value)
            return cast(dict[str, Any], decoded)
        except (TypeError, ValueError) as exc:
            logger.warning("Failed to decode JSON cache value for key '%s': %s", key, exc)
            return None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        if not self.available or self._ttl_seconds == 0:
            return
        try:
            await self._client.set(  # type: ignore[union-attr]
                key,
                json.dumps(value),
                ex=self._ttl_seconds,
            )
        except Exception as exc:
            logger.warning("Redis SET failed for key '%s': %s", key, exc)
            return

    async def increment_version(self) -> None:
        if not self.available:
            return
        try:
            await self._client.incr("taskhub:cache:version")  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("Redis INCR failed for version key: %s", exc)
            return

    async def get_version(self) -> int:
        if not self.available:
            return 0
        try:
            version = await self._client.get("taskhub:cache:version")  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("Redis GET failed for version key: %s", exc)
            return 0
        return int(version or 0)
