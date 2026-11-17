from __future__ import annotations

import hashlib
import re
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.cache import RedisCache
from app.core.constants import (
    AUTH_PATH_PREFIX,
    AUTHORIZATION_HEADER,
    CACHE_STATUS_HEADER,
    CACHEABLE_METHODS,
    HEALTH_PATH,
    HTTP_ERROR_STATUS_THRESHOLD,
    HTTP_OK_STATUS,
    JSON_MEDIA_TYPE,
    REDIS_CACHE_KEY_PREFIX,
    REQUEST_ID_HEADER,
    REQUEST_ID_MAX_LENGTH,
    REQUEST_PROCESS_TIME_HEADER,
    CacheStatus,
)

REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


def _sanitize_request_id(raw_id: str | None) -> str:
    """Validate request ID from client header or generate a fresh UUID4.

    Accepts alphanumeric characters, hyphens, and underscores up to 64 chars.
    Prevents header injection and oversized values.
    """
    if raw_id and len(raw_id) <= REQUEST_ID_MAX_LENGTH and REQUEST_ID_REGEX.match(raw_id):
        return raw_id
    return str(uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a stable request ID and processing duration to every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _sanitize_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[REQUEST_PROCESS_TIME_HEADER] = f"{elapsed_ms:.2f}"
        return response


class RedisCacheMiddleware(BaseHTTPMiddleware):
    """Cache successful JSON GET responses and invalidate them after writes."""

    def __init__(self, app: ASGIApp, cache: RedisCache) -> None:
        super().__init__(app)
        self._cache = cache

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path
        is_auth_path = path.startswith(AUTH_PATH_PREFIX) or "/auth/" in path
        is_sensitive = (
            path == HEALTH_PATH
            or is_auth_path
            or AUTHORIZATION_HEADER in request.headers
        )
        if is_sensitive:
            response = await call_next(request)
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        if not await self._cache.ensure_available():
            response = await call_next(request)
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        if request.method not in CACHEABLE_METHODS:
            response = await call_next(request)
            if response.status_code < HTTP_ERROR_STATUS_THRESHOLD:
                await self._cache.increment_version()
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        key = await self._cache_key(request)
        cached = await self._cache.get(key)
        if cached is not None:
            return Response(
                content=cached["body"].encode("utf-8"),
                status_code=cached["status_code"],
                media_type=cached["media_type"],
                headers={CACHE_STATUS_HEADER: CacheStatus.HIT},
            )

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if response.status_code != HTTP_OK_STATUS or JSON_MEDIA_TYPE not in content_type:
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        # BaseHTTPMiddleware returns _StreamingResponse; consume body_iterator directly
        body = b"".join(
            [chunk async for chunk in response.body_iterator]
        )
        await self._cache.set(
            key,
            {
                "body": body.decode("utf-8"),
                "media_type": content_type.split(";", 1)[0],
                "status_code": response.status_code,
            },
        )
        response_headers = dict(response.headers)
        response_headers[CACHE_STATUS_HEADER] = CacheStatus.MISS
        response_headers.pop("content-length", None)
        return Response(
            content=body,
            status_code=response.status_code,
            media_type=content_type.split(";", 1)[0],
            headers=response_headers,
        )

    async def _cache_key(self, request: Request) -> str:
        auth = request.headers.get("Authorization", "")
        auth_fingerprint = hashlib.sha256(auth.encode()).hexdigest()
        version = await self._cache.get_version()
        raw_key = (
            f"{version}:{request.method}:{request.url.path}?"
            f"{request.url.query}:{auth_fingerprint}"
        )
        return f"{REDIS_CACHE_KEY_PREFIX}{hashlib.sha256(raw_key.encode()).hexdigest()}"
