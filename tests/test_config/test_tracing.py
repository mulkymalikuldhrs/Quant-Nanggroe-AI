"""Tests for OpenTelemetry tracing module."""

from __future__ import annotations

import pytest

from quant_nanggroe.config.tracing import (
    HAS_OTEL,
    setup_tracing,
    DecisionTracer,
    _NoOpSpan,
    _NoOpTracer,
)


class TestSetupTracing:
    """Tests for the setup_tracing function."""

    def test_setup_tracing_default_returns_tracer(self):
        """setup_tracing() returns a tracer-like object (real or NoOp)."""
        tracer = setup_tracing()
        # Should have the expected interface
        assert hasattr(tracer, "start_span")
        assert hasattr(tracer, "start_as_current_span")

    def test_setup_tracing_with_console(self):
        """setup_tracing(console=True) configures console exporter if OTEL available."""
        tracer = setup_tracing(console=True)
        assert tracer is not None

    def test_setup_tracing_with_custom_service_name(self):
        """setup_tracing accepts custom service_name."""
        tracer = setup_tracing(service_name="test-service")
        assert tracer is not None

    def test_setup_tracing_without_otel_uses_noop(self):
        """When OTEL is not available, NoOp tracer is returned."""
        if not HAS_OTEL:
            tracer = setup_tracing()
            assert isinstance(tracer, _NoOpTracer)


class TestDecisionTracer:
    """Tests for the DecisionTracer class."""

    def test_decision_tracer_creation_default(self):
        """DecisionTracer() creates a tracer (real or NoOp)."""
        dt = DecisionTracer()
        assert dt.tracer is not None

    def test_decision_tracer_with_explicit_noop_tracer(self):
        """DecisionTracer accepts an explicit NoOp tracer."""
        noop = _NoOpTracer()
        dt = DecisionTracer(tracer=noop)
        assert dt.tracer is noop

    def test_trace_market_analysis_returns_context_manager(self):
        """trace_market_analysis returns a context manager."""
        dt = DecisionTracer(tracer=_NoOpTracer())
        span = dt.trace_market_analysis("XAUUSD", "TRENDING_UP")
        # Should be usable as context manager
        with span as s:
            assert s is not None

    def test_trace_pressure_calculation_returns_context_manager(self):
        """trace_pressure_calculation returns a context manager."""
        dt = DecisionTracer(tracer=_NoOpTracer())
        span = dt.trace_pressure_calculation({
            "trend_direction": "bullish",
            "trend_strength": 0.8,
        })
        with span as s:
            assert s is not None

    def test_trace_risk_assessment_returns_context_manager(self):
        """trace_risk_assessment returns a context manager."""
        dt = DecisionTracer(tracer=_NoOpTracer())
        span = dt.trace_risk_assessment(
            decision="APPROVED",
            checkpoints={"risk_per_trade": True, "daily_loss": True},
        )
        with span as s:
            assert s is not None

    def test_trace_execution_returns_context_manager(self):
        """trace_execution returns a context manager."""
        dt = DecisionTracer(tracer=_NoOpTracer())
        span = dt.trace_execution(
            order_type="MARKET",
            symbol="EURUSD",
            quantity=0.01,
        )
        with span as s:
            assert s is not None


class TestNoOpFallback:
    """Tests for NoOp fallback implementations."""

    def test_noop_span_is_context_manager(self):
        """_NoOpSpan can be used as a context manager."""
        with _NoOpSpan() as span:
            span.set_attribute("key", "value")
            span.set_attributes({"k": "v"})
            span.add_event("event")
            assert span.is_recording() is False

    def test_noop_span_record_exception(self):
        """_NoOpSpan.record_exception does not raise."""
        span = _NoOpSpan()
        span.record_exception(ValueError("test"))

    def test_noop_tracer_creates_spans(self):
        """_NoOpTracer creates _NoOpSpan instances."""
        tracer = _NoOpTracer()
        span = tracer.start_span("test")
        assert isinstance(span, _NoOpSpan)

        ctx_span = tracer.start_as_current_span("test_ctx")
        assert isinstance(ctx_span, _NoOpSpan)

    def test_has_otel_flag_is_boolean(self):
        """HAS_OTEL is a boolean indicating OTEL availability."""
        assert isinstance(HAS_OTEL, bool)
