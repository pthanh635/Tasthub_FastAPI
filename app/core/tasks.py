from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


async def log_audit_event(
    action: str,
    *,
    user_id: UUID | str | None = None,
    resource: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Simulate recording an audit log event asynchronously."""
    await asyncio.sleep(0.01)
    logger.info(
        "AUDIT_EVENT: action=%s user_id=%s resource=%s details=%s",
        action,
        user_id,
        resource,
        details or {},
    )


async def send_email_notification(
    to_email: str,
    subject: str,
    content: str,
) -> None:
    """Simulate sending an asynchronous email notification (e.g., welcome, task assignment)."""
    await asyncio.sleep(0.01)
    logger.info(
        "EMAIL_NOTIFICATION: to=%s subject='%s' content='%s'",
        to_email,
        subject,
        content,
    )


class TaskQueue:
    """Lightweight in-memory async task runner/queue with graceful shutdown support."""

    def __init__(self) -> None:
        self._pending_tasks: set[asyncio.Task[Any]] = set()

    def enqueue(
        self,
        coro_func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> asyncio.Task[Any]:
        """Schedule a background coroutine to run safely without blocking the request."""
        task: asyncio.Task[Any] = asyncio.create_task(coro_func(*args, **kwargs))
        self._pending_tasks.add(task)
        task.add_done_callback(self._on_task_done)
        return task

    def _on_task_done(self, task: asyncio.Task[Any]) -> None:
        self._pending_tasks.discard(task)
        if not task.cancelled():
            exc = task.exception()
            if exc:
                logger.error("Background task failed with exception: %s", exc, exc_info=exc)

    async def wait_all(self, timeout_seconds: float = 5.0) -> None:
        """Wait for all pending tasks to complete during application graceful shutdown."""
        if not self._pending_tasks:
            return
        logger.info(
            "Waiting for %d pending background tasks to finish...",
            len(self._pending_tasks),
        )
        try:
            async with asyncio.timeout(timeout_seconds):
                await asyncio.gather(*self._pending_tasks, return_exceptions=True)
        except TimeoutError:
            logger.warning(
                "Background tasks timed out after %.1fs, cancelling...",
                timeout_seconds,
            )
            for task in self._pending_tasks:
                task.cancel()


background_queue = TaskQueue()
