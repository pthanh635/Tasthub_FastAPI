from __future__ import annotations

import hashlib
import re
import time
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse
from starlette.types import ASGIApp

from app.core.cache import RedisCache
from app.core.constants import (
    AUTH_PATH_PREFIX,
    AUTHORIZATION_HEADER,
    CACHE_STATUS_HEADER,
    CACHEABLE_METHODS,
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
CACHE_MAX_BUFFER_BYTES = 1024 * 1024
NEVER_CACHE_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})


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

    def __init__(
        self,
        app: ASGIApp,
        cache: RedisCache,
        public_get_paths: frozenset[str] = frozenset(),
    ) -> None:
        super().__init__(app)
        self._cache = cache
        self._public_get_paths = public_get_paths

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path
        is_auth_path = (
            path == AUTH_PATH_PREFIX
            or path.startswith(f"{AUTH_PATH_PREFIX}/")
            or path.endswith("/auth")
            or "/auth/" in path
        )

        # Handle write operations (POST, PUT, PATCH, DELETE, etc.) first
        if request.method not in CACHEABLE_METHODS:
            response = await call_next(request)
            if not is_auth_path and response.status_code < HTTP_ERROR_STATUS_THRESHOLD:
                await self._cache.increment_version()
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        # Non-cacheable endpoints or authenticated requests bypass cache
        has_authentication = (
            AUTHORIZATION_HEADER in request.headers or "cookie" in request.headers
        )
        if (
            path in NEVER_CACHE_PATHS
            or path.startswith(("/docs/", "/redoc/"))
            or is_auth_path
            or has_authentication
        ):
            response = await call_next(request)
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        if request.method != "GET" or path not in self._public_get_paths:
            response = await call_next(request)
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        if not await self._cache.ensure_available():
            response = await call_next(request)
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        key = await self._cache_key(request)
        cached = await self._cache.get(key)
        if cached is not None:
            headers = [
                (name.encode("latin-1"), value.encode("latin-1"))
                for name, value in cached.get("headers", [])
                if name.lower() != CACHE_STATUS_HEADER.lower()
            ]
            return self._response_with_raw_headers(
                cached["body"].encode("utf-8"),
                cached["status_code"],
                headers,
                CacheStatus.HIT,
            )

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if response.status_code != HTTP_OK_STATUS or JSON_MEDIA_TYPE not in content_type:
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        if any(name.lower() == b"set-cookie" for name, _ in response.raw_headers):
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response

        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is None:
            response.headers[CACHE_STATUS_HEADER] = CacheStatus.BYPASS
            return response
        if not any(name.lower() == b"content-length" for name, _ in response.raw_headers):
            streamed = StreamingResponse(body_iterator, status_code=response.status_code)
            streamed.raw_headers = self._headers_with_cache_status(
                response.raw_headers, CacheStatus.BYPASS
            )
            return streamed

        chunks: list[bytes] = []
        size = 0
        async for chunk in body_iterator:
            chunks.append(chunk)
            size += len(chunk)
            if size > CACHE_MAX_BUFFER_BYTES:
                async def replay() -> AsyncIterator[bytes]:
                    for buffered_chunk in chunks:
                        yield buffered_chunk
                    async for remaining_chunk in body_iterator:
                        yield remaining_chunk

                streamed = StreamingResponse(replay(), status_code=response.status_code)
                streamed.raw_headers = self._headers_with_cache_status(
                    response.raw_headers, CacheStatus.BYPASS
                )
                return streamed

        body = b"".join(chunks)
        if any(
            name.lower() == b"content-encoding" and value.lower() != b"identity"
            for name, value in response.raw_headers
        ):
            return self._response_with_raw_headers(
                body,
                response.status_code,
                response.raw_headers,
                CacheStatus.BYPASS,
            )

        await self._cache.set(
            key,
            {
                "body": body.decode("utf-8"),
                "media_type": content_type.split(";", 1)[0],
                "status_code": response.status_code,
                "headers": [
                    (name.decode("latin-1"), value.decode("latin-1"))
                    for name, value in response.raw_headers
                ],
            },
        )
        return self._response_with_raw_headers(
            body,
            response.status_code,
            response.raw_headers,
            CacheStatus.MISS,
        )

    @staticmethod
    def _headers_with_cache_status(
        raw_headers: list[tuple[bytes, bytes]], status: CacheStatus
    ) -> list[tuple[bytes, bytes]]:
        return [
            (name, value)
            for name, value in raw_headers
            if name.lower() != CACHE_STATUS_HEADER.lower().encode()
        ] + [
            (CACHE_STATUS_HEADER.lower().encode(), status.value.encode()),
        ]

    @staticmethod
    def _response_with_raw_headers(
        body: bytes,
        status_code: int,
        raw_headers: list[tuple[bytes, bytes]],
        cache_status: CacheStatus,
    ) -> Response:
        response = Response(content=body, status_code=status_code)
        response.raw_headers = [
            (name, value)
            for name, value in raw_headers
            if name.lower() not in {b"content-length", CACHE_STATUS_HEADER.lower().encode()}
        ]
        response.raw_headers.extend(
            [
                (b"content-length", str(len(body)).encode()),
                (CACHE_STATUS_HEADER.lower().encode(), cache_status.value.encode()),
            ]
        )
        return response

    async def _cache_key(self, request: Request) -> str:
        version = await self._cache.get_version()
        raw_key = f"{version}:{request.method}:{request.url.path}?{request.url.query}"
        return f"{REDIS_CACHE_KEY_PREFIX}{hashlib.sha256(raw_key.encode()).hexdigest()}"
