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

from . import auto_tune
from . import benchmarks
from . import cpcv
from . import engine
from .engine import BacktestEngine, BacktestConfig
from .engine import MarketType, StrategyType
from .metrics import MetricsResult, PerformanceMetrics
from .portfolio import TradeRecord
from quant_nanggroe.engine.backtest.monte_carlo import MonteCarloSimulator, MonteCarloResult

__all__ = ['BacktestEngine', 'BacktestConfig', 'MarketType', 'StrategyType', 'MetricsResult', 'PerformanceMetrics', 'TradeRecord', 'MonteCarloSimulator', 'MonteCarloResult']
from . import execution
from . import fama_french
from . import metrics
from . import monte_carlo
from . import nautilus_adapter
from . import persistence
from . import portfolio
from . import psr
from . import report
from . import risk_models
from . import walk_forward
