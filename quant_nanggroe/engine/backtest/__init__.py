"""Backtesting Engine for Quant-Nanggroe-AI.

Provides a comprehensive backtesting framework supporting:
- Multiple markets (crypto, forex, stocks, futures)
- Realistic execution (slippage, commission, market impact)
- Walk-Forward Analysis (mandatory for validation)
- Monte Carlo simulation for confidence intervals
- Multiple strategy types (signal-based, factor-based, ML-based)
- Multi-strategy backtesting with portfolio aggregation
- Parameter sensitivity analysis
- Benchmark comparison
- Trade-level analytics
- Specialised multi-market engines (equity, crypto, forex, futures, composite)
- Data loaders (yfinance, ccxt)
- Portfolio optimizers (risk parity, mean variance, equal volatility)

Extracted from Vibe-Trading's backtest engines and ai-hedge-fund's metrics.
"""

# ── Core engine (simple/default backtest) ──

from quant_nanggroe.engine.backtest.benchmarks import BenchmarkManager, BenchmarkResult
from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine, MarketType, StrategyType

# ── Multi-market engines ──
from quant_nanggroe.engine.backtest.engines import (
    BaseEngine,
    CompositeEngine,
    CryptoEngine,
    EquityEngine,
    ForexEngine,
    FuturesEngine,
    create_engine,
    detect_market,
    detect_submarket,
    is_china_futures,
)
from quant_nanggroe.engine.backtest.execution import ExecutionConfig, ExecutionSimulator

# ── Data loaders ──
from quant_nanggroe.engine.backtest.loaders import (
    BaseLoader,
    CCXTLoader,
    NoAvailableSourceError,
    YFinanceLoader,
    validate_date_range,
)
from quant_nanggroe.engine.backtest.metrics import MetricsResult, PerformanceMetrics
from quant_nanggroe.engine.backtest.monte_carlo import (
    MonteCarloResult,
    MonteCarloSimulator,
    MultiMetricMonteCarloResult,
    RegimeInfo,
)

# ── Portfolio optimizers ──
from quant_nanggroe.engine.backtest.optimizers import (
    BaseOptimizer,
    EqualVolatilityOptimizer,
    MeanVarianceOptimizer,
    RiskParityOptimizer,
)
from quant_nanggroe.engine.backtest.portfolio import Portfolio, Position, TradeRecord
from quant_nanggroe.engine.backtest.report import BacktestReport
from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer, WalkForwardResult, WalkForwardStability

__all__ = [
    # Core
    "BacktestEngine",
    "BacktestConfig",
    "MarketType",
    "StrategyType",
    "Portfolio",
    "Position",
    "TradeRecord",
    "PerformanceMetrics",
    "MetricsResult",
    "ExecutionSimulator",
    "ExecutionConfig",
    "WalkForwardAnalyzer",
    "WalkForwardResult",
    "WalkForwardStability",
    "MonteCarloSimulator",
    "MonteCarloResult",
    "MultiMetricMonteCarloResult",
    "RegimeInfo",
    "BacktestReport",
    "BenchmarkManager",
    "BenchmarkResult",
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
