from __future__ import annotations

import asyncio
import io
import json
import logging
from collections.abc import Callable, Coroutine, Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.v1.dependencies import get_task_queue
from app.core.constants import UVICORN_LOGGERS
from app.core.database import get_db_session
from app.core.logging import JSONFormatter, RequestIdFilter, setup_logging
from app.core.messages import EmailMessages
from app.core.middleware import RequestContextMiddleware
from app.core.tasks import (
    TaskQueue,
    log_audit_event,
    mask_email,
    send_email_notification,
)
from app.main import app
from app.models.enums import AuditAction, AuditResource


@pytest.fixture(autouse=True)
def restore_logging_state() -> Generator[None, None, None]:
    """Snapshot and restore root and Uvicorn logger state so tests never leak handlers."""
    root = logging.getLogger()
    orig_root_level = root.level
    orig_root_handlers = list(root.handlers)

    uvicorn_snapshots: dict[str, tuple[int, list[logging.Handler], bool]] = {}
    for name in UVICORN_LOGGERS:
        uv_logger = logging.getLogger(name)
        uvicorn_snapshots[name] = (
            uv_logger.level,
            list(uv_logger.handlers),
            uv_logger.propagate,
        )

    try:
        yield
    finally:
        root.setLevel(orig_root_level)
        root.handlers.clear()
        root.handlers.extend(orig_root_handlers)

        for name, (lvl, handlers, propagate) in uvicorn_snapshots.items():
            uv_logger = logging.getLogger(name)
            uv_logger.setLevel(lvl)
            uv_logger.handlers.clear()
            uv_logger.handlers.extend(handlers)
            uv_logger.propagate = propagate


def test_json_formatter_produces_valid_json() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="Test log message with %s",
        args=("parameter",),
        exc_info=None,
    )
    record.request_id = "test-request-id-12345"

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test log message with parameter"
    assert parsed["request_id"] == "test-request-id-12345"
    assert "timestamp" in parsed


def test_setup_logging_configures_root_and_uvicorn_loggers() -> None:
    # Pre-populate dummy handler on uvicorn logger to simulate Uvicorn's default config
    uv_main = logging.getLogger("uvicorn")
    uv_main.addHandler(logging.NullHandler())
    uv_main.propagate = False

    setup_logging(level="DEBUG", json_format=False)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1

    setup_logging(level="INFO", json_format=True)
    assert root.level == logging.INFO
    assert isinstance(root.handlers[0].formatter, JSONFormatter)

    stream = io.StringIO()
    json_handler = logging.StreamHandler(stream)
    json_handler.addFilter(RequestIdFilter())
    json_handler.setFormatter(JSONFormatter())
    root.handlers = [json_handler]

    for logger_name in UVICORN_LOGGERS:
        uv_logger = logging.getLogger(logger_name)
        assert uv_logger.handlers == []
        assert uv_logger.propagate is True
        uv_logger.info("event from %s", logger_name)

    lines = [json.loads(line) for line in stream.getvalue().strip().splitlines()]
    assert [entry["logger"] for entry in lines] == list(UVICORN_LOGGERS)


async def test_request_id_propagates_to_json_logs_via_middleware() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JSONFormatter())

    route_logger = logging.getLogger("app.test_request_context")
    route_logger.setLevel(logging.INFO)
    route_logger.addHandler(handler)
    route_logger.propagate = False

    mini_app = FastAPI()
    mini_app.add_middleware(RequestContextMiddleware)

    @mini_app.get("/ping")
    async def ping() -> dict[str, str]:
        route_logger.info("Handling ping endpoint")
        return {"ok": "true"}

    try:
        transport = ASGITransport(app=mini_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                "/ping",
                headers={"X-Request-ID": "trace-corr-998877"},
            )
        assert resp.status_code == 200
        assert resp.headers["X-Request-ID"] == "trace-corr-998877"

        logged = json.loads(stream.getvalue().strip())
        assert logged["message"] == "Handling ping endpoint"
        assert logged["request_id"] == "trace-corr-998877"
    finally:
        route_logger.removeHandler(handler)


async def test_task_queue_enqueue_and_wait_all() -> None:
    queue = TaskQueue()
    results: list[str] = []

    async def simple_task(val: str) -> None:
        await asyncio.sleep(0)
        results.append(val)

    queue.enqueue(simple_task, "item-1")
    queue.enqueue(simple_task, "item-2")

    await queue.wait_all(timeout_seconds=1.0)
    assert sorted(results) == ["item-1", "item-2"]


async def test_task_queue_handles_exception_gracefully(
    caplog: pytest.LogCaptureFixture,
) -> None:
    queue = TaskQueue()

    async def failing_task() -> None:
        raise ValueError("Simulated background error")

    with caplog.at_level(logging.ERROR):
        queue.enqueue(failing_task)
        await queue.wait_all(timeout_seconds=1.0)

    assert "Background task failed with exception" in caplog.text


async def test_background_audit_and_email_tasks_do_not_log_pii(
    caplog: pytest.LogCaptureFixture,
) -> None:
    uid = uuid4()
    assert mask_email("alice@example.com") == "a***@example.com"

    with caplog.at_level(logging.INFO):
        await send_email_notification(
            "alice@example.com",
            EmailMessages.WELCOME_SUBJECT,
            EmailMessages.WELCOME_BODY_TEMPLATE.format(full_name="Alice SecretName"),
            user_id=uid,
        )
        await log_audit_event(
            AuditAction.USER_REGISTERED,
            user_id=uid,
            resource=AuditResource.USERS,
        )

    assert f"user_id={uid}" in caplog.text
    assert "AUDIT_EVENT: action=USER_REGISTERED" in caplog.text
    assert "alice@example.com" not in caplog.text
    assert "Alice SecretName" not in caplog.text


async def test_register_enqueues_background_tasks_without_pii_and_survives_task_failure(
    session_factory: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify /auth/register enqueues tasks via DI, logs no PII, and returns 201 on task error."""
    recorded_calls: list[str] = []
    custom_queue = TaskQueue()

    class RecordingQueue(TaskQueue):
        def enqueue(
            self,
            coro_func: Callable[..., Coroutine[Any, Any, Any]],
            *args: Any,
            **kwargs: Any,
        ) -> asyncio.Task[None]:
            recorded_calls.append(coro_func.__name__)
            return super().enqueue(coro_func, *args, **kwargs)

    recording_queue = RecordingQueue()

    async def _override_db() -> Any:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_task_queue] = lambda: recording_queue
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            with caplog.at_level(logging.INFO):
                resp = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "newuser_pii@example.com",
                        "password": "StrongPassword123!",
                        "full_name": "Nguyen Van Private",
                    },
                )
                await recording_queue.wait_all(timeout_seconds=1.0)

            assert resp.status_code == 201
            created_id = resp.json()["id"]
            assert recorded_calls == ["send_email_notification", "log_audit_event"]
            assert created_id in caplog.text
            assert "newuser_pii@example.com" not in caplog.text
            assert "Nguyen Van Private" not in caplog.text

            # Now simulate failing background tasks: register MUST still return 201
            class FailingQueue(TaskQueue):
                def enqueue(
                    self,
                    coro_func: Callable[..., Coroutine[Any, Any, Any]],
                    *args: Any,
                    **kwargs: Any,
                ) -> asyncio.Task[None]:
                    async def _boom() -> None:
                        raise RuntimeError(f"Broker failure in {coro_func.__name__}")

                    return custom_queue.enqueue(_boom)

            app.dependency_overrides[get_task_queue] = FailingQueue
            with caplog.at_level(logging.ERROR):
                resp_fail_bg = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "resilient_user@example.com",
                        "password": "StrongPassword123!",
                        "full_name": "Resilient User",
                    },
                )
                await custom_queue.wait_all(timeout_seconds=1.0)

            assert resp_fail_bg.status_code == 201
            assert "Broker failure in send_email_notification" in caplog.text
    finally:
        app.dependency_overrides.clear()
