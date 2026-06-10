"""Polygon.io data provider for equities, forex, and crypto.

Provides institutional-grade market data via Polygon.io API.
Requires POLYGON_API_KEY.
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

logger = logging.getLogger("quant_nanggroe.data.providers.polygon")

_INTERVAL_MAP: dict[Interval, str] = {
    Interval.MIN_1: "1",
    Interval.MIN_5: "5",
    Interval.MIN_15: "15",
    Interval.MIN_30: "30",
    Interval.HOUR_1: "60",
    Interval.DAY_1: "day",
    Interval.WEEK_1: "week",
    Interval.MONTH_1: "month",
}


class PolygonProvider(DataProvider):
    """Polygon.io data provider for institutional-grade market data.

    Supports stocks, crypto, forex, and indices.
    Requires API key — free tier has 15-minute delayed data.
    """

    BASE_URL = "https://api.polygon.io"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def name(self) -> str:
        return "polygon"

    @property
    def is_available(self) -> bool:
        return bool(get_settings().polygon_api_key)

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV data from Polygon.io."""
        api_key = get_settings().polygon_api_key
        if not api_key:
            return []

        try:
            timespan = _INTERVAL_MAP.get(interval, "day")
            url = f"{self.BASE_URL}/v2/aggs/ticker/{symbol}/range/1/{timespan}/"

            from_date = start.strftime("%Y-%m-%d") if start else "2023-01-01"
            to_date = end.strftime("%Y-%m-%d") if end else datetime.now().strftime("%Y-%m-%d")

            params = {
                "adjusted": "true",
                "sort": "asc",
                "limit": limit,
                "apiKey": api_key,
            }

            url = f"{self.BASE_URL}/v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_date}/{to_date}"
            resp = await self._client.get(url, params=params)
            data = resp.json()

            results = data.get("results", [])
            if not results:
                logger.warning(f"Polygon: No OHLCV data for {symbol}")
                return []

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.92,
                latency_estimate_ms=80.0,
                update_frequency=timespan,
                domain_type="market",
            )

            candles: list[OHLCV] = []
            for item in results:
                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(item["t"] / 1000),
                        open=float(item["o"]),
                        high=float(item["h"]),
                        low=float(item["l"]),
                        close=float(item["c"]),
                        volume=float(item.get("v", 0)),
                        interval=interval,
                        metadata=metadata,
                    )
                )

            return candles

        except Exception as e:
            logger.error(f"Polygon get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch latest trade from Polygon.io."""
        api_key = get_settings().polygon_api_key
        if not api_key:
            return None

        try:
            url = f"{self.BASE_URL}/v2/aggs/ticker/{symbol}/prev"
            params = {"adjusted": "true", "apiKey": api_key}

            resp = await self._client.get(url, params=params)
            data = resp.json()

            results = data.get("results", [])
            if not results:
                return None

            item = results[0]
            metadata = DataMetadata(
                source=self.name,
                trust_score=0.92,
                latency_estimate_ms=80.0,
                update_frequency="realtime",
                domain_type="market",
            )

            return Ticker(
                symbol=symbol,
                current_price=float(item["c"]),
                volume_24h=float(item.get("v", 0)),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Polygon get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """Polygon.io does not support order book via REST."""
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=[],
            asks=[],
            metadata=DataMetadata(source=self.name, trust_score=0.0),
        )
