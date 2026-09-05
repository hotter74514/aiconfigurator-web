from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import os
import sys
from collections.abc import Iterator
from typing import Any

from opentelemetry import trace

RUN_ID_ENV = "PORTAL_RUN_ID"
_run_id: ContextVar[str | None] = ContextVar("portal_run_id", default=None)
_HANDLER_MARKER = "_aiconfigurator_portal_json_handler"


class JsonLogFormatter(logging.Formatter):
    """Render one structured JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        structured = dict(getattr(record, "structured", {}))
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "event": structured.pop("event", record.getMessage()),
            "run_id": structured.pop("run_id", None) or get_run_id(),
            "trace_id": (
                format(span_context.trace_id, "032x")
                if span_context.is_valid
                else None
            ),
            "span_id": (
                format(span_context.span_id, "016x")
                if span_context.is_valid
                else None
            ),
        }
        payload.update(structured)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    """Configure one JSON stream handler for portal-owned loggers."""

    logger = logging.getLogger("aiconfigurator.portal")
    logger.setLevel(os.getenv("PORTAL_LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    if not any(getattr(handler, _HANDLER_MARKER, False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        setattr(handler, _HANDLER_MARKER, True)
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit a structured event without placing dynamic values in metric labels."""

    logger.log(level, event, extra={"structured": {"event": event, **fields}})


@contextmanager
def bind_run_id(run_id: object) -> Iterator[None]:
    token = _run_id.set(str(run_id))
    try:
        yield
    finally:
        _run_id.reset(token)


def get_run_id() -> str | None:
    return _run_id.get()
