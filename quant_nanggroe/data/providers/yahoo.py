"""Yahoo Finance data provider.

Uses the yfinance library for free market data access.
Supports stocks, ETFs, forex, crypto, and futures.
No API key required — rate limited to ~2000 requests/hour.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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

# yfinance only supports certain intervals for certain period ranges
# Intraday data (1m, 5m, etc.) is only available for the last 60 days
_INTRADAY_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance data provider using yfinance.

    Provides free access to stock, ETF, forex, crypto, and futures data.
    Rate limited to ~2000 requests/hour. No API key required.

    Features:
    - Real OHLCV data with proper date ranges
    - Real price quotes (fast_info and info)
    - Real dividend and split data
    - Real earnings data (quarterly and annual)
    - Support for stocks, ETFs, crypto, forex, futures
    - Automatic period adjustment for intraday data

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
        """Fetch OHLCV data from Yahoo Finance.

        Handles intraday interval restrictions (yfinance only provides
        intraday data for the last 60 days).
        """
        try:
            interval = TIMEFRAME_MAP.get(timeframe, "1d")

            # For intraday intervals, yfinance requires recent date ranges
            if interval in _INTRADAY_INTERVALS:
                if start is None:
                    start = datetime.now() - timedelta(days=59)
                # If start is more than 60 days ago, clamp it
                max_start = datetime.now() - timedelta(days=59)
                if start < max_start:
                    logger.info(
                        f"Yahoo Finance: clamping intraday start date from "
                        f"{start.isoformat()} to {max_start.isoformat()}"
                    )
                    start = max_start

            # Run yfinance in thread pool since it's synchronous
            df = await asyncio.to_thread(
                self._fetch_history,
                symbol=symbol,
                interval=interval,
                start=start,
                end=end,
            )

            if df.empty:
                self.mark_error(f"No OHLCV data returned for {symbol}")
                return []

            result = []
            for idx, row in df.iterrows():
                try:
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
                except (ValueError, TypeError) as e:
                    logger.debug(f"Skipping invalid candle for {symbol}: {e}")
                    continue

            self.mark_success()
            return result[-limit:]

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance OHLCV error for {symbol}: {e}")
            return []

    @staticmethod
    def _fetch_history(
        symbol: str,
        interval: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ):
        """Fetch history from yfinance (synchronous — run in thread)."""
        ticker = yf.Ticker(symbol)
        kwargs = {"interval": interval}
        if start is not None:
            kwargs["start"] = start
        else:
            kwargs["period"] = "1mo"
        if end is not None:
            kwargs["end"] = end
        return ticker.history(**kwargs)

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker data from Yahoo Finance.

        Uses fast_info for real-time price data and info dict for
        additional fields like 52-week range, market cap, etc.
        """
        try:
            ticker_obj = yf.Ticker(symbol)

            # Fetch fast_info and info in thread
            fast_info, info = await asyncio.to_thread(
                self._fetch_ticker_info, ticker_obj
            )

            # Build ticker from fast_info + info
            last_price = getattr(fast_info, "last_price", None)
            if last_price is None:
                last_price = getattr(fast_info, "lastPrice", None)
            if last_price is None:
                last_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            if last_price is None or last_price <= 0:
                self.mark_error(f"Invalid last price for {symbol}")
                return None

            # Get 24h change from info
            prev_close = info.get("regularMarketPreviousClose") or getattr(fast_info, "previous_close", None)
            change_24h = None
            change_pct_24h = None
            if prev_close and prev_close > 0:
                change_24h = last_price - prev_close
                change_pct_24h = (change_24h / prev_close) * 100

            t = Ticker(
                symbol=symbol,
                timestamp=datetime.now(),
                last_price=float(last_price),
                bid=getattr(fast_info, "bid", None) or info.get("bid"),
                ask=getattr(fast_info, "ask", None) or info.get("ask"),
                high_24h=getattr(fast_info, "day_high", None) or info.get("dayHigh"),
                low_24h=getattr(fast_info, "day_low", None) or info.get("dayLow"),
                volume_24h=getattr(fast_info, "last_volume", None) or info.get("volume"),
                change_24h=change_24h,
                change_pct_24h=change_pct_24h,
                vwap=None,
            )
            self.mark_success()
            return t

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance ticker error for {symbol}: {e}")
            return None

    @staticmethod
    def _fetch_ticker_info(ticker_obj):
        """Fetch both fast_info and info from yfinance (synchronous)."""
        fast_info = ticker_obj.fast_info
        try:
            info = ticker_obj.info
        except Exception:
            info = {}
        return fast_info, info

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Yahoo Finance does not support order book data."""
        logger.debug("Yahoo Finance does not support order book data")
        return None

    async def get_dividends(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch dividend history from Yahoo Finance.

        Args:
            symbol: Stock/ETF symbol (e.g., 'AAPL', 'VOO').
            start: Start date filter.
            end: End date filter.

        Returns:
            List of dividend dicts with date, amount.
        """
        try:
            ticker_obj = yf.Ticker(symbol)
            divs = await asyncio.to_thread(lambda: ticker_obj.dividends)

            if divs is None or divs.empty:
                return []

            result = []
            for idx, value in divs.items():
                date = idx.to_pydatetime()
                if start and date < start:
                    continue
                if end and date > end:
                    continue
                result.append({
                    "symbol": symbol,
                    "date": date.isoformat(),
                    "amount": float(value),
                })

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance dividends error for {symbol}: {e}")
            return []

    async def get_splits(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch stock split history from Yahoo Finance.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'TSLA').
            start: Start date filter.
            end: End date filter.

        Returns:
            List of split dicts with date, ratio.
        """
        try:
            ticker_obj = yf.Ticker(symbol)
            splits = await asyncio.to_thread(lambda: ticker_obj.splits)

            if splits is None or splits.empty:
                return []

            result = []
            for idx, value in splits.items():
                date = idx.to_pydatetime()
                if start and date < start:
                    continue
                if end and date > end:
                    continue
                result.append({
                    "symbol": symbol,
                    "date": date.isoformat(),
                    "ratio": float(value),
                })

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance splits error for {symbol}: {e}")
            return []

    async def get_earnings(
        self,
        symbol: str,
        frequency: str = "annual",
    ) -> Dict[str, Any]:
        """Fetch earnings data from Yahoo Finance.

        Args:
            symbol: Stock symbol (e.g., 'AAPL').
            frequency: 'annual' or 'quarterly'.

        Returns:
            Dict with earnings data (revenue, earnings, dates).
        """
        try:
            ticker_obj = yf.Ticker(symbol)

            if frequency == "quarterly":
                financials = await asyncio.to_thread(lambda: ticker_obj.quarterly_financials)
                earnings_data = await asyncio.to_thread(lambda: ticker_obj.quarterly_earnings)
            else:
                financials = await asyncio.to_thread(lambda: ticker_obj.financials)
                earnings_data = await asyncio.to_thread(lambda: ticker_obj.earnings)

            result = {
                "symbol": symbol,
                "frequency": frequency,
                "financials": {},
                "earnings": {},
            }

            if financials is not None and not financials.empty:
                # Convert DataFrame to dict for serialization
                result["financials"] = financials.to_dict()

            if earnings_data is not None and not earnings_data.empty:
                result["earnings"] = earnings_data.to_dict()

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance earnings error for {symbol}: {e}")
            return {}

    async def get_info(self, symbol: str) -> Dict[str, Any]:
        """Fetch comprehensive company/asset info from Yahoo Finance.

        Returns market cap, P/E ratio, sector, industry, description,
        52-week range, and more.
        """
        try:
            ticker_obj = yf.Ticker(symbol)
            info = await asyncio.to_thread(lambda: ticker_obj.info)

            if not info:
                self.mark_error(f"No info returned for {symbol}")
                return {}

            self.mark_success()
            return info

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance info error for {symbol}: {e}")
            return {}

    async def get_recommendations(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch analyst recommendations from Yahoo Finance.

        Args:
            symbol: Stock symbol.

        Returns:
            List of recommendation dicts.
        """
        try:
            ticker_obj = yf.Ticker(symbol)
            recs = await asyncio.to_thread(lambda: ticker_obj.recommendations)

            if recs is None or (hasattr(recs, 'empty') and recs.empty):
                return []

            if hasattr(recs, "to_dict"):
                result = recs.to_dict("records")
            else:
                result = []

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Yahoo Finance recommendations error for {symbol}: {e}")
            return []

    async def health_check(self) -> bool:
        """Check Yahoo Finance connectivity."""
        try:
            df = await asyncio.to_thread(
                lambda: yf.Ticker("AAPL").history(period="1d")
            )
            self._is_available = not df.empty
            return self._is_available
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False
