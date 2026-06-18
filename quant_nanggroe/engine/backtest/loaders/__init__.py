"""Data loaders for backtesting.

Provides data loading from multiple sources:
  - BaseLoader: Abstract base with retry/budget helpers
  - YFinanceLoader: US/HK equity data via Yahoo Finance
  - CCXTLoader: Crypto data via CCXT (100+ exchanges)

Ported from Vibe-Trading's loader architecture.
"""

from quant_nanggroe.engine.backtest.loaders.base_loader import (
    BaseLoader,
    NoAvailableSourceError,
    validate_date_range,
    check_budget,
    retry_with_budget,
)
from quant_nanggroe.engine.backtest.loaders.yfinance_loader import YFinanceLoader
from quant_nanggroe.engine.backtest.loaders.ccxt_loader import CCXTLoader

__all__ = [
    "BaseLoader",
    "NoAvailableSourceError",
    "validate_date_range",
    "check_budget",
    "retry_with_budget",
    "YFinanceLoader",
    "CCXTLoader",
]
