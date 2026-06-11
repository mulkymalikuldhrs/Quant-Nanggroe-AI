"""Structured logging configuration for Quant Nanggroe AI.

Provides JSON-structured logging for production and human-readable
text logging for development. All log entries include timestamp,
level, module, and a structured message.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from quant_nanggroe.config.settings import get_settings


class StructuredFormatter(logging.Formatter):
    """Formatter that produces structured log records.

    In JSON mode each record is a single-line JSON object.
    In text mode records use a human-readable format.
    """

    def __init__(self, fmt: str = "json") -> None:
        super().__init__()
        self.fmt = fmt

    def format(self, record: logging.LogRecord) -> str:
        record.asctime = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        payload: dict[str, Any] = {
            "timestamp": record.asctime,
            "level": record.levelname,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self.formatException(record.exc_info)

        if self.fmt == "json":
            import json
            return json.dumps(payload, default=str)

        return (
            f"{record.asctime} | {record.levelname:<8} | "
            f"{record.module}:{record.funcName}:{record.lineno} — "
            f"{record.getMessage()}"
        )


def setup_logging(
    level: str | None = None,
    fmt: str | None = None,
) -> None:
    """Configure the root logger with structured output.

    Args:
        level: Override log level (defaults to settings.LOG_LEVEL).
        fmt: Override format style — "json" or "text" (defaults to settings.LOG_FORMAT).
    """
    settings = get_settings()
    log_level = level or settings.log_level
    log_fmt = fmt or settings.log_format

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter(fmt=log_fmt))
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger inheriting the root configuration.

    Args:
        name: Logger name — typically ``__name__`` of the calling module.

    Returns:
        Configured ``logging.Logger`` instance.
    """
    return logging.getLogger(f"quant_nanggroe.{name}")
