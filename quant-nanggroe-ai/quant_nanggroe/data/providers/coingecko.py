"""CoinGecko data provider for cryptocurrency data.

Provides crypto market data via the CoinGecko API.
API key is optional (free tier has rate limits).
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

logger = logging.getLogger("quant_nanggroe.data.providers.coingecko")


class CoinGeckoProvider(DataProvider):
    """CoinGecko crypto data provider.

    Free tier: 10-30 calls/minute.
    Pro tier: 500+ calls/minute with API key.
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def name(self) -> str:
        return "coingecko"

    @property
    def is_available(self) -> bool:
        return True  # CoinGecko free tier doesn't require an API key

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV data from CoinGecko.

        CoinGecko uses coin IDs (e.g., 'bitcoin') not symbols.
        The symbol parameter should be a CoinGecko coin ID.
        """
        try:
            # CoinGecko OHLCV endpoint (max 365 days for free)
            url = f"{self.BASE_URL}/coins/{symbol}/ohlc"
            params = {"vs_currency": "usd", "days": min(limit, 365)}

            resp = await self._client.get(url, params=params)
            data = resp.json()

            if not isinstance(data, list):
                logger.warning(f"CoinGecko: No OHLCV data for {symbol}")
                return []

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.85,
                latency_estimate_ms=300.0,
                update_frequency="1d",
                domain_type="market",
            )

            candles: list[OHLCV] = []
            for item in data:
                ts, o, h, l, c = item[:5]
                candle_time = datetime.fromtimestamp(ts / 1000)

                if start and candle_time < start:
                    continue
                if end and candle_time > end:
                    continue

                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=candle_time,
                        open=float(o),
                        high=float(h),
                        low=float(l),
                        close=float(c),
                        volume=0.0,  # CoinGecko OHLCV doesn't include volume
                        interval=interval,
                        metadata=metadata,
                    )
                )

            return candles[-limit:]

        except Exception as e:
            logger.error(f"CoinGecko get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current price from CoinGecko."""
        try:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": symbol,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
            }

            resp = await self._client.get(url, params=params)
            data = resp.json()

            if symbol not in data:
                return None

            coin_data = data[symbol]
            metadata = DataMetadata(
                source=self.name,
                trust_score=0.85,
                latency_estimate_ms=300.0,
                update_frequency="realtime",
                domain_type="market",
            )

            return Ticker(
                symbol=symbol,
                current_price=float(coin_data.get("usd", 0)),
                price_change_pct_24h=float(coin_data.get("usd_24h_change", 0) or 0),
                volume_24h=float(coin_data.get("usd_24h_vol", 0) or 0),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"CoinGecko get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """CoinGecko does not support order book data."""
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=[],
            asks=[],
            metadata=DataMetadata(source=self.name, trust_score=0.0),
        )
