from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from httpx import ASGITransport, AsyncClient

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
) -> AsyncGenerator[AsyncClient, None]:
    test_app = FastAPI()
    test_app.add_middleware(
        RedisCacheMiddleware,
        cache=fake_redis_cache,
        public_get_paths=frozenset({"/items", "/cookies", "/large", "/stream"}),
    )
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

    @test_app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/private")
    async def private() -> dict[str, str]:
        return {"secret": "response"}

    @test_app.get("/cookies")
    async def cookies() -> JSONResponse:
        response = JSONResponse({"ok": True})
        response.raw_headers.extend(
            [(b"set-cookie", b"first=1"), (b"set-cookie", b"second=2")]
        )
        return response

    @test_app.get("/large")
    async def large() -> JSONResponse:
        return JSONResponse({"payload": "x" * (1024 * 1024 + 32)})

    @test_app.get("/stream")
    async def stream() -> StreamingResponse:
        async def chunks() -> AsyncGenerator[bytes, None]:
            yield b'{"part":'
            yield b'"one"}'

        return StreamingResponse(chunks(), media_type="application/json")

    @test_app.post("/api/v1/auth/refresh")
    async def refresh() -> dict[str, str]:
        return {"status": "refreshed"}

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
    assert "Redis connection unavailable" in caplog.text
    assert "nonexistent-host" not in caplog.text


async def test_redis_connection_logs_do_not_include_url_or_password(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import app.core.cache as cache_module

    class FailingRedisClient(FakeRedisClient):
        async def ping(self) -> bool:
            raise ConnectionError("redis://user:private-password@redis.internal")

    monkeypatch.setattr(
        cache_module.Redis,
        "from_url",
        lambda _url, **_kwargs: FailingRedisClient(),
    )
    cache = RedisCache(
        "redis://user:private-password@redis.internal:6379/0", ttl_seconds=30
    )
    with caplog.at_level(logging.WARNING):
        await cache.connect()
    assert "private-password" not in caplog.text
    assert "redis.internal" not in caplog.text


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

    assert "Redis operation failed; cache requests will bypass it" in caplog.text


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


async def test_public_cache_hit(cached_test_client: AsyncClient) -> None:
    first = await cached_test_client.get("/items")
    second = await cached_test_client.get("/items")
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.json()["views"] == 1


async def test_multiple_set_cookie_headers_are_preserved(
    cached_test_client: AsyncClient,
) -> None:
    response = await cached_test_client.get("/cookies")
    assert response.headers.get_list("set-cookie") == ["first=1", "second=2"]
    assert response.headers["X-Cache"] == "BYPASS"


async def test_large_json_response_replays_all_bytes(cached_test_client: AsyncClient) -> None:
    response = await cached_test_client.get("/large")
    assert response.status_code == 200
    assert len(response.json()["payload"]) == 1024 * 1024 + 32
    assert response.headers["X-Cache"] == "BYPASS"


async def test_streaming_json_response_is_replayed(cached_test_client: AsyncClient) -> None:
    response = await cached_test_client.get("/stream")
    assert response.content == b'{"part":"one"}'
    assert response.headers["X-Cache"] == "BYPASS"


async def test_authentication_cookie_bypasses_cache(cached_test_client: AsyncClient) -> None:
    first = await cached_test_client.get("/items")
    with_cookie = await cached_test_client.get(
        "/items", headers={"Cookie": "access_token=token"}
    )
    next_public = await cached_test_client.get("/items")
    assert first.headers["X-Cache"] == "MISS"
    assert with_cookie.headers["X-Cache"] == "BYPASS"
    assert with_cookie.json()["views"] == 2
    assert next_public.headers["X-Cache"] == "HIT"
    assert next_public.json()["views"] == 1


async def test_expired_token_never_uses_cached_response(
    fake_redis_cache: RedisCache,
) -> None:
    test_app = FastAPI()
    token_state = {"expired": False, "checks": 0}

    async def authenticate(authorization: str | None = Header(default=None)) -> None:
        token_state["checks"] += 1
        if authorization != "Bearer temporary" or token_state["expired"]:
            raise HTTPException(status_code=401, detail="Invalid token")

    test_app.add_middleware(
        RedisCacheMiddleware,
        cache=fake_redis_cache,
        public_get_paths=frozenset({"/protected"}),
    )

    @test_app.get("/protected", dependencies=[Depends(authenticate)])
    async def protected() -> dict[str, str]:
        return {"secret": "fresh"}

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        success = await client.get("/protected", headers={"Authorization": "Bearer temporary"})
        token_state["expired"] = True
        expired = await client.get(
            "/protected", headers={"Authorization": "Bearer temporary"}
        )

    assert success.status_code == 200
    assert expired.status_code == 401
    assert token_state["checks"] == 2


async def test_cache_bypass_for_non_json_and_errors(
    cached_test_client: AsyncClient,
) -> None:
    plain_res = await cached_test_client.get("/plain")
    assert plain_res.status_code == 200
    assert plain_res.headers["X-Cache"] == "BYPASS"

    error_res = await cached_test_client.get("/error")
    assert error_res.status_code == 400
    assert error_res.headers["X-Cache"] == "BYPASS"


async def test_cache_bypasses_health_sensitive_and_authorized_requests(
    cached_test_client: AsyncClient,
    fake_redis_cache: RedisCache,
) -> None:
    health_response = await cached_test_client.get("/health")
    private_response = await cached_test_client.get(
        "/private", headers={"Authorization": "Bearer access-token"}
    )
    refresh_response = await cached_test_client.post("/api/v1/auth/refresh")

    assert health_response.headers["X-Cache"] == "BYPASS"
    assert private_response.headers["X-Cache"] == "BYPASS"
    assert refresh_response.headers["X-Cache"] == "BYPASS"
    assert await fake_redis_cache.get_version() == 0


async def test_cache_reconnects_after_backoff_and_sets_socket_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.cache as cache_module

    cache = RedisCache("redis://user:password@redis.internal:6379/0", ttl_seconds=60)
    created_kwargs: list[dict[str, Any]] = []

    def make_client(url: str, **kwargs: Any) -> FakeRedisClient:
        assert url.startswith("redis://user:")
        created_kwargs.append(kwargs)
        return FakeRedisClient()

    monkeypatch.setattr(cache_module.Redis, "from_url", make_client)
    cache._next_retry_at = time.monotonic() + 60
    assert await cache.get("key") is None
    assert created_kwargs == []

    cache._next_retry_at = 0
    assert await cache.get("key") is None
    assert cache.available
    assert created_kwargs[0]["socket_connect_timeout"] > 0
    assert created_kwargs[0]["socket_timeout"] > 0
    await cache.close()


async def test_unavailable_redis_bypasses_cache_and_returns_api_response(
    cached_test_client: AsyncClient,
    fake_redis_cache: RedisCache,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.cache as cache_module

    class UnavailableRedisClient(FakeRedisClient):
        async def ping(self) -> bool:
            raise ConnectionError("Redis is offline")

    monkeypatch.setattr(
        cache_module.Redis,
        "from_url",
        lambda _url, **_kwargs: UnavailableRedisClient(),
    )
    fake_redis_cache._client = None
    fake_redis_cache._available = False

    response = await asyncio.wait_for(cached_test_client.get("/items"), timeout=1)

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "BYPASS"
    assert response.json()["items"] == ["item1", "item2"]
