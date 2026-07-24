"""Backtest engine: strategy factory, backtester, and runner."""

# QNA Backtest Engine — Strategy Factory + Backtester + Selector
from .strategy_factory import StrategyFactory, StrategyVariant
from .backtester import Backtester, BacktestResult, DataFetcher
from .runner import BacktestRunner
