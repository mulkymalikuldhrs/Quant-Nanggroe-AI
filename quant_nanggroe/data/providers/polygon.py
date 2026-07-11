"""Polygon.io data provider for production-grade US Equity data.

Implements the DataProvider interface for Polygon's market data API.
Provides comprehensive historical and real-time data with 99.9% SLA.

Data source strategy (D-005):
- US Equity historical: Polygon (full tick history)
- Fallback for real-time when Alpaca is unavailable

Polygon provides:
- Full tick-level historical data
- 99.9% uptime SLA
- Options, forex, and crypto data
- $29/month for starter tier
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, MarketData, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)

# Timeframe mapping from our TimeFrame to Polygon's timespan strings
_TIMESPAN_MAP: Dict[TimeFrame, str] = {
    TimeFrame.M1: "minute",
    TimeFrame.M5: "minute",
    TimeFrame.M15: "minute",
    TimeFrame.M30: "minute",
    TimeFrame.H1: "hour",
    TimeFrame.H4: "hour",
    TimeFrame.D1: "day",
    TimeFrame.W1: "week",
    TimeFrame.MO1: "month",
}

# Multiplier for Polygon's aggregate bars
_MULTIPLIER_MAP: Dict[TimeFrame, int] = {
    TimeFrame.M1: 1,
    TimeFrame.M5: 5,
    TimeFrame.M15: 15,
    TimeFrame.M30: 30,
    TimeFrame.H1: 1,
    TimeFrame.H4: 4,
    TimeFrame.D1: 1,
    TimeFrame.W1: 1,
    TimeFrame.MO1: 1,
}


class PolygonProvider(DataProvider):
    """Polygon.io data provider.

    Provides US equity data via Polygon's REST API.
    Requires QNAI_POLYGON_API_KEY environment variable.

    Features:
    - Full tick-level historical data (starter plan and above)
    - 99.9% uptime SLA
    - Real-time data with WebSocket support
    - Options, forex, and crypto data on higher plans
    - Automatic rate limit handling

    Example:
        >>> provider = PolygonProvider(api_key="your-key")
        >>> candles = await provider.get_ohlcv("AAPL", TimeFrame.D1)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        priority: int = 20,
        **kwargs,
    ):
        """Initialize Polygon provider.

        Args:
            api_key: Polygon API key. Falls back to QNAI_POLYGON_API_KEY env var.
            priority: Failover priority (lower = higher priority). Default 20 (after Alpaca).
        """
        super().__init__(name="polygon", priority=priority, **kwargs)
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Polygon client."""
        if self._client is not None:
            return self._client

        try:
            from polygon import RESTClient

            api_key = self._api_key
            if not api_key:
                import os
                api_key = os.environ.get("QNAI_POLYGON_API_KEY", "")

            if not api_key:
                raise ValueError(
                    "Polygon API key not configured. Set QNAI_POLYGON_API_KEY "
                    "environment variable or pass api_key."
                )

            self._client = RESTClient(api_key=api_key)
            return self._client

        except ImportError:
            raise ImportError(
                "polygon-api-client is required for Polygon data. "
                "Install with: pip install polygon-api-client"
            )

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV candlestick data from Polygon.

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

            multiplier = _MULTIPLIER_MAP.get(timeframe, 1)
            timespan = _TIMESPAN_MAP.get(timeframe, "day")

            start_str = (start or datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            end_str = (end or datetime.now()).strftime("%Y-%m-%d")

            bars = client.list_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=start_str,
                to=end_str,
                limit=limit,
            )

            if not bars:
                self.mark_error(f"No bars returned for {symbol}")
                return []

            result = []
            for bar in bars:
                ts = datetime.fromtimestamp(bar.timestamp / 1000).isoformat() if bar.timestamp else ""
                result.append(
                    OHLCV(
                        timestamp=ts,
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
            logger.error(f"Polygon get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker data from Polygon.

        Args:
            symbol: US equity symbol.

        Returns:
            Current ticker data or None if unavailable.
        """
        try:
            client = self._get_client()

            snapshot = client.get_snapshot_ticker(symbol)

            if not snapshot:
                self.mark_error(f"No snapshot for {symbol}")
                return None

            self.mark_success()

            last_price = 0.0
            if hasattr(snapshot, "last_trade") and snapshot.last_trade:
                last_price = float(snapshot.last_trade.price or 0)
            elif hasattr(snapshot, "last_quote") and snapshot.last_quote:
                last_price = float(snapshot.last_quote.ask or snapshot.last_quote.bid or 0)

            bid = 0.0
            ask = 0.0
            if hasattr(snapshot, "last_quote") and snapshot.last_quote:
                bid = float(snapshot.last_quote.bid or 0)
                ask = float(snapshot.last_quote.ask or 0)

            volume = 0
            if hasattr(snapshot, "day") and snapshot.day:
                volume = int(snapshot.day.volume or 0)

            return Ticker(
                symbol=symbol,
                bid=bid,
                ask=ask,
                last=last_price,
                volume=volume,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            self.mark_error(str(e))
            logger.error(f"Polygon get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Fetch order book snapshot.

        Note: Polygon Level 2 data requires a premium subscription.
        This returns None for basic plans.

        Args:
            symbol: US equity symbol.
            limit: Number of bid/ask levels.

        Returns:
            None - Level 2 data requires premium subscription.
        """
        self.mark_error("Polygon Level 2 order book requires premium subscription")
        return None

    async def health_check(self) -> bool:
        """Check if the Polygon API is accessible.

        Returns:
            True if the API responds successfully.
        """
        try:
            client = self._get_client()
            # Try a minimal query
            client.get_snapshot_ticker("SPY")
            self._is_available = True
            return True
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False
