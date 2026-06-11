"""Tests for the OpenTelemetry observability layer.

Tests cover:
- ObservabilityManager creation (disabled default, enabled)
- No-op providers (when disabled or OTEL not installed)
- Metric instruments availability
- Structured logging
- Singleton factory
- Tracing decorator
- Reset functionality
"""

from __future__ import annotations

import os
import pytest
import logging
import json

# Ensure observability is disabled for most tests
os.environ.pop("OBSERVABILITY_ENABLED", None)


class TestObservabilityManager:
    """Tests for ObservabilityManager."""

    def setup_method(self):
        """Reset singleton before each test."""
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def teardown_method(self):
        """Reset singleton after each test."""
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def test_default_disabled(self):
        """Observability should be disabled by default."""
        from quant_nanggroe.engine.observability import ObservabilityManager
        obs = ObservabilityManager()
        assert obs.enabled is False

    def test_explicit_disabled(self):
        """Explicitly disabled ObservabilityManager."""
        from quant_nanggroe.engine.observability import ObservabilityManager
        obs = ObservabilityManager(enabled=False)
        assert obs.enabled is False

    def test_noop_tracer_when_disabled(self):
        """When disabled, tracer should be NoOpTracer."""
        from quant_nanggroe.engine.observability import ObservabilityManager, NoOpTracer
        obs = ObservabilityManager(enabled=False)
        assert isinstance(obs.tracer, NoOpTracer)

    def test_noop_metrics_when_disabled(self):
        """When disabled, metrics should be NoOpMetrics."""
        from quant_nanggroe.engine.observability import ObservabilityManager, NoOpMetrics
        obs = ObservabilityManager(enabled=False)
        assert isinstance(obs.metrics, NoOpMetrics)

    def test_noop_span_context_manager(self):
        """NoOpSpan should work as a context manager."""
        from quant_nanggroe.engine.observability import NoOpSpan
        span = NoOpSpan()
        with span as s:
            s.set_attribute("key", "value")
            s.set_attributes({"a": 1})
            s.add_event("event")
            assert s.is_recording() is False

    def test_noop_counter_add(self):
        """NoOpCounter.add should not raise."""
        from quant_nanggroe.engine.observability import NoOpCounter
        counter = NoOpCounter()
        counter.add(1, {"symbol": "AAPL"})  # Should not raise

    def test_noop_histogram_record(self):
        """NoOpHistogram.record should not raise."""
        from quant_nanggroe.engine.observability import NoOpHistogram
        hist = NoOpHistogram()
        hist.record(0.5, {"check_name": "risk"})  # Should not raise

    def test_noop_gauge_set(self):
        """NoOpGauge.set should not raise."""
        from quant_nanggroe.engine.observability import NoOpGauge
        gauge = NoOpGauge()
        gauge.set(42, {"sensor": "quant_scanner"})  # Should not raise


class TestMetricsInstruments:
    """Tests that all required metric instruments exist."""

    def setup_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def teardown_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def test_all_metrics_present(self):
        """All 9 required metrics should be available."""
        from quant_nanggroe.engine.observability import ObservabilityManager
        obs = ObservabilityManager(enabled=False)
        metrics = obs.metrics

        # Required metrics per spec
        assert hasattr(metrics, "trades_total")
        assert hasattr(metrics, "trade_duration_seconds")
        assert hasattr(metrics, "risk_check_duration_seconds")
        assert hasattr(metrics, "kill_switch_activations_total")
        assert hasattr(metrics, "active_positions")
        assert hasattr(metrics, "daily_pnl")
        assert hasattr(metrics, "pressure_score")
        assert hasattr(metrics, "api_request_duration_seconds")
        assert hasattr(metrics, "llm_tokens_total")

    def test_metrics_callable_noop(self):
        """All metrics should be callable without error when disabled."""
        from quant_nanggroe.engine.observability import ObservabilityManager
        obs = ObservabilityManager(enabled=False)
        m = obs.metrics

        # Counter operations
        m.trades_total.add(1, {"symbol": "AAPL", "direction": "BUY", "verdict": "APPROVED"})
        m.kill_switch_activations_total.add(1, {"reason": "AUTO_DAILY_LIMIT"})
        m.llm_tokens_total.add(100, {"model": "llama-3.1", "token_type": "input"})

        # Histogram operations
        m.trade_duration_seconds.record(0.5, {"symbol": "AAPL"})
        m.risk_check_duration_seconds.record(0.01, {"check_name": "full_gate"})
        m.api_request_duration_seconds.record(0.3, {"provider": "nvidia_nim"})

        # Gauge operations
        m.active_positions.set(5)
        m.daily_pnl.set(-500.0)
        m.pressure_score.set(0.7, {"sensor": "quant_scanner", "side": "buy"})


class TestStructuredLogger:
    """Tests for the StructuredLogger."""

    def test_logger_creation(self):
        """StructuredLogger should be created with a name."""
        from quant_nanggroe.engine.observability import StructuredLogger
        sl = StructuredLogger("test_module")
        assert sl._name == "test_module"

    def test_logger_info(self, caplog):
        """StructuredLogger.info should emit JSON."""
        from quant_nanggroe.engine.observability import StructuredLogger
        sl = StructuredLogger("test_module")
        with caplog.at_level(logging.INFO, logger="observability.test_module"):
            sl.info("test_message", key="value")
        assert len(caplog.records) > 0
        record = caplog.records[-1]
        data = json.loads(record.message)
        assert data["message"] == "test_message"
        assert data["key"] == "value"
        assert data["level"] == "INFO"

    def test_logger_warning(self, caplog):
        """StructuredLogger.warning should emit JSON."""
        from quant_nanggroe.engine.observability import StructuredLogger
        sl = StructuredLogger("test_module")
        with caplog.at_level(logging.WARNING, logger="observability.test_module"):
            sl.warning("test_warning", code=500)
        assert len(caplog.records) > 0
        data = json.loads(caplog.records[-1].message)
        assert data["message"] == "test_warning"
        assert data["code"] == 500

    def test_logger_error(self, caplog):
        """StructuredLogger.error should emit JSON."""
        from quant_nanggroe.engine.observability import StructuredLogger
        sl = StructuredLogger("test_module")
        with caplog.at_level(logging.ERROR, logger="observability.test_module"):
            sl.error("test_error", detail="fail")
        assert len(caplog.records) > 0
        data = json.loads(caplog.records[-1].message)
        assert data["message"] == "test_error"

    def test_observability_manager_has_structured_logger(self):
        """ObservabilityManager should provide a structured logger."""
        from quant_nanggroe.engine.observability import ObservabilityManager, StructuredLogger
        obs = ObservabilityManager(enabled=False)
        assert isinstance(obs.structured_logger, StructuredLogger)


class TestSingletonFactory:
    """Tests for get_observability singleton factory."""

    def setup_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def teardown_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def test_singleton_returns_same_instance(self):
        """get_observability should return the same instance each time."""
        from quant_nanggroe.engine.observability import get_observability
        obs1 = get_observability()
        obs2 = get_observability()
        assert obs1 is obs2

    def test_reset_creates_new_instance(self):
        """After reset, get_observability should return a new instance."""
        from quant_nanggroe.engine.observability import get_observability, reset_observability
        obs1 = get_observability()
        reset_observability()
        obs2 = get_observability()
        assert obs1 is not obs2


class TestTracingDecorator:
    """Tests for the @traced decorator."""

    def setup_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def teardown_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def test_traced_decorator_preserves_function(self):
        """@traced should not change function behavior when disabled."""
        from quant_nanggroe.engine.observability import traced

        @traced("test_func")
        def my_func(x, y):
            return x + y

        result = my_func(3, 4)
        assert result == 7

    def test_traced_decorator_preserves_function_name(self):
        """@traced should preserve function name."""
        from quant_nanggroe.engine.observability import traced

        @traced("custom_name")
        def my_func():
            pass

        assert my_func.__name__ == "my_func"

    def test_traced_decorator_handles_exceptions(self):
        """@traced should re-raise exceptions."""
        from quant_nanggroe.engine.observability import traced

        @traced("failing_func")
        def my_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            my_func()

    def test_traced_decorator_with_attributes(self):
        """@traced should accept static attributes."""
        from quant_nanggroe.engine.observability import traced

        @traced("attr_func", attributes={"component": "test"})
        def my_func():
            return "ok"

        result = my_func()
        assert result == "ok"

    def test_traced_decorator_on_method(self):
        """@traced should work on class methods."""
        from quant_nanggroe.engine.observability import traced

        class MyClass:
            @traced("my_method")
            def my_method(self, x):
                return x * 2

        obj = MyClass()
        result = obj.my_method(5)
        assert result == 10


class TestEnvironmentConfiguration:
    """Tests for environment variable configuration."""

    def setup_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        reset_observability()

    def teardown_method(self):
        from quant_nanggroe.engine.observability import reset_observability
        # Clean env vars
        os.environ.pop("OBSERVABILITY_ENABLED", None)
        os.environ.pop("OTEL_SERVICE_NAME", None)

    def test_observability_default_false(self):
        """OBSERVABILITY_ENABLED should default to false."""
        os.environ.pop("OBSERVABILITY_ENABLED", None)
        # Re-import to get fresh module-level var
        import importlib
        from quant_nanggroe.engine import observability
        importlib.reload(observability)
        assert observability.OBSERVABILITY_ENABLED is False

    def test_observability_enabled_true(self):
        """OBSERVABILITY_ENABLED=true should enable."""
        import importlib
        from quant_nanggroe.engine import observability
        os.environ["OBSERVABILITY_ENABLED"] = "true"
        importlib.reload(observability)
        assert observability.OBSERVABILITY_ENABLED is True
        os.environ.pop("OBSERVABILITY_ENABLED", None)
        importlib.reload(observability)

    def test_observability_enabled_yes(self):
        """OBSERVABILITY_ENABLED=yes should enable."""
        import importlib
        from quant_nanggroe.engine import observability
        os.environ["OBSERVABILITY_ENABLED"] = "yes"
        importlib.reload(observability)
        assert observability.OBSERVABILITY_ENABLED is True
        os.environ.pop("OBSERVABILITY_ENABLED", None)
        importlib.reload(observability)

    def test_service_name_default(self):
        """Default service name should be quant-nanggroe-ai."""
        import importlib
        from quant_nanggroe.engine import observability
        os.environ.pop("OTEL_SERVICE_NAME", None)
        importlib.reload(observability)
        assert observability.OTEL_SERVICE_NAME == "quant-nanggroe-ai"


class TestNoOpZeroOverhead:
    """Tests that no-op operations are truly zero-overhead."""

    def test_noop_counter_no_error(self):
        """NoOpCounter should never raise, regardless of attributes."""
        from quant_nanggroe.engine.observability import NoOpCounter
        counter = NoOpCounter()
        # Various attribute types
        counter.add(1, {"symbol": "AAPL"})
        counter.add(100, {})
        counter.add(0, None)
        counter.add(-1, {"key": "value"})
        # No assertion needed — just no exception

    def test_noop_histogram_no_error(self):
        """NoOpHistogram should never raise."""
        from quant_nanggroe.engine.observability import NoOpHistogram
        hist = NoOpHistogram()
        hist.record(0.001, {"check_name": "test"})
        hist.record(0.0)
        hist.record(999.99, None)

    def test_noop_tracer_no_error(self):
        """NoOpTracer should never raise."""
        from quant_nanggroe.engine.observability import NoOpTracer
        tracer = NoOpTracer()
        span = tracer.start_span("test")
        span.set_attribute("key", "value")
        span.set_attributes({"a": 1, "b": "two"})
        span.add_event("event_name")
        span.record_exception(ValueError("test"))
        assert span.is_recording() is False

    def test_disabled_observability_full_workflow(self):
        """Full workflow with disabled observability should work without errors."""
        from quant_nanggroe.engine.observability import ObservabilityManager
        obs = ObservabilityManager(enabled=False)

        # Use tracer
        with obs.tracer.start_as_current_span("test_span") as span:
            span.set_attribute("key", "value")

        # Use all metrics
        obs.metrics.trades_total.add(1, {"symbol": "BTC", "direction": "BUY", "verdict": "APPROVED"})
        obs.metrics.trade_duration_seconds.record(0.5)
        obs.metrics.risk_check_duration_seconds.record(0.01, {"check_name": "gate"})
        obs.metrics.kill_switch_activations_total.add(1, {"reason": "AUTO_DAILY_LIMIT"})
        obs.metrics.active_positions.set(3)
        obs.metrics.daily_pnl.set(100.50)
        obs.metrics.pressure_score.set(0.75, {"sensor": "smc_agent"})
        obs.metrics.api_request_duration_seconds.record(0.2, {"provider": "nvidia_nim"})
        obs.metrics.llm_tokens_total.add(500, {"model": "llama-3.1"})

        # Use structured logger
        obs.structured_logger.info("test_event", data="value")

        assert obs.enabled is False
