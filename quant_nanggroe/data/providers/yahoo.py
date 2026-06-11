"""Yahoo Finance data provider.

Uses the yfinance library for free market data access.
Supports stocks, ETFs, forex, and crypto pairs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

import yfinance as yf

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    TimeFrame.M1: "1m",
    TimeFrame.M5: "5m",
    TimeFrame.M15: "15m",
    TimeFrame.M30: "30m",
    TimeFrame.H1: "1h",
    TimeFrame.H4: "4h",
    TimeFrame.D1: "1d",
    TimeFrame.W1: "1wk",
    TimeFrame.MO1: "1mo",
}


class YahooFinanceProvider(DataProvider):
    """
    Yahoo Finance data provider using yfinance.

    Provides free access to stock, ETF, forex, and crypto data.
    Rate limited to ~2000 requests/hour. No API key required.
    Priority: 10 (secondary fallback after exchange APIs).
    """

    def __init__(self, **kwargs):
        super().__init__(name="yahoo", priority=10, **kwargs)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from Yahoo Finance."""
        try:
            interval = TIMEFRAME_MAP.get(timeframe, "1d")
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                period="1mo" if start is None else None,
                start=start,
                end=end,
                interval=interval,
            )
            if df.empty:
                return []

            result = []
            for idx, row in df.iterrows():
                candle = OHLCV(
                    symbol=symbol,
                    timestamp=idx.to_pydatetime(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                )
                result.append(candle)

            self.mark_success()
            return result[-limit:]

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance OHLCV error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker data from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info

            t = Ticker(
                symbol=symbol,
                timestamp=datetime.now(),
                last_price=info.get("lastPrice", 0),
                high_24h=info.get("dayHigh"),
                low_24h=info.get("dayLow"),
                volume_24h=info.get("volume"),
                change_24h=info.get("regularMarketPreviousClose"),
            )
            self.mark_success()
            return t

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Yahoo Finance does not support order book data."""
        logger.debug("Yahoo Finance does not support order book data")
        return None

    async def health_check(self) -> bool:
        """Check Yahoo Finance connectivity."""
        try:
            ticker = yf.Ticker("AAPL")
            hist = ticker.history(period="1d")
            self._is_available = not hist.empty
            return self._is_available
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False
