"""Abstract base class for market data providers.

All data providers must implement this interface to ensure
consistent data access across different sources.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from quant_nanggroe.types.market import OHLCV, MarketData, OrderBook, Ticker, TimeFrame


class DataProvider(ABC):
    """
    Abstract data provider interface.

    Every data source (Binance, Alpaca, Yahoo, etc.) must implement
    these methods. The DataProviderManager uses this interface to
    provide unified access with automatic failover.
    """

    def __init__(self, name: str, priority: int = 0, **kwargs):
        """
        Initialize the data provider.

        Args:
            name: Provider name (e.g., 'binance', 'alpaca')
            priority: Priority for failover (lower = higher priority)
            **kwargs: Provider-specific configuration
        """
        self._name = name
        self._priority = priority
        self._is_available = True
        self._last_error: Optional[str] = None
        self._request_count: int = 0
        self._error_count: int = 0

    @property
    def name(self) -> str:
        """Provider name."""
        return self._name

    @property
    def priority(self) -> int:
        """Failover priority (lower = higher priority)."""
        return self._priority

    @property
    def is_available(self) -> bool:
        """Whether the provider is currently available."""
        return self._is_available

    @property
    def last_error(self) -> Optional[str]:
        """Last error message from this provider."""
        return self._last_error

    @property
    def health_score(self) -> float:
        """Health score based on success rate (0.0-1.0)."""
        if self._request_count == 0:
            return 1.0
        return 1.0 - (self._error_count / self._request_count)

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """
        Fetch OHLCV candlestick data.

        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            start: Start datetime
            end: End datetime
            limit: Maximum number of candles

        Returns:
            List of OHLCV candles sorted by timestamp ascending
        """
        ...

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """
        Fetch current ticker data.

        Args:
            symbol: Trading pair symbol

        Returns:
            Current ticker data
        """
        ...

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """
        Fetch order book snapshot.

        Args:
            symbol: Trading pair symbol
            limit: Number of bid/ask levels

        Returns:
            Order book snapshot
        """
        ...

    async def get_market_data(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        include_ohlcv: bool = True,
        include_ticker: bool = True,
        include_orderbook: bool = False,
    ) -> MarketData:
        """
        Fetch aggregated market data for a symbol.

        Args:
            symbol: Trading pair symbol
            timeframe: Candle timeframe
            include_ohlcv: Whether to include OHLCV data
            include_ticker: Whether to include ticker data
            include_orderbook: Whether to include order book data

        Returns:
            Aggregated MarketData object
        """
        ohlcv = await self.get_ohlcv(symbol, timeframe) if include_ohlcv else []
        ticker = await self.get_ticker(symbol) if include_ticker else None
        orderbook = await self.get_orderbook(symbol) if include_orderbook else None

        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            ohlcv=ohlcv,
            ticker=ticker,
            orderbook=orderbook,
            provider=self._name,
        )

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and responsive."""
        ...

    def mark_error(self, error: str) -> None:
        """Record an error from this provider."""
        self._last_error = error
        self._error_count += 1
        self._request_count += 1
        if self.health_score < 0.5:
            self._is_available = False

    def mark_success(self) -> None:
        """Record a successful request."""
        self._request_count += 1

    def reset(self) -> None:
        """Reset error counts and restore availability."""
        self._is_available = True
        self._last_error = None

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name={self._name}, "
            f"priority={self._priority}, available={self._is_available})"
        )
