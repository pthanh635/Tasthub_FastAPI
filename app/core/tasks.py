from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from app.core.constants import DEFAULT_TASK_QUEUE_SHUTDOWN_TIMEOUT_SECONDS
from app.models.enums import AuditAction, AuditResource

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """Mask email address to avoid leaking PII into centralized logs."""
    cleaned = email.strip()
    local_part, separator, domain = cleaned.partition("@")
    if not separator or not local_part or not domain:
        return "***"
    return f"{local_part[0]}***@{domain}"


async def log_audit_event(
    action: AuditAction,
    *,
    user_id: UUID,
    resource: AuditResource,
) -> None:
    """Record a structured audit event without exposing PII."""
    logger.info(
        "AUDIT_EVENT: action=%s user_id=%s resource=%s",
        action.value,
        user_id,
        resource.value,
    )


async def send_email_notification(
    to_email: str,
    subject: str,
    content: str,
    *,
    user_id: UUID | None = None,
) -> None:
    """Simulate dispatching an asynchronous email notification without logging PII."""
    _ = (subject, content)
    recipient_ref = (
        f"user_id={user_id}"
        if user_id is not None
        else f"recipient={mask_email(to_email)}"
    )
    logger.info("EMAIL_NOTIFICATION: %s status=dispatched", recipient_ref)


class TaskQueue:
    """In-memory async task queue managed via FastAPI lifespan and Dependency Injection."""

    def __init__(self) -> None:
        self._pending_tasks: set[asyncio.Task[None]] = set()

    def enqueue(
        self,
        coro_func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> asyncio.Task[None]:
        """Schedule a background coroutine safely so task errors never fail the caller."""

        async def _runner() -> None:
            try:
                await coro_func(*args, **kwargs)
            except Exception as exc:
                logger.error(
                    "Background task failed with exception: %s",
                    exc,
                    exc_info=exc,
                )

        task: asyncio.Task[None] = asyncio.create_task(_runner())
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)
        return task

    async def wait_all(
        self,
        timeout_seconds: float = DEFAULT_TASK_QUEUE_SHUTDOWN_TIMEOUT_SECONDS,
    ) -> None:
        """Wait for pending background tasks to finish during graceful shutdown."""
        if not self._pending_tasks:
            return
        pending_snapshot = tuple(self._pending_tasks)
        logger.info(
            "Waiting for %d pending background tasks to finish...",
            len(pending_snapshot),
        )
        try:
            async with asyncio.timeout(timeout_seconds):
                await asyncio.gather(*pending_snapshot, return_exceptions=True)
        except TimeoutError:
            logger.warning(
                "Background tasks timed out after %.1fs, cancelling...",
                timeout_seconds,
            )
            for task in pending_snapshot:
                task.cancel()
