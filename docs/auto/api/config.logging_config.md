# config.logging_config

## Function: 

Lazy import of PII redaction to avoid circular imports.

The import chain logging_config → core.pii_redaction → core.__init__
can cause circular imports at module load time. By deferring the import
until setup_logging() is called, all modules are already loaded.

*Line: 21*

---

## Function: 

Configure structured logging for the application.

Uses structlog when available for JSON-formatted structured logs.
Falls back to standard library logging otherwise.
PII redaction is automatically wired into both paths.

Args:
    level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format_type: Output format ('json' for production, 'console' for development)
    log_file: Optional file path for log output

*Line: 32*

---

## Function: 

Configure structlog-based structured logging.

*Line: 55*

---

## Function: 

Fallback standard library logging when structlog is not available.

*Line: 118*

---

## Function: 

Get a structured logger instance.

Returns a structlog BoundLogger when structlog is available,
otherwise returns a standard library logger.

Args:
    name: Logger name (typically __name__)

Returns:
    Bound structured logger or stdlib logger instance

*Line: 156*

---

