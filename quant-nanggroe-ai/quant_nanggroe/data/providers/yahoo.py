"""Yahoo Finance data provider using yfinance.

Provides free equity and crypto data. No API key required.
Used as the default/fallback provider for stock data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import (
    OHLCV,
    DataMetadata,
    Interval,
    OrderBook,
    OrderBookLevel,
    Ticker,
)

logger = logging.getLogger("quant_nanggroe.data.providers.yahoo")

# Map our Interval enum to yfinance interval strings
_INTERVAL_MAP: dict[Interval, str] = {
    Interval.MIN_1: "1m",
    Interval.MIN_5: "5m",
    Interval.MIN_15: "15m",
    Interval.MIN_30: "30m",
    Interval.HOUR_1: "1h",
    Interval.DAY_1: "1d",
    Interval.WEEK_1: "1wk",
    Interval.MONTH_1: "1mo",
}


class YahooProvider(DataProvider):
    """Yahoo Finance data provider powered by yfinance.

    Supports equities, ETFs, and some crypto pairs.
    No API key required — ideal for development and testing.
    """

    def __init__(self) -> None:
        self._available = True

    @property
    def name(self) -> str:
        return "yahoo"

    @property
    def is_available(self) -> bool:
        return self._available

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV data from Yahoo Finance."""
        try:
            import yfinance as yf

            yf_interval = _INTERVAL_MAP.get(interval, "1d")
            ticker = yf.Ticker(symbol)

            kwargs: dict = {"interval": yf_interval, "period": "max"}
            if start:
                kwargs["start"] = start.strftime("%Y-%m-%d")
            if end:
                kwargs["end"] = end.strftime("%Y-%m-%d")
            if not start and not end:
                # Use period instead
                kwargs.pop("start", None)
                kwargs.pop("end", None)
                kwargs["period"] = "1y"

            df: pd.DataFrame = ticker.history(**kwargs)

            if df.empty:
                logger.warning(f"Yahoo: No OHLCV data for {symbol}")
                return []

            # Apply limit
            if len(df) > limit:
                df = df.iloc[-limit:]

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.85,
                latency_estimate_ms=200.0,
                update_frequency=yf_interval,
                domain_type="market",
            )

            candles: list[OHLCV] = []
            for idx, row in df.iterrows():
                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=idx.to_pydatetime(),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row.get("Volume", 0)),
                        interval=interval,
                        metadata=metadata,
                    )
                )

            return candles

        except Exception as e:
            logger.error(f"Yahoo get_ohlcv error for {symbol}: {e}")
            self._available = False
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch real-time ticker from Yahoo Finance."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.fast_info

            current_price = getattr(info, "last_price", 0.0) or 0.0
            prev_close = getattr(info, "previous_close", 0.0) or 0.0

            price_change = current_price - prev_close if prev_close > 0 else 0.0
            price_change_pct = (price_change / prev_close * 100) if prev_close > 0 else 0.0

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.85,
                latency_estimate_ms=300.0,
                update_frequency="realtime",
                domain_type="market",
            )

            return Ticker(
                symbol=symbol,
                current_price=current_price,
                price_change_24h=price_change,
                price_change_pct_24h=price_change_pct,
                volume_24h=getattr(info, "last_volume", None),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Yahoo get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> OrderBook:
        """Yahoo Finance does not support order book data."""
        logger.warning(f"Yahoo: Order book not supported for {symbol}")
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=[],
            asks=[],
            metadata=DataMetadata(source=self.name, trust_score=0.0),
        )
