"""Tests for the Prometheus metrics module."""
import pytest
from quant_nanggroe.config.metrics import (
    HAS_PROMETHEUS,
    TRADE_SIGNALS_TOTAL,
    RISK_GATE_DECISIONS,
    KILL_SWITCH_TRIGGERS,
    TRADE_EXECUTION_LATENCY,
    ACTIVE_POSITIONS,
    PORTFOLIO_VALUE,
    DRAWDOWN_PCT,
    STRATEGY_PERFORMANCE,
    SYSTEM_INFO,
    REGISTRY,
    start_metrics_server,
    get_metrics,
    track_execution_latency,
)


class TestNoOpMetricsWorkWithoutPrometheus:
    """All NoOp metric methods should be callable without error."""

    def test_noop_metrics_work_without_prometheus(self):
        # These should all work whether prometheus_client is installed or not
        TRADE_SIGNALS_TOTAL.labels(strategy="test", signal_type="buy", symbol="BTC").inc()
        RISK_GATE_DECISIONS.labels(decision="pass", veto_reason="none").inc()
        KILL_SWITCH_TRIGGERS.labels(trigger_type="manual").inc()
        ACTIVE_POSITIONS.labels(exchange="test").set(5)
        ACTIVE_POSITIONS.labels(exchange="test").inc()
        ACTIVE_POSITIONS.labels(exchange="test").dec()
        PORTFOLIO_VALUE.set(100000.0)
        DRAWDOWN_PCT.set(2.5)
        STRATEGY_PERFORMANCE.labels(strategy_name="momentum").observe(1.5)
        SYSTEM_INFO.info({"version": "test"})
        # If we got here, no exception was raised


class TestGetMetricsWithoutPrometheus:
    """get_metrics should return a string even without prometheus_client."""

    def test_get_metrics_without_prometheus(self):
        result = get_metrics()
        assert isinstance(result, str)
        if not HAS_PROMETHEUS:
            assert "not installed" in result.lower() or len(result) > 0


class TestTrackExecutionLatencyContext:
    """track_execution_latency should work as a context manager."""

    def test_track_execution_latency_context(self):
        with track_execution_latency(exchange="test", order_type="limit"):
            x = 1 + 1  # simulate work
        # No exception means success


class TestTradeSignalsNoop:
    """Test trade signals metric with noop fallback."""

    def test_trade_signals_noop(self):
        # Should not raise
        TRADE_SIGNALS_TOTAL.labels(strategy="alpha", signal_type="sell", symbol="ETH").inc(5)
        result = TRADE_SIGNALS_TOTAL.labels(strategy="alpha", signal_type="sell", symbol="ETH")
        # NoOp returns self
        if not HAS_PROMETHEUS:
            from quant_nanggroe.config.metrics import _NoOpMetric
            assert isinstance(result, _NoOpMetric)


class TestRiskGateDecisionsNoop:
    """Test risk gate decisions metric with noop fallback."""

    def test_risk_gate_decisions_noop(self):
        RISK_GATE_DECISIONS.labels(decision="veto", veto_reason="drawdown").inc()
        # Should not raise


class TestStartMetricsServerWithoutPrometheus:
    """start_metrics_server should not crash when prometheus is not installed."""

    def test_start_metrics_server_without_prometheus(self):
        # This should not raise even without prometheus
        # We can't actually start a server in tests, just verify it doesn't crash
        # when prometheus is not installed
        if not HAS_PROMETHEUS:
            start_metrics_server(port=9999)  # should warn but not crash
