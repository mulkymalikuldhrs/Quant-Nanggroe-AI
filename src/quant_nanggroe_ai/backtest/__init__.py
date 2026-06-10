"""
Backtest Engine Package — Strategy Backtesting & Walk-Forward Analysis
======================================================================

Exports:
    BacktestEngine   — Event-driven strategy backtesting
    WalkForwardAnalyzer — Walk-forward optimization
    BacktestMetrics  — Performance metric calculations (Sharpe, Sortino, etc.)

Usage:
    from quant_nanggroe_ai.backtest import BacktestEngine, BacktestMetrics

    engine = BacktestEngine(initial_capital=100_000, commission=0.001)
    result = engine.run(my_strategy, data)
    metrics = BacktestMetrics()
    print(metrics.sharpe_ratio(result.returns))
"""

from quant_nanggroe_ai.backtest.engine import BacktestEngine, BacktestResult, BacktestTrade
from quant_nanggroe_ai.backtest.metrics import BacktestMetrics
from quant_nanggroe_ai.backtest.walk_forward import WalkForwardAnalyzer, WalkForwardResult

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "BacktestTrade",
    "BacktestMetrics",
    "WalkForwardAnalyzer",
    "WalkForwardResult",
]
