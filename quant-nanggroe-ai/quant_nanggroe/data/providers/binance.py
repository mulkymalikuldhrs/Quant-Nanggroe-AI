"""Binance data provider using ccxt.

Provides crypto market data via the Binance exchange API.
Requires BINANCE_API_KEY and BINANCE_SECRET_KEY for authenticated access.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import (
    OHLCV,
    DataMetadata,
    Interval,
    OrderBook,
    OrderBookLevel,
    Ticker,
)
from quant_nanggroe.config.settings import get_settings

logger = logging.getLogger("quant_nanggroe.data.providers.binance")

_INTERVAL_MAP: dict[Interval, str] = {
    Interval.MIN_1: "1m",
    Interval.MIN_5: "5m",
    Interval.MIN_15: "15m",
    Interval.MIN_30: "30m",
    Interval.HOUR_1: "1h",
    Interval.HOUR_4: "4h",
    Interval.DAY_1: "1d",
    Interval.WEEK_1: "1w",
    Interval.MONTH_1: "1M",
}


class BinanceProvider(DataProvider):
    """Binance crypto data provider using the ccxt library.

    Supports spot and futures markets. API keys are optional
    for public data but required for account-specific operations.
    """

    def __init__(self) -> None:
        self._exchange = None

    def _get_exchange(self):
        """Lazy-initialize the ccxt Binance exchange."""
        if self._exchange is not None:
            return self._exchange

        try:
            import ccxt

            settings = get_settings()
            self._exchange = ccxt.binance(
                {
                    "apiKey": settings.binance_api_key or None,
                    "secret": settings.binance_secret_key or None,
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"},
                }
            )
            return self._exchange
        except Exception as e:
            logger.error(f"Binance ccxt init error: {e}")
            return None

    @property
    def name(self) -> str:
        return "binance"

    @property
    def is_available(self) -> bool:
        exchange = self._get_exchange()
        return exchange is not None

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV data from Binance."""
        exchange = self._get_exchange()
        if exchange is None:
            return []

        try:
            timeframe = _INTERVAL_MAP.get(interval, "1d")
            since = int(start.timestamp() * 1000) if start else None

            ohlcv_data = exchange.fetch_ohlcv(
                symbol, timeframe=timeframe, since=since, limit=limit
            )

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.95,
                latency_estimate_ms=50.0,
                update_frequency=timeframe,
                domain_type="market",
            )

            candles: list[OHLCV] = []
            for candle in ohlcv_data:
                ts, o, h, l, c, v = candle[:6]
                candle_time = datetime.fromtimestamp(ts / 1000)

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
                        volume=float(v),
                        interval=interval,
                        metadata=metadata,
                    )
                )

            return candles

        except Exception as e:
            logger.error(f"Binance get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch real-time ticker from Binance."""
        exchange = self._get_exchange()
        if exchange is None:
            return None

        try:
            ticker_data = exchange.fetch_ticker(symbol)
            metadata = DataMetadata(
                source=self.name,
                trust_score=0.95,
                latency_estimate_ms=50.0,
                update_frequency="realtime",
                domain_type="market",
            )

            return Ticker(
                symbol=symbol,
                current_price=float(ticker_data.get("last", 0)),
                price_change_24h=float(ticker_data.get("change", 0)),
                price_change_pct_24h=float(ticker_data.get("percentage", 0) or 0),
                high_24h=float(ticker_data.get("high", 0) or 0),
                low_24h=float(ticker_data.get("low", 0) or 0),
                volume_24h=float(ticker_data.get("quoteVolume", 0) or 0),
                bid=float(ticker_data.get("bid", 0) or 0),
                ask=float(ticker_data.get("ask", 0) or 0),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Binance get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(
        self,
        symbol: str,
        depth: int = 20,
    ) -> OrderBook:
        """Fetch order book from Binance."""
        exchange = self._get_exchange()
        if exchange is None:
            return OrderBook(
                symbol=symbol,
                timestamp=datetime.now(),
                bids=[],
                asks=[],
                metadata=DataMetadata(source=self.name, trust_score=0.0),
            )

        try:
            book = exchange.fetch_order_book(symbol, limit=depth)
            metadata = DataMetadata(
                source=self.name,
                trust_score=0.95,
                latency_estimate_ms=30.0,
                update_frequency="realtime",
                domain_type="market",
            )

            bids = [
                OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
                for b in book.get("bids", [])
            ]
            asks = [
                OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
                for a in book.get("asks", [])
            ]

            return OrderBook(
                symbol=symbol,
                timestamp=datetime.now(),
                bids=bids,
                asks=asks,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Binance get_orderbook error for {symbol}: {e}")
            return OrderBook(
                symbol=symbol,
                timestamp=datetime.now(),
                bids=[],
                asks=[],
                metadata=DataMetadata(source=self.name, trust_score=0.0),
            )
