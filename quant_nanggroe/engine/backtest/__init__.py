"""Backtest engine: metrics, Monte Carlo, walk-forward, and reporting."""

# Package init

__all__ = [
    'auto_tune',
    'benchmarks',
    'cpcv',
    'engine',
    'execution',
    'fama_french',

    'metrics',
    'monte_carlo',
    'nautilus_adapter',
    'persistence',
    'portfolio',
    'psr',
    'report',
    'risk_models',
    'walk_forward',
]

from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloResult, MonteCarloSimulator

from . import auto_tune, benchmarks, cpcv, engine
from .engine import BacktestConfig, BacktestEngine, MarketType, StrategyType
from .metrics import MetricsResult, PerformanceMetrics
from .portfolio import TradeRecord

__all__ = ['BacktestEngine', 'BacktestConfig', 'MarketType', 'StrategyType', 'MetricsResult', 'PerformanceMetrics', 'TradeRecord', 'MonteCarloSimulator', 'MonteCarloResult']
from . import (
    execution,
    fama_french,
    metrics,
    monte_carlo,
    nautilus_adapter,
    persistence,
    portfolio,
    psr,
    report,
    risk_models,
    walk_forward,
)
