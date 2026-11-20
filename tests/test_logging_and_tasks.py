from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

import pytest

from app.core.logging import JSONFormatter, setup_logging
from app.core.tasks import TaskQueue, log_audit_event, send_email_notification


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
    record.request_id = "test-request-id-12345"  # type: ignore[attr-defined]

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test log message with parameter"
    assert parsed["request_id"] == "test-request-id-12345"
    assert "timestamp" in parsed


def test_setup_logging_configures_root_logger() -> None:
    setup_logging(level="DEBUG", json_format=False)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) >= 1

    setup_logging(level="INFO", json_format=True)
    root = logging.getLogger()
    assert root.level == logging.INFO
    assert isinstance(root.handlers[0].formatter, JSONFormatter)


async def test_task_queue_enqueue_and_wait_all() -> None:
    queue = TaskQueue()
    results: list[str] = []

    async def simple_task(val: str) -> None:
        await asyncio.sleep(0.01)
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
        await asyncio.sleep(0.01)
        raise ValueError("Simulated background error")

    with caplog.at_level(logging.ERROR):
        queue.enqueue(failing_task)
        await queue.wait_all(timeout_seconds=1.0)

    assert "Background task failed with exception" in caplog.text


async def test_background_audit_and_email_tasks(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        await send_email_notification("user@example.com", "Subject", "Body")
        await log_audit_event("TEST_ACTION", user_id=uuid4(), resource="test")

    assert "EMAIL_NOTIFICATION: to=user@example.com" in caplog.text
    assert "AUDIT_EVENT: action=TEST_ACTION" in caplog.text
