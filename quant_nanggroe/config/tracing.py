"""OpenTelemetry tracing for Quant-Nanggroe-AI decision pipeline.

Provides:
- setup_tracing(): Initialize OpenTelemetry with optional OTLP or console export
- DecisionTracer: High-level tracer for decision pipeline steps

If opentelemetry packages are not installed, NoOp fallbacks are used automatically.
This ensures the system works without opentelemetry dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Optional OpenTelemetry imports ───────────────────────────────────────

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource

    HAS_OTEL = True
    logger.info("OpenTelemetry packages available — tracing can be enabled.")
except ImportError:
    HAS_OTEL = False
    logger.info(
        "OpenTelemetry packages not installed — tracing will use no-op fallbacks. "
        "Install with: pip install opentelemetry-api opentelemetry-sdk"
    )


# ── No-op fallback implementations ──────────────────────────────────────


class _NoOpSpan:
    """A span that does nothing — used when OpenTelemetry is not installed."""

    def __enter__(self):
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        pass

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def is_recording(self) -> bool:
        return False


class _NoOpTracer:
    """A tracer that creates no-op spans — used when OpenTelemetry is not installed."""

    def start_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()

    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()


# ── Setup function ───────────────────────────────────────────────────────


def setup_tracing(
    service_name: str = "quant-nanggroe-ai",
    endpoint: Optional[str] = None,
    console: bool = False,
) -> Any:
    """Initialize OpenTelemetry tracing.

    If OpenTelemetry is not installed, returns a NoOp tracer that
    provides the same interface but does nothing.

    Args:
        service_name: Name of the service for resource attribution.
        endpoint: OTLP endpoint URL (e.g., "http://localhost:4317").
        console: If True, also export spans to console for debugging.

    Returns:
        Configured tracer instance (real or NoOp).
    """
    if not HAS_OTEL:
        logger.info("OpenTelemetry not available — returning NoOp tracer.")
        return _NoOpTracer()

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTLP trace exporter configured: %s", endpoint)
        except ImportError:
            logger.info(
                "OTLP exporter not installed — spans will not be exported remotely. "
                "Install with: pip install opentelemetry-exporter-otlp-proto-grpc"
            )
        except Exception as e:
            logger.warning("Failed to configure OTLP exporter: %s", e)

    if console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console span exporter configured.")

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


# ── DecisionTracer ───────────────────────────────────────────────────────


class DecisionTracer:
    """Trace decision pipeline steps for audit and debugging.

    Provides high-level tracing methods for each stage of the
    quantitative decision pipeline:
    - Market analysis
    - Pressure calculation
    - Risk assessment
    - Order execution

    If OpenTelemetry is not installed, all methods return NoOp spans
    that provide the same interface but do nothing.

    Usage::

        tracer = DecisionTracer()
        with tracer.trace_market_analysis("XAUUSD", "TRENDING_UP") as span:
            # ... do analysis
            span.set_attribute("adx", 30.0)
    """

    def __init__(self, tracer: Optional[Any] = None) -> None:
        if tracer is not None:
            self.tracer = tracer
        elif HAS_OTEL:
            self.tracer = trace.get_tracer("quant-nanggroe-ai")
        else:
            self.tracer = _NoOpTracer()

    def trace_market_analysis(self, symbol: str, regime: str) -> Any:
        """Create span for market analysis step.

        Args:
            symbol: Trading symbol being analyzed.
            regime: Detected market regime.

        Returns:
            A context manager span (real or NoOp).
        """
        return self.tracer.start_as_current_span(
            "market_analysis",
            attributes={"symbol": symbol, "regime": regime},
        )

    def trace_pressure_calculation(self, sensors: dict[str, Any]) -> Any:
        """Create span for pressure calculation.

        Args:
            sensors: Dictionary of sensor readings and their values.

        Returns:
            A context manager span (real or NoOp).
        """
        # Flatten sensor dict into attributes (OTel attributes must be simple types)
        attrs: dict[str, Any] = {}
        for k, v in sensors.items():
            if isinstance(v, (str, int, float, bool)):
                attrs[k] = v
            else:
                attrs[k] = str(v)
        return self.tracer.start_as_current_span(
            "pressure_calculation",
            attributes=attrs,
        )

    def trace_risk_assessment(
        self, decision: str, checkpoints: dict[str, Any]
    ) -> Any:
        """Create span for risk assessment.

        Args:
            decision: Risk gate decision (APPROVED, VETOED).
            checkpoints: Dictionary of checkpoint results.

        Returns:
            A context manager span (real or NoOp).
        """
        attrs: dict[str, Any] = {"decision": decision}
        for k, v in checkpoints.items():
            if isinstance(v, (str, int, float, bool)):
                attrs[k] = v
            else:
                attrs[k] = str(v)
        return self.tracer.start_as_current_span(
            "risk_assessment",
            attributes=attrs,
        )

    def trace_execution(
        self, order_type: str, symbol: str, quantity: float
    ) -> Any:
        """Create span for order execution.

        Args:
            order_type: Type of order (MARKET, LIMIT, etc.).
            symbol: Trading symbol.
            quantity: Order quantity/lot size.

        Returns:
            A context manager span (real or NoOp).
        """
        return self.tracer.start_as_current_span(
            "execution",
            attributes={
                "order_type": order_type,
                "symbol": symbol,
                "quantity": quantity,
            },
        )
