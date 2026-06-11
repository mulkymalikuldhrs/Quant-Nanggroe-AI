"""Backtesting Engine for Quant-Nanggroe-AI.

Provides a comprehensive backtesting framework supporting:
- Multiple markets (crypto, forex, stocks)
- Realistic execution (slippage, commission, market impact)
- Walk-Forward Analysis (mandatory for validation)
- Monte Carlo simulation for confidence intervals
- Multiple strategy types (signal-based, factor-based, ML-based)

Extracted from Vibe-Trading's backtest engines and ai-hedge-fund's metrics.
"""

from quant_nanggroe.engine.backtest.engine import BacktestEngine
from quant_nanggroe.engine.backtest.portfolio import Portfolio
from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
from quant_nanggroe.engine.backtest.execution import ExecutionSimulator
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloSimulator
from quant_nanggroe.engine.backtest.report import BacktestReport

__all__ = [
    "BacktestEngine",
    "Portfolio",
    "PerformanceMetrics",
    "ExecutionSimulator",
    "WalkForwardAnalyzer",
    "MonteCarloSimulator",
    "BacktestReport",
]
