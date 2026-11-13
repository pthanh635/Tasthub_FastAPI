from __future__ import annotations

import logging
import uuid
from typing import Any
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from httpx import ASGITransport, AsyncClient
import pytest

from app.core.cache import RedisCache
from app.core.middleware import (
    RedisCacheMiddleware,
    RequestContextMiddleware,
    _sanitize_request_id,
)


class FakeRedisClient:
    """In-memory Redis fake for testing caching behaviors."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.fail_get = False
        self.fail_set = False
        self.fail_incr = False

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        if self.fail_get:
            raise ConnectionError("Simulated Redis GET error")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        if self.fail_set:
            raise ConnectionError("Simulated Redis SET error")
        self.store[key] = value
        return True

    async def incr(self, key: str) -> int:
        if self.fail_incr:
            raise ConnectionError("Simulated Redis INCR error")
        val = int(self.store.get(key, 0)) + 1
        self.store[key] = str(val)
        return val

    async def aclose(self) -> None:
        pass


@pytest.fixture
def fake_redis_cache() -> RedisCache:
    cache = RedisCache("redis://localhost:6379/0", ttl_seconds=60)
    cache._client = FakeRedisClient()  # type: ignore[assignment]
    cache._available = True
    return cache


@pytest.fixture
async def cached_test_client(
    fake_redis_cache: RedisCache,
) -> AsyncClient:
    test_app = FastAPI()
    test_app.add_middleware(RedisCacheMiddleware, cache=fake_redis_cache)
    test_app.add_middleware(RequestContextMiddleware)

    counter = {"views": 0}

    @test_app.get("/items")
    async def get_items() -> dict[str, Any]:
        counter["views"] += 1
        return {"items": ["item1", "item2"], "views": counter["views"]}

    @test_app.post("/items")
    async def create_item() -> dict[str, str]:
        return {"status": "created"}

    @test_app.get("/plain")
    async def get_plain() -> PlainTextResponse:
        return PlainTextResponse("not json")

    @test_app.get("/error")
    async def get_error() -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": "bad request"})

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# --- RequestContextMiddleware tests ---


def test_sanitize_request_id_valid() -> None:
    valid_id = "req_12345-abc"
    assert _sanitize_request_id(valid_id) == valid_id


def test_sanitize_request_id_invalid_generates_uuid() -> None:
    # Contains invalid characters (newlines, spaces, script tag)
    bad_id = "invalid\r\n<script>"
    sanitized = _sanitize_request_id(bad_id)
    assert sanitized != bad_id
    uuid.UUID(sanitized)  # Must be a valid UUID4 string


def test_sanitize_request_id_too_long_generates_uuid() -> None:
    too_long = "a" * 65
    sanitized = _sanitize_request_id(too_long)
    assert sanitized != too_long
    uuid.UUID(sanitized)


def test_sanitize_request_id_empty_generates_uuid() -> None:
    sanitized = _sanitize_request_id(None)
    uuid.UUID(sanitized)


async def test_request_id_custom_valid_header(async_client: AsyncClient) -> None:
    valid_custom_id = "custom-trace-id-12345"
    response = await async_client.get(
        "/health",
        headers={"X-Request-ID": valid_custom_id},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == valid_custom_id
    assert "X-Process-Time-Ms" in response.headers


async def test_request_id_invalid_header_is_sanitized(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/health",
        headers={"X-Request-ID": "bad\r\nheader value <script>"},
    )
    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert "bad" not in request_id
    assert "<script>" not in request_id
    uuid.UUID(request_id)


# --- RedisCache warning logging tests ---


async def test_redis_cache_connect_failure_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cache = RedisCache("redis://nonexistent-host:9999/0", ttl_seconds=60)
    with caplog.at_level(logging.WARNING):
        await cache.connect()
    assert not cache.available
    assert "Failed to connect to Redis" in caplog.text


async def test_redis_cache_operations_log_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cache = RedisCache("redis://localhost:6379/0", ttl_seconds=60)
    fake_client = FakeRedisClient()
    fake_client.fail_get = True
    fake_client.fail_set = True
    fake_client.fail_incr = True
    cache._client = fake_client  # type: ignore[assignment]
    cache._available = True

    with caplog.at_level(logging.WARNING):
        assert await cache.get("test_key") is None
        await cache.set("test_key", {"foo": "bar"})
        await cache.increment_version()
        assert await cache.get_version() == 0

    assert "Redis GET failed for key 'test_key'" in caplog.text
    assert "Redis SET failed for key 'test_key'" in caplog.text
    assert "Redis INCR failed for version key" in caplog.text
    assert "Redis GET failed for version key" in caplog.text


# --- RedisCacheMiddleware MISS -> HIT -> Invalidation tests ---


async def test_cache_miss_then_hit_then_invalidation(
    cached_test_client: AsyncClient,
) -> None:
    # 1. First GET: cache MISS (consumed from body_iterator without AttributeError)
    res1 = await cached_test_client.get("/items")
    assert res1.status_code == 200
    assert res1.headers["X-Cache"] == "MISS"
    data1 = res1.json()
    assert data1["items"] == ["item1", "item2"]
    assert data1["views"] == 1

    # 2. Second GET: cache HIT (returned from cache without incrementing views)
    res2 = await cached_test_client.get("/items")
    assert res2.status_code == 200
    assert res2.headers["X-Cache"] == "HIT"
    data2 = res2.json()
    assert data2["items"] == ["item1", "item2"]
    assert data2["views"] == 1  # Unchanged because cached

    # 3. Write request: POST /items invalidates cache by incrementing version
    res_post = await cached_test_client.post("/items")
    assert res_post.status_code == 200
    assert res_post.headers["X-Cache"] == "BYPASS"

    # 4. Third GET: cache MISS again because version incremented
    res3 = await cached_test_client.get("/items")
    assert res3.status_code == 200
    assert res3.headers["X-Cache"] == "MISS"
    data3 = res3.json()
    assert data3["views"] == 2  # Incremented because handler was executed


async def test_cache_bypass_for_non_json_and_errors(
    cached_test_client: AsyncClient,
) -> None:
    plain_res = await cached_test_client.get("/plain")
    assert plain_res.status_code == 200
    assert plain_res.headers["X-Cache"] == "BYPASS"

    error_res = await cached_test_client.get("/error")
    assert error_res.status_code == 400
    assert error_res.headers["X-Cache"] == "BYPASS"
