"""FRED (Federal Reserve Economic Data) provider.

Provides macroeconomic data from the Federal Reserve Bank of St. Louis.
Requires FRED_API_KEY.
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

logger = logging.getLogger("quant_nanggroe.data.providers.fred")

# Common FRED series IDs
FRED_SERIES = {
    "DFF": "Federal Funds Effective Rate",
    "DGS10": "10-Year Treasury",
    "DGS2": "2-Year Treasury",
    "T10Y2Y": "10Y-2Y Spread",
    "CPIAUCSL": "CPI (All Urban)",
    "UNRATE": "Unemployment Rate",
    "GDP": "GDP",
    "VIXCLS": "VIX",
    "BAMLH0A0HYM2": "High Yield Spread",
}


class FREDProvider(DataProvider):
    """FRED economic data provider.

    Provides macroeconomic indicators from the Federal Reserve.
    Not a market data provider — returns economic time series.
    """

    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def name(self) -> str:
        return "fred"

    @property
    def is_available(self) -> bool:
        return bool(get_settings().fred_api_key)

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch economic time series as OHLCV from FRED.

        FRED data is represented as OHLCV where open=high=low=close=value.
        """
        api_key = get_settings().fred_api_key
        if not api_key:
            return []

        try:
            url = f"{self.BASE_URL}/series/observations"
            params = {
                "series_id": symbol,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            }

            if start:
                params["observation_start"] = start.strftime("%Y-%m-%d")
            if end:
                params["observation_end"] = end.strftime("%Y-%m-%d")

            resp = await self._client.get(url, params=params)
            data = resp.json()

            observations = data.get("observations", [])
            if not observations:
                return []

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.98,
                latency_estimate_ms=500.0,
                update_frequency="1d",
                domain_type="macro",
            )

            candles: list[OHLCV] = []
            for obs in reversed(observations):
                value = obs.get("value", ".")
                if value == ".":
                    continue

                val = float(value)
                candle_time = datetime.strptime(obs["date"], "%Y-%m-%d")

                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=candle_time,
                        open=val,
                        high=val,
                        low=val,
                        close=val,
                        volume=0.0,
                        interval=Interval.DAY_1,
                        metadata=metadata,
                    )
                )

            return candles

        except Exception as e:
            logger.error(f"FRED get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch latest observation from FRED."""
        api_key = get_settings().fred_api_key
        if not api_key:
            return None

        try:
            url = f"{self.BASE_URL}/series/observations"
            params = {
                "series_id": symbol,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            }

            resp = await self._client.get(url, params=params)
            data = resp.json()

            observations = data.get("observations", [])
            if not observations:
                return None

            obs = observations[0]
            value = obs.get("value", ".")
            if value == ".":
                return None

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.98,
                latency_estimate_ms=500.0,
                update_frequency="1d",
                domain_type="macro",
            )

            return Ticker(
                symbol=symbol,
                name=FRED_SERIES.get(symbol, symbol),
                current_price=float(value),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"FRED get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """FRED does not support order book data."""
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=[],
            asks=[],
            metadata=DataMetadata(source=self.name, trust_score=0.0),
        )

    async def get_fundamentals(self, symbol: str) -> dict:
        """Fetch series metadata from FRED."""
        api_key = get_settings().fred_api_key
        if not api_key:
            return {}

        try:
            url = f"{self.BASE_URL}/series"
            params = {
                "series_id": symbol,
                "api_key": api_key,
                "file_type": "json",
            }

            resp = await self._client.get(url, params=params)
            data = resp.json()

            series_list = data.get("seriess", [])
            if not series_list:
                return {}

            s = series_list[0]
            return {
                "id": s.get("id"),
                "title": s.get("title"),
                "frequency": s.get("frequency"),
                "units": s.get("units"),
                "seasonal_adjustment": s.get("seasonal_adjustment"),
                "observation_start": s.get("observation_start"),
                "observation_end": s.get("observation_end"),
            }

        except Exception as e:
            logger.error(f"FRED get_fundamentals error for {symbol}: {e}")
            return {}
