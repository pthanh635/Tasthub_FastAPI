from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.constants import CONSOLE_LOG_FORMAT, DEFAULT_LOG_LEVEL, UVICORN_LOGGERS

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Inject active request correlation ID from ContextVar into LogRecords."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = request_id_ctx_var.get()
        return True


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter producing structured logs for cloud/container observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        request_id = getattr(record, "request_id", None) or request_id_ctx_var.get()
        if request_id:
            log_obj["request_id"] = request_id

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(
    level: str = DEFAULT_LOG_LEVEL,
    *,
    json_format: bool = True,
) -> None:
    """Configure root and Uvicorn loggers with unified structured output."""
    resolved_level = getattr(logging, str(level).upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT))

    root_logger.addHandler(handler)

    # Route all Uvicorn loggers through the root handler so every log line shares one format
    for logger_name in UVICORN_LOGGERS:
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.setLevel(resolved_level)
        uv_logger.propagate = True
