"""Abstract base class for data providers.

All data providers (Yahoo, Binance, Alpaca, etc.) must implement
this interface. The DataProviderManager uses this abstraction to
support failover and provider-agnostic data access.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pandas as pd

from quant_nanggroe.types.market import OHLCV, Ticker, OrderBook, Interval


class DataProvider(ABC):
    """Abstract data provider interface.

    Each provider must implement:
    - ``get_ohlcv``: Historical OHLCV candle data
    - ``get_ticker``: Real-time ticker / quote
    - ``get_orderbook``: Order book snapshot
    - ``get_fundamentals``: Fundamental data (optional)

    All methods are async to support concurrent data fetching.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and identification."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is currently available.

        Returns:
            True if the provider can serve requests, False otherwise.
        """

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV candle data.

        Args:
            symbol: Trading pair / ticker symbol.
            interval: Candle interval.
            start: Start datetime (UTC). If None, uses ``limit`` from now.
            end: End datetime (UTC). If None, uses current time.
            limit: Maximum number of candles to return.

        Returns:
            List of OHLCV candles sorted by timestamp ascending.
        """

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Fetch real-time ticker data.

        Args:
            symbol: Trading pair / ticker symbol.

        Returns:
            Current ticker data.
        """

    @abstractmethod
    async def get_orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> OrderBook:
        """Fetch order book snapshot.

        Args:
            symbol: Trading pair / ticker symbol.
            depth: Number of price levels per side.

        Returns:
            Order book snapshot.
        """

    async def get_fundamentals(self, symbol: str) -> dict:
        """Fetch fundamental data for a symbol.

        Default implementation returns empty dict; override if
        the provider supports fundamentals.

        Args:
            symbol: Ticker symbol.

        Returns:
            Dictionary of fundamental metrics.
        """
        return {}

    async def health_check(self) -> bool:
        """Perform a lightweight health check.

        Returns:
            True if the provider responds successfully.
        """
        try:
            _ = self.is_available
            return True
        except Exception:
            return False
