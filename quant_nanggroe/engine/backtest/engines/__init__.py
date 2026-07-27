"""Backtest engines: crypto, equity, forex, and futures."""

# Package init

__all__ = [
    'base_engine',
    'composite_engine',
    'crypto_engine',
    'equity_engine',
    'forex_engine',
    'futures_engine',
    'market_detection',
]

from . import (
    base_engine,
    composite_engine,
    crypto_engine,
    equity_engine,
    forex_engine,
    futures_engine,
    market_detection,
)
