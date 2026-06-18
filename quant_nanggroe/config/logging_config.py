"""
Structured logging configuration for Quant Nanggroe AI.

Provides JSON-formatted logs for production and human-readable logs for development.
Falls back to standard library logging when structlog is not installed.
Includes PII redaction to prevent leaking sensitive data in logs.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

try:
    import structlog
except ImportError:
    structlog = None


def _get_pii_redaction():
    """Lazy import of PII redaction to avoid circular imports.

    The import chain logging_config → core.pii_redaction → core.__init__
    can cause circular imports at module load time. By deferring the import
    until setup_logging() is called, all modules are already loaded.
    """
    from quant_nanggroe.core.pii_redaction import PIIRedactionFilter, pii_redaction_processor
    return PIIRedactionFilter, pii_redaction_processor


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
) -> None:
    """
    Configure structured logging for the application.

    Uses structlog when available for JSON-formatted structured logs.
    Falls back to standard library logging otherwise.
    PII redaction is automatically wired into both paths.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format ('json' for production, 'console' for development)
        log_file: Optional file path for log output
    """
    if structlog is not None:
        _setup_structlog(level=level, format_type=format_type, log_file=log_file)
    else:
        _setup_stdlib_logging(level=level, format_type=format_type, log_file=log_file)


def _setup_structlog(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
) -> None:
    """Configure structlog-based structured logging."""
    # Lazy import PII redaction to avoid circular imports
    try:
        PIIRedactionFilter, pii_redaction_processor = _get_pii_redaction()
    except ImportError:
        PIIRedactionFilter = None
        pii_redaction_processor = None

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    # Add PII redaction filter to root handler
    if PIIRedactionFilter is not None:
        for handler in logging.getLogger().handlers:
            handler.addFilter(PIIRedactionFilter())

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add PII redaction processor to structlog chain
    if pii_redaction_processor is not None:
        shared_processors.append(pii_redaction_processor)

    processors = list(shared_processors)

    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        if PIIRedactionFilter is not None:
            file_handler.addFilter(PIIRedactionFilter())
        logging.getLogger().addHandler(file_handler)


def _setup_stdlib_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
) -> None:
    """Fallback standard library logging when structlog is not available."""
    # Lazy import PII redaction to avoid circular imports
    try:
        PIIRedactionFilter, _ = _get_pii_redaction()
    except ImportError:
        PIIRedactionFilter = None

    log_level = getattr(logging, level.upper(), logging.INFO)

    if format_type == "json":
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}'
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)

    # Add PII redaction filter to all handlers
    if PIIRedactionFilter is not None:
        for handler in handlers:
            handler.addFilter(PIIRedactionFilter())

    logging.basicConfig(
        format=fmt,
        level=log_level,
        handlers=handlers,
        force=True,
    )


def get_logger(name: str):
    """
    Get a structured logger instance.

    Returns a structlog BoundLogger when structlog is available,
    otherwise returns a standard library logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Bound structured logger or stdlib logger instance
    """
    if structlog is not None:
        return structlog.get_logger(name)
    return logging.getLogger(name)
