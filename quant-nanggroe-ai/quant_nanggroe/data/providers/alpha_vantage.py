"""Alpha Vantage data provider.

Provides equity, forex, and crypto data via Alpha Vantage API.
Requires ALPHA_VANTAGE_API_KEY.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import (
    OHLCV,
    DataMetadata,
    Interval,
    OrderBook,
    Ticker,
)
from quant_nanggroe.config.settings import get_settings

logger = logging.getLogger("quant_nanggroe.data.providers.alpha_vantage")


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider for equities, forex, and crypto.

    Rate limited to 25 requests/day (free tier) or 75/min (premium).
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def name(self) -> str:
        return "alpha_vantage"

    @property
    def is_available(self) -> bool:
        return bool(get_settings().alpha_vantage_api_key)

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV data from Alpha Vantage."""
        api_key = get_settings().alpha_vantage_api_key
        if not api_key:
            return []

        try:
            # Use TIME_SERIES_DAILY for daily data
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "full" if limit > 100 else "compact",
                "apikey": api_key,
            }

            resp = await self._client.get(self.BASE_URL, params=params)
            data = resp.json()

            time_series_key = "Time Series (Daily)"
            if time_series_key not in data:
                logger.warning(f"Alpha Vantage: No data for {symbol}")
                return []

            time_series = data[time_series_key]
            metadata = DataMetadata(
                source=self.name,
                trust_score=0.80,
                latency_estimate_ms=500.0,
                update_frequency="1d",
                domain_type="market",
            )

            candles: list[OHLCV] = []
            for date_str, values in sorted(time_series.items(), reverse=True):
                candle_time = datetime.strptime(date_str, "%Y-%m-%d")

                if end and candle_time > end:
                    continue
                if start and candle_time < start:
                    continue

                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=candle_time,
                        open=float(values["1. open"]),
                        high=float(values["2. high"]),
                        low=float(values["3. low"]),
                        close=float(values["4. close"]),
                        volume=float(values["5. volume"]),
                        interval=Interval.DAY_1,
                        metadata=metadata,
                    )
                )

                if len(candles) >= limit:
                    break

            candles.reverse()
            return candles

        except Exception as e:
            logger.error(f"Alpha Vantage get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch global quote from Alpha Vantage."""
        api_key = get_settings().alpha_vantage_api_key
        if not api_key:
            return None

        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": api_key,
            }
            resp = await self._client.get(self.BASE_URL, params=params)
            data = resp.json()

            quote = data.get("Global Quote", {})
            if not quote:
                return None

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.80,
                latency_estimate_ms=500.0,
                update_frequency="realtime",
                domain_type="market",
            )

            current_price = float(quote.get("05. price", 0))
            prev_close = float(quote.get("08. previous close", 0))
            change = float(quote.get("09. change", 0))
            change_pct = float(quote.get("10. change percent", "0").replace("%", ""))

            return Ticker(
                symbol=symbol,
                current_price=current_price,
                price_change_24h=change,
                price_change_pct_24h=change_pct,
                volume_24h=float(quote.get("06. volume", 0)),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """Alpha Vantage does not support order book data."""
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=[],
            asks=[],
            metadata=DataMetadata(source=self.name, trust_score=0.0),
        )
