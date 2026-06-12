"""Configuration module for Quant Nanggroe AI."""

from quant_nanggroe.config.settings import Settings, get_settings
from quant_nanggroe.config.logging import (
    setup_logging,
    get_logger,
    TradeLogger,
    AuditTrail,
    request_id,
    agent_id,
    trade_id,
)
from quant_nanggroe.config.tracing import (
    setup_tracing,
    DecisionTracer,
    HAS_OTEL,
)
from quant_nanggroe.config.metrics import (
    HAS_PROMETHEUS,
    REGISTRY,
    TRADE_SIGNALS_TOTAL,
    RISK_GATE_DECISIONS,
    KILL_SWITCH_TRIGGERS,
    TRADE_EXECUTION_LATENCY,
    ACTIVE_POSITIONS,
    PORTFOLIO_VALUE,
    DRAWDOWN_PCT,
    STRATEGY_PERFORMANCE,
    SYSTEM_INFO,
    start_metrics_server,
    get_metrics,
    track_execution_latency,
)
from quant_nanggroe.config.shutdown import (
    ShutdownConfig,
    GracefulShutdown,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Structured logging
    "setup_logging",
    "get_logger",
    "TradeLogger",
    "AuditTrail",
    "request_id",
    "agent_id",
    "trade_id",
    # OpenTelemetry tracing
    "setup_tracing",
    "DecisionTracer",
    "HAS_OTEL",
    # Prometheus metrics
    "HAS_PROMETHEUS",
    "REGISTRY",
    "TRADE_SIGNALS_TOTAL",
    "RISK_GATE_DECISIONS",
    "KILL_SWITCH_TRIGGERS",
    "TRADE_EXECUTION_LATENCY",
    "ACTIVE_POSITIONS",
    "PORTFOLIO_VALUE",
    "DRAWDOWN_PCT",
    "STRATEGY_PERFORMANCE",
    "SYSTEM_INFO",
    "start_metrics_server",
    "get_metrics",
    "track_execution_latency",
    # Graceful shutdown
    "ShutdownConfig",
    "GracefulShutdown",
]
