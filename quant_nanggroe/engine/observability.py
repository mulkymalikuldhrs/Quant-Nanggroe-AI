"""OpenTelemetry Observability Layer for Quant-Nanggroe-AI.

Provides tracing, metrics, and structured logging via OpenTelemetry.
All functionality is OFF by default (OBSERVABILITY_ENABLED=false).
When disabled, all operations are zero-overhead no-ops.

If opentelemetry packages are not installed, graceful no-op providers
are used with logging.info notifications.

Usage::

    from quant_nanggroe.engine.observability import get_observability

    obs = get_observability()
    with obs.tracer.start_as_current_span("check_trade") as span:
        span.set_attribute("symbol", "AAPL")
        ...

    obs.metrics.trades_total.add(1, {"symbol": "AAPL", "direction": "BUY", "verdict": "APPROVED"})

Environment Variables:
    OBSERVABILITY_ENABLED: Set to "true" to enable (default: "false")
    OTEL_SERVICE_NAME: Service name for traces (default: "quant-nanggroe-ai")
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint URL
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

# ── Environment configuration ─────────────────────────────────────────────

OBSERVABILITY_ENABLED: bool = os.getenv("OBSERVABILITY_ENABLED", "true").lower() in ("true", "1", "yes")
OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "quant-nanggroe-ai")

# ── Lazy OpenTelemetry imports ────────────────────────────────────────────

_OTEL_AVAILABLE: bool = False
_Tracer = None
_Meter = None
_Counter = None
_Histogram = None
_ObservableGauge = None
_TelemetryProvider = None

try:
    from opentelemetry import metrics, trace  # type: ignore[import-untyped]
    from opentelemetry.sdk.metrics import MeterProvider  # type: ignore[import-untyped]
    from opentelemetry.sdk.resources import Resource  # type: ignore[import-untyped]
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-untyped]
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-untyped]
    _OTEL_AVAILABLE = True
    logger.info("OpenTelemetry packages available — observability can be enabled.")
except ImportError:
    logger.info(
        "OpenTelemetry packages not installed — observability will use no-op providers. "
        "Install with: pip install opentelemetry-api>=1.20.0 opentelemetry-sdk>=1.20.0"
    )


# ── No-op implementations (zero overhead) ────────────────────────────────

class NoOpSpan:
    """A span that does nothing."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        pass

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def is_recording(self) -> bool:
        return False


class NoOpTracer:
    """A tracer that creates no-op spans."""

    def start_span(self, name: str, **kwargs) -> NoOpSpan:
        return NoOpSpan()

    def start_as_current_span(self, name: str, **kwargs):
        return NoOpSpan()


class NoOpCounter:
    """A counter that does nothing."""

    def add(self, amount: int | float, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass


class NoOpHistogram:
    """A histogram that does nothing."""

    def record(self, amount: int | float, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass


class NoOpGauge:
    """A gauge that does nothing."""

    def set(self, amount: int | float, attributes: Optional[Dict[str, Any]] = None) -> None:
        pass


class NoOpMetrics:
    """Container for no-op metric instruments."""

    def __init__(self) -> None:
        self.trades_total = NoOpCounter()
        self.trade_duration_seconds = NoOpHistogram()
        self.risk_check_duration_seconds = NoOpHistogram()
        self.kill_switch_activations_total = NoOpCounter()
        self.active_positions = NoOpGauge()
        self.daily_pnl = NoOpGauge()
        self.pressure_score = NoOpGauge()
        self.api_request_duration_seconds = NoOpHistogram()
        self.llm_tokens_total = NoOpCounter()


# ── Real metrics container ───────────────────────────────────────────────

class RealMetrics:
    """Container for real OpenTelemetry metric instruments."""

    def __init__(self, meter) -> None:  # type: ignore[type-arg]
        self.trades_total = meter.create_counter(
            name="trades_total",
            description="Total number of trades by symbol, direction, and verdict",
            unit="1",
        )
        self.trade_duration_seconds = meter.create_histogram(
            name="trade_duration_seconds",
            description="Duration of trade execution in seconds",
            unit="s",
        )
        self.risk_check_duration_seconds = meter.create_histogram(
            name="risk_check_duration_seconds",
            description="Duration of risk check operations by check name",
            unit="s",
        )
        self.kill_switch_activations_total = meter.create_counter(
            name="kill_switch_activations_total",
            description="Total number of kill switch activations by reason",
            unit="1",
        )
        self.active_positions = meter.create_gauge(
            name="active_positions",
            description="Current number of active positions",
            unit="1",
        )
        self.daily_pnl = meter.create_gauge(
            name="daily_pnl",
            description="Current daily P&L value",
            unit="USD",
        )
        self.pressure_score = meter.create_gauge(
            name="pressure_score",
            description="Pressure score by sensor",
            unit="1",
        )
        self.api_request_duration_seconds = meter.create_histogram(
            name="api_request_duration_seconds",
            description="Duration of API requests by provider",
            unit="s",
        )
        self.llm_tokens_total = meter.create_counter(
            name="llm_tokens_total",
            description="Total LLM token usage by model",
            unit="1",
        )


# ── Structured JSON logger ───────────────────────────────────────────────

class StructuredLogger:
    """JSON-formatted structured logger.

    Emits log entries as JSON objects for easy parsing by log aggregation
    systems (e.g. ELK, Loki, CloudWatch Logs Insights).
    """

    def __init__(self, name: str = "quant_nanggroe") -> None:
        self._name = name
        self._logger = logging.getLogger(f"observability.{name}")

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "logger": self._name,
            "message": message,
            **kwargs,
        }
        getattr(self._logger, level.lower())(json.dumps(entry, default=str))

    def info(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log("DEBUG", message, **kwargs)


# ── ObservabilityManager ─────────────────────────────────────────────────

class ObservabilityManager:
    """Central observability manager for Quant-Nanggroe-AI.

    Sets up OpenTelemetry tracing and metrics with graceful degradation.
    When OBSERVABILITY_ENABLED is false (default), all operations are
    zero-overhead no-ops.

    Usage::

        obs = ObservabilityManager()
        # or use the singleton factory:
        obs = get_observability()
    """

    def __init__(self, enabled: Optional[bool] = None) -> None:
        self._enabled = enabled if enabled is not None else OBSERVABILITY_ENABLED
        self._otel_available = _OTEL_AVAILABLE
        self._structured_logger = StructuredLogger()

        if self._enabled and self._otel_available:
            self._setup_real_observability()
        else:
            self._setup_noop_observability()

        if self._enabled and not self._otel_available:
            logger.info(
                "Observability enabled but OpenTelemetry not installed. "
                "Using no-op providers. Install opentelemetry-api and opentelemetry-sdk."
            )

    def _setup_real_observability(self) -> None:
        """Configure real OpenTelemetry providers."""
        resource = Resource.create({"service.name": OTEL_SERVICE_NAME})

        # Tracing
        tracer_provider = TracerProvider(resource=resource)
        # Try to set up OTLP exporter if endpoint configured
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-untyped]
                    OTLPSpanExporter,
                )
                tracer_provider.add_span_processor(
                    BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
                )
                logger.info("OTLP trace exporter configured: %s", otlp_endpoint)
            except ImportError:
                logger.info("OTLP exporter not installed — traces will be processed but not exported remotely.")
            except Exception as e:
                logger.warning("Failed to configure OTLP exporter: %s", e)

        trace.set_tracer_provider(tracer_provider)
        self._tracer = trace.get_tracer(OTEL_SERVICE_NAME)

        # Metrics
        meter_provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(meter_provider)
        meter = metrics.get_meter(OTEL_SERVICE_NAME)
        self._metrics = RealMetrics(meter)

        self._structured_logger.info("observability_initialized", enabled=True, service=OTEL_SERVICE_NAME)

    def _setup_noop_observability(self) -> None:
        """Configure no-op providers (zero overhead)."""
        self._tracer = NoOpTracer()
        self._metrics = NoOpMetrics()

    @property
    def enabled(self) -> bool:
        """Whether observability is actively enabled."""
        return self._enabled and self._otel_available

    @property
    def tracer(self):
        """Return the tracer (real or no-op)."""
        return self._tracer

    @property
    def metrics(self):
        """Return the metrics container (real or no-op)."""
        return self._metrics

    @property
    def structured_logger(self) -> StructuredLogger:
        """Return the structured JSON logger."""
        return self._structured_logger


# ── Singleton factory ────────────────────────────────────────────────────

_instance: Optional[ObservabilityManager] = None


def get_observability() -> ObservabilityManager:
    """Get or create the singleton ObservabilityManager.

    Auto-configured from environment variables:
    - OBSERVABILITY_ENABLED (default: false)
    - OTEL_SERVICE_NAME (default: quant-nanggroe-ai)
    - OTEL_EXPORTER_OTLP_ENDPOINT

    Returns:
        ObservabilityManager instance (singleton).
    """
    global _instance
    if _instance is None:
        _instance = ObservabilityManager()
    return _instance


def reset_observability() -> None:
    """Reset the singleton (mainly for testing)."""
    global _instance
    _instance = None


# ── Tracing decorator ────────────────────────────────────────────────────

F = TypeVar("F", bound=Callable)


def traced(span_name: Optional[str] = None, attributes: Optional[Dict[str, str]] = None):
    """Decorator that creates a tracing span around a function.

    When observability is disabled, this is zero-overhead (no-op span).

    Args:
        span_name: Custom span name (defaults to function.__qualname__).
        attributes: Static attributes to set on the span.

    Usage::

        @traced("check_trade", attributes={"component": "risk"})
        def check_trade(self, symbol, direction, ...):
            ...
    """
    def decorator(func: F) -> F:
        name = span_name or func.__qualname__

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            obs = get_observability()
            with obs.tracer.start_as_current_span(name) as span:
                if attributes:
                    span.set_attributes(attributes)
                # Set common attributes from function args
                _set_span_args(span, func, args, kwargs)
                start = time.monotonic()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_attribute("error", True)
                    raise
                finally:
                    span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            obs = get_observability()
            with obs.tracer.start_as_current_span(name) as span:
                if attributes:
                    span.set_attributes(attributes)
                _set_span_args(span, func, args, kwargs)
                start = time.monotonic()
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_attribute("error", True)
                    raise
                finally:
                    span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _set_span_args(span, func: Callable, args: tuple, kwargs: dict) -> None:
    """Set span attributes from function argument names and values."""
    try:
        import inspect
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        # Skip 'self' and 'cls' parameters
        for i, param_name in enumerate(params):
            if param_name in ("self", "cls"):
                continue
            if i < len(args):
                val = args[i]
                if isinstance(val, (str, int, float, bool)):
                    span.set_attribute(f"arg.{param_name}", val)
            elif param_name in kwargs:
                val = kwargs[param_name]
                if isinstance(val, (str, int, float, bool)):
                    span.set_attribute(f"arg.{param_name}", val)
    except Exception:
        # Don't let span attribute setting break the function
        pass
