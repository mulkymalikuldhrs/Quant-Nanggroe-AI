# core.pii_redaction

## Function: 

Redact PII from *text* using compiled regex patterns.

Parameters
----------
text : str
    The input string potentially containing PII.

Returns
-------
str
    The string with all matched PII replaced by redaction tokens.

*Line: 73*

---

## Function: 

structlog processor that redacts PII from all string values.

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

*Line: 94*

---

## Class: 

Standard ``logging.Filter`` that redacts PII from log records.

Add to any logging handler::

    handler = logging.StreamHandler()
    handler.addFilter(PIIRedactionFilter())

The filter redacts PII from the formatted message by overriding
``getMessage()`` to apply redaction after formatting.

**Methods:** filter

*Line: 126*

---

## Function: 

Redact PII in the log record message.

Always returns ``True`` so the record is not suppressed.
Uses a patched getMessage to avoid overwriting LogRecord built-in
attributes that cause KeyError in Python's logging internals.

*Line: 138*

---

## Function: 

*Line: 147*

---

