"""PII redaction utilities for log sanitization.

Provides regex-based redaction of Personally Identifiable Information (PII)
from log messages, plus integrations with both structlog and standard
library logging.

Redacted patterns:
- JWT tokens                -> ``[REDACTED_JWT]``
- API keys (sk-…, ghp_…, api_key=…) -> ``[REDACTED_API_KEY]``
- Email addresses           -> ``[REDACTED_EMAIL]``
- Credit card numbers       -> ``[REDACTED_CC]``
- IP addresses              -> ``[REDACTED_IP]``
- Phone numbers             -> ``[REDACTED_PHONE]``
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

# ── Compiled regex patterns ──────────────────────────────────────────────────

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ── High-specificity patterns first (to avoid false positives) ──
    # JWT tokens (three base64url segments separated by dots)
    (
        re.compile(r"\beyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"),
        "[REDACTED_JWT]",
    ),
    # API keys — common prefixes (must come before phone/cc to avoid partial matches)
    (
        re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
        "[REDACTED_API_KEY]",
    ),
    (
        re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
        "[REDACTED_API_KEY]",
    ),
    # API keys — assignment patterns like api_key=... or api_key:...
    (
        re.compile(r"\bapi_key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?", re.IGNORECASE),
        "[REDACTED_API_KEY]",
    ),
    # Email addresses
    (
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
        "[REDACTED_EMAIL]",
    ),
    # Credit card numbers (13-19 digits, with optional spaces/dashes)
    (
        re.compile(r"\b(?:\d[ \-]?){12,18}\d\b"),
        "[REDACTED_CC]",
    ),
    # IPv4 addresses (avoid matching version numbers like 1.2.3)
    (
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "[REDACTED_IP]",
    ),
    # Phone numbers (various international formats)
    # Use negative lookbehind/ahead to avoid matching inside alphanumeric tokens
    (
        re.compile(
            r"(?<![A-Za-z0-9_\-])"
            r"(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}"
            r"(?![A-Za-z0-9_\-])"
        ),
        "[REDACTED_PHONE]",
    ),
]


def redact_pii(text: str) -> str:
    """Redact PII from *text* using compiled regex patterns.

    Parameters
    ----------
    text : str
        The input string potentially containing PII.

    Returns
    -------
    str
        The string with all matched PII replaced by redaction tokens.
    """
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── structlog processor ──────────────────────────────────────────────────────


def pii_redaction_processor(
    logger: Any, method: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """structlog processor that redacts PII from all string values.

    Add to your structlog processor chain::

        structlog.configure(processors=[..., pii_redaction_processor, ...])

    Parameters
    ----------
    logger : Any
        The structlog logger (unused, required by processor protocol).
    method : str
        The log method name (unused, required by processor protocol).
    event_dict : dict
        The structlog event dictionary.

    Returns
    -------
    dict
        The event dictionary with PII redacted from string values.
    """
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = redact_pii(value)
    return event_dict


# ── Standard logging Filter ──────────────────────────────────────────────────


class PIIRedactionFilter(logging.Filter):
    """Standard ``logging.Filter`` that redacts PII from log records.

    Add to any logging handler::

        handler = logging.StreamHandler()
        handler.addFilter(PIIRedactionFilter())

    The filter redacts PII from the formatted message by overriding
    ``getMessage()`` to apply redaction after formatting.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact PII in the log record message.

        Always returns ``True`` so the record is not suppressed.
        Uses a patched getMessage to avoid overwriting LogRecord built-in
        attributes that cause KeyError in Python's logging internals.
        """
        original_getMessage = record.getMessage

        def _redacted_getMessage():
            msg = original_getMessage()
            return redact_pii(msg) if isinstance(msg, str) else msg

        record.getMessage = _redacted_getMessage
        return True
