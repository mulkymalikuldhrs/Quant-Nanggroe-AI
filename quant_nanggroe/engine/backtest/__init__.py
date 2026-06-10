"""Backtesting Engine for Quant-Nanggroe-AI.

Provides a comprehensive backtesting framework supporting:
- Multiple markets (crypto, forex, stocks, futures)
- Realistic execution (slippage, commission, market impact)
- Walk-Forward Analysis (mandatory for validation)
- Monte Carlo simulation for confidence intervals
- Multiple strategy types (signal-based, factor-based, ML-based)
- Specialised multi-market engines (equity, crypto, forex, futures, composite)
- Data loaders (yfinance, ccxt)
- Portfolio optimizers (risk parity, mean variance, equal volatility)

Extracted from Vibe-Trading's backtest engines and ai-hedge-fund's metrics.
"""

# ── Core engine (simple/default backtest) ──

from quant_nanggroe.engine.backtest.engine import BacktestEngine
from quant_nanggroe.engine.backtest.portfolio import Portfolio
from quant_nanggroe.engine.backtest.metrics import PerformanceMetrics
from quant_nanggroe.engine.backtest.execution import ExecutionSimulator
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloSimulator
from quant_nanggroe.engine.backtest.report import BacktestReport

# ── Multi-market engines ──

from quant_nanggroe.engine.backtest.engines import (
    BaseEngine,
    EquityEngine,
    CryptoEngine,
    ForexEngine,
    FuturesEngine,
    CompositeEngine,
    create_engine,
    detect_market,
    detect_submarket,
    is_china_futures,
)

# ── Data loaders ──

from quant_nanggroe.engine.backtest.loaders import (
    BaseLoader,
    NoAvailableSourceError,
    validate_date_range,
    YFinanceLoader,
    CCXTLoader,
)

# ── Portfolio optimizers ──

from quant_nanggroe.engine.backtest.optimizers import (
    BaseOptimizer,
    RiskParityOptimizer,
    MeanVarianceOptimizer,
    EqualVolatilityOptimizer,
)

__all__ = [
    # Core
    "BacktestEngine",
    "Portfolio",
    "PerformanceMetrics",
    "ExecutionSimulator",
    "WalkForwardAnalyzer",
    "MonteCarloSimulator",
    "BacktestReport",
    # Multi-market engines
    "BaseEngine",
    "EquityEngine",
    "CryptoEngine",
    "ForexEngine",
    "FuturesEngine",
    "CompositeEngine",
    "create_engine",
    "detect_market",
    "detect_submarket",
    "is_china_futures",
    # Data loaders
    "BaseLoader",
    "NoAvailableSourceError",
    "validate_date_range",
    "YFinanceLoader",
    "CCXTLoader",
    # Portfolio optimizers
    "BaseOptimizer",
    "RiskParityOptimizer",
    "MeanVarianceOptimizer",
    "EqualVolatilityOptimizer",
]
