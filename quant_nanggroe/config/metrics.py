"""Prometheus metrics for Quant-Nanggroe-AI monitoring."""
import structlog
from typing import Optional
from contextlib import contextmanager

logger = structlog.get_logger(__name__)

HAS_PROMETHEUS = False
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
    from prometheus_client import start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    pass

# Define metrics (with NoOp fallback)
if HAS_PROMETHEUS:
    REGISTRY = CollectorRegistry()
    
    TRADE_SIGNALS_TOTAL = Counter(
        'trade_signals_total', 'Total trade signals generated',
        ['strategy', 'signal_type', 'symbol'], registry=REGISTRY
    )
    RISK_GATE_DECISIONS = Counter(
        'risk_gate_decisions_total', 'Risk gate decisions',
        ['decision', 'veto_reason'], registry=REGISTRY
    )
    KILL_SWITCH_TRIGGERS = Counter(
        'kill_switch_triggers_total', 'Kill switch activations',
        ['trigger_type'], registry=REGISTRY
    )
    TRADE_EXECUTION_LATENCY = Histogram(
        'trade_execution_latency_seconds', 'Trade execution latency',
        ['exchange', 'order_type'], registry=REGISTRY
    )
    ACTIVE_POSITIONS = Gauge(
        'active_positions', 'Number of active positions',
        ['exchange'], registry=REGISTRY
    )
    PORTFOLIO_VALUE = Gauge(
        'portfolio_value', 'Current portfolio value',
        [], registry=REGISTRY
    )
    DRAWDOWN_PCT = Gauge(
        'drawdown_pct', 'Current drawdown percentage',
        [], registry=REGISTRY
    )
    STRATEGY_PERFORMANCE = Histogram(
        'strategy_return_pct', 'Strategy return distribution',
        ['strategy_name'], registry=REGISTRY
    )
    SYSTEM_INFO = Info(
        'quant_nanggroe_system', 'System information', registry=REGISTRY
    )
else:
    # NoOp fallback
    class _NoOpMetric:
        def labels(self, *a, **kw): return self
        def inc(self, *a, **kw): pass
        def dec(self, *a, **kw): pass
        def set(self, *a, **kw): pass
        def observe(self, *a, **kw): pass
        def info(self, *a, **kw): pass
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, *a): pass
    
    TRADE_SIGNALS_TOTAL = _NoOpMetric()
    RISK_GATE_DECISIONS = _NoOpMetric()
    KILL_SWITCH_TRIGGERS = _NoOpMetric()
    TRADE_EXECUTION_LATENCY = _NoOpMetric()
    ACTIVE_POSITIONS = _NoOpMetric()
    PORTFOLIO_VALUE = _NoOpMetric()
    DRAWDOWN_PCT = _NoOpMetric()
    STRATEGY_PERFORMANCE = _NoOpMetric()
    SYSTEM_INFO = _NoOpMetric()
    REGISTRY = None

def start_metrics_server(port: int = 9090) -> None:
    """Start Prometheus metrics HTTP server."""
    if HAS_PROMETHEUS:
        start_http_server(port, registry=REGISTRY)
        logger.info("metrics_server_started", port=port)
    else:
        logger.warning("prometheus_not_installed", message="Metrics server not started")

def get_metrics() -> str:
    """Get metrics in Prometheus exposition format."""
    if HAS_PROMETHEUS:
        return generate_latest(REGISTRY).decode('utf-8')
    return "# Prometheus client not installed\n"

@contextmanager
def track_execution_latency(exchange: str = "unknown", order_type: str = "market"):
    """Context manager to track execution latency."""
    if HAS_PROMETHEUS:
        with TRADE_EXECUTION_LATENCY.labels(exchange=exchange, order_type=order_type).time():
            yield
    else:
        yield
