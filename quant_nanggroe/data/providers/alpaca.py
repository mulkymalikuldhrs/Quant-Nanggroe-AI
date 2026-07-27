"""Alpaca Markets data provider for US Equity data.

Implements the DataProvider interface for Alpaca's market data API.
Provides real-time and historical equity data via Alpaca's free tier.

Data source strategy (D-005):
- US Equity real-time: Alpaca (free with account) → fallback: Polygon
- US Equity historical: Polygon (full tick history)
- Alpaca is the primary real-time data source for US equities.

Extracted from Misi-Screener's Alpaca integration with production hardening.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)

# Timeframe mapping from our TimeFrame to Alpaca's bar timeframe strings
_TIMEFRAME_MAP: Dict[TimeFrame, str] = {
    TimeFrame.M1: "1Min",
    TimeFrame.M5: "5Min",
    TimeFrame.M15: "15Min",
    TimeFrame.M30: "30Min",
    TimeFrame.H1: "1Hour",
    TimeFrame.H4: "4Hour",
    TimeFrame.D1: "1Day",
    TimeFrame.W1: "1Week",
    TimeFrame.MO1: "1Month",
}


class AlpacaProvider(DataProvider):
    """Alpaca Markets data provider.

    Provides US equity data via Alpaca's market data API.
    Requires QNAI_ALPACA_API_KEY and QNAI_ALPACA_SECRET_KEY environment variables.

    Features:
    - Real-time and historical OHLCV data for US equities
    - Free tier: unlimited paper trading data, limited live data
    - Automatic failover when Alpaca is unavailable
    - Rate limit handling with backoff

    Example:
        >>> provider = AlpacaProvider(
        ...     api_key="your-key",
        ...     secret_key="your-secret",
        ...     paper=True,  # Use paper trading data
        ... )
        >>> candles = await provider.get_ohlcv("AAPL", TimeFrame.D1)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True,
        priority: int = 10,
        **kwargs,
    ):
        """Initialize Alpaca provider.

        Args:
            api_key: Alpaca API key. Falls back to QNAI_ALPACA_API_KEY env var.
            secret_key: Alpaca secret key. Falls back to QNAI_ALPACA_SECRET_KEY env var.
            paper: Use paper trading data endpoint (free, no rate limits).
            priority: Failover priority (lower = higher priority).
        """
        super().__init__(name="alpaca", priority=priority, **kwargs)

        self._api_key = api_key
        self._secret_key = secret_key
        self._paper = paper
        self._base_url = (
            "https://paper-data.alpaca.markets"
            if paper
            else "https://data.alpaca.markets"
        )
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Alpaca client."""
        if self._client is not None:
            return self._client

        try:
            from alpaca.data.historical.stock import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest

            api_key = self._api_key
            secret_key = self._secret_key

            if not api_key or not secret_key:
                import os
                api_key = os.environ.get("QNAI_ALPACA_API_KEY", "")
                secret_key = os.environ.get("QNAI_ALPACA_SECRET_KEY", "")

            if not api_key or not secret_key:
                raise ValueError(
                    "Alpaca API keys not configured. Set QNAI_ALPACA_API_KEY and "
                    "QNAI_ALPACA_SECRET_KEY environment variables or pass api_key/secret_key."
                )

            self._client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key,
            )
            return self._client

        except ImportError:
            raise ImportError(
                "alpaca-py is required for Alpaca data. "
                "Install with: pip install alpaca-py"
            )

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV candlestick data from Alpaca.

        Args:
            symbol: US equity symbol (e.g., 'AAPL', 'MSFT').
            timeframe: Candle timeframe.
            start: Start datetime.
            end: End datetime.
            limit: Maximum number of candles.

        Returns:
            List of OHLCV candles sorted by timestamp ascending.
        """
        try:
            client = self._get_client()

            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame as AlpacaTimeFrame

            # Map timeframe
            tf_map = {
                TimeFrame.M1: AlpacaTimeFrame.Minute,
                TimeFrame.M5: AlpacaTimeFrame.Minute,  # Will adjust
                TimeFrame.H1: AlpacaTimeFrame.Hour,
                TimeFrame.D1: AlpacaTimeFrame.Day,
                TimeFrame.W1: AlpacaTimeFrame.Week,
                TimeFrame.MO1: AlpacaTimeFrame.Month,
            }

            alpaca_tf = tf_map.get(timeframe, AlpacaTimeFrame.Day)

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=alpaca_tf,
                start=start or (datetime.now() - timedelta(days=365)),
                end=end or datetime.now(),
                limit=limit,
            )

            bars = client.get_stock_bars(request)

            if not bars or symbol not in bars:
                self.mark_error(f"No bars returned for {symbol}")
                return []

            result = []
            for bar in bars[symbol]:
                result.append(
                    OHLCV(
                        timestamp=bar.timestamp.isoformat() if bar.timestamp else "",
                        open=float(bar.open),
                        high=float(bar.high),
                        low=float(bar.low),
                        close=float(bar.close),
                        volume=float(bar.volume),
                    )
                )

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.error(f"Alpaca get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker data from Alpaca.

        Args:
            symbol: US equity symbol.

        Returns:
            Current ticker data or None if unavailable.
        """
        try:
            client = self._get_client()

            from alpaca.data.requests import StockLatestQuoteRequest

            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = client.get_stock_latest_quote(request)

            if not quotes or symbol not in quotes:
                self.mark_error(f"No quote for {symbol}")
                return None

            quote = quotes[symbol]
            self.mark_success()

            return Ticker(
                symbol=symbol,
                bid=float(quote.bid_price) if quote.bid_price else 0.0,
                ask=float(quote.ask_price) if quote.ask_price else 0.0,
                last=float(quote.ask_price or quote.bid_price or 0),
                volume=0,  # Not available from quote
                timestamp=quote.timestamp.isoformat() if quote.timestamp else "",
            )

        except Exception as e:
            self.mark_error(str(e))
            logger.error(f"Alpaca get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Fetch order book snapshot.

        Note: Alpaca does not provide Level 2 order book data through
        the standard data API. This returns None and the system should
        fall back to another provider.

        Args:
            symbol: US equity symbol.
            limit: Number of bid/ask levels.

        Returns:
            None - Alpaca doesn't provide order book data.
        """
        self.mark_error("Alpaca does not provide order book data")
        return None

    async def health_check(self) -> bool:
        """Check if the Alpaca API is accessible.

        Returns:
            True if the API responds successfully.
        """
        try:
            client = self._get_client()
            # Try fetching a minimal quote for a common symbol
            from alpaca.data.requests import StockLatestQuoteRequest

            request = StockLatestQuoteRequest(symbol_or_symbols="SPY")
            client.get_stock_latest_quote(request)
            self._is_available = True
            return True
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False
