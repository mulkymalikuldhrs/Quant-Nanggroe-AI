# engine.observability

## Class: 

A span that does nothing.

**Methods:** __enter__, __exit__, set_attribute, set_attributes, add_event, record_exception, is_recording

*Line: 71*

---

## Class: 

A tracer that creates no-op spans.

**Methods:** start_span, start_as_current_span

*Line: 96*

---

## Class: 

A counter that does nothing.

**Methods:** add

*Line: 106*

---

## Class: 

A histogram that does nothing.

**Methods:** record

*Line: 113*

---

## Class: 

A gauge that does nothing.

**Methods:** set

*Line: 120*

---

## Class: 

Container for no-op metric instruments.

**Methods:** __init__

*Line: 127*

---

## Class: 

Container for real OpenTelemetry metric instruments.

**Methods:** __init__

*Line: 144*

---

## Class: 

JSON-formatted structured logger.

Emits log entries as JSON objects for easy parsing by log aggregation
systems (e.g. ELK, Loki, CloudWatch Logs Insights).

**Methods:** __init__, _log, info, warning, error, debug

*Line: 197*

---

## Class: 

Central observability manager for Quant-Nanggroe-AI.

Sets up OpenTelemetry tracing and metrics with graceful degradation.
When OBSERVABILITY_ENABLED is false (default), all operations are
zero-overhead no-ops.

Usage::

    obs = ObservabilityManager()
    # or use the singleton factory:
    obs = get_observability()

**Methods:** __init__, _setup_real_observability, _setup_noop_observability, enabled, tracer, metrics, structured_logger

*Line: 233*

---

## Function: 

Get or create the singleton ObservabilityManager.

Auto-configured from environment variables:
- OBSERVABILITY_ENABLED (default: false)
- OTEL_SERVICE_NAME (default: quant-nanggroe-ai)
- OTEL_EXPORTER_OTLP_ENDPOINT

Returns:
    ObservabilityManager instance (singleton).

*Line: 327*

---

## Function: 

Reset the singleton (mainly for testing).

*Line: 344*

---

## Function: 

Decorator that creates a tracing span around a function.

When observability is disabled, this is zero-overhead (no-op span).

Args:
    span_name: Custom span name (defaults to function.__qualname__).
    attributes: Static attributes to set on the span.

Usage::

    @traced("check_trade", attributes={"component": "risk"})
    def check_trade(self, symbol, direction, ...):
        ...

*Line: 355*

---

## Function: 

Set span attributes from function argument names and values.

*Line: 418*

---

## Function: 

*Line: 74*

---

## Function: 

*Line: 77*

---

## Function: 

*Line: 80*

---

## Function: 

*Line: 83*

---

## Function: 

*Line: 86*

---

## Function: 

*Line: 89*

---

## Function: 

*Line: 92*

---

## Function: 

*Line: 99*

---

## Function: 

*Line: 102*

---

## Function: 

*Line: 109*

---

## Function: 

*Line: 116*

---

## Function: 

*Line: 123*

---

## Function: 

*Line: 130*

---

## Function: 

*Line: 147*

---

## Function: 

*Line: 204*

---

## Function: 

*Line: 208*

---

## Function: 

*Line: 218*

---

## Function: 

*Line: 221*

---

## Function: 

*Line: 224*

---

## Function: 

*Line: 227*

---

## Function: 

*Line: 247*

---

## Function: 

Configure real OpenTelemetry providers.

*Line: 263*

---

## Function: 

Configure no-op providers (zero overhead).

*Line: 296*

---

## Function: 

Whether observability is actively enabled.

*Line: 302*

---

## Function: 

Return the tracer (real or no-op).

*Line: 307*

---

## Function: 

Return the metrics container (real or no-op).

*Line: 312*

---

## Function: 

Return the structured JSON logger.

*Line: 317*

---

## Function: 

*Line: 370*

---

## Function: 

*Line: 374*

---

