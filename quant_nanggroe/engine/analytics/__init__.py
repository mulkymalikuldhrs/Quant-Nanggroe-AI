"""
Performance Analytics — ffn-style financial metrics
===================================================
Portfolio/strategy performance metrics: Sharpe, Sortino, Calmar,
drawdown analysis, rolling metrics, benchmarking.

Referensi: ffn (pmorissette/ffn), QuantPy (jsmidt/QuantPy),
Finance-Python (alpha-miner/Finance-Python)
"""

from quant_nanggroe.engine.analytics.metrics import (
    PerformanceMetrics,
    benchmark_returns,
    compute_metrics,
    rolling_sharpe,
    strategy_comparison,
)

__all__ = [
    "PerformanceMetrics",
    "benchmark_returns",
    "compute_metrics",
    "rolling_sharpe",
    "strategy_comparison",
]
