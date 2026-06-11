"""Alpaca data provider for US equities.

Provides real-time and historical equity data via the Alpaca Markets API.
Requires ALPACA_API_KEY and ALPACA_SECRET_KEY.
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

logger = logging.getLogger("quant_nanggroe.data.providers.alpaca")

_INTERVAL_MAP: dict[Interval, str] = {
    Interval.MIN_1: "1Min",
    Interval.MIN_5: "5Min",
    Interval.MIN_15: "15Min",
    Interval.MIN_30: "30Min",
    Interval.HOUR_1: "1Hour",
    Interval.DAY_1: "1Day",
    Interval.WEEK_1: "1Week",
    Interval.MONTH_1: "1Month",
}


class AlpacaProvider(DataProvider):
    """Alpaca Markets data provider for US equities.

    Supports stocks and crypto. Requires API credentials
    configured via environment variables.
    """

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Alpaca trade client."""
        if self._client is not None:
            return self._client

        try:
            import alpaca_trade_api as tradeapi

            settings = get_settings()
            self._client = tradeapi.REST(
                key_id=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                base_url="https://paper-api.alpaca.markets",
                api_version="v2",
            )
            return self._client
        except Exception as e:
            logger.error(f"Alpaca init error: {e}")
            return None

    @property
    def name(self) -> str:
        return "alpaca"

    @property
    def is_available(self) -> bool:
        settings = get_settings()
        return bool(settings.alpaca_api_key and settings.alpaca_secret_key)

    async def get_ohlcv(
        self,
        symbol: str,
        interval: Interval = Interval.DAY_1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[OHLCV]:
        """Fetch OHLCV data from Alpaca."""
        client = self._get_client()
        if client is None:
            return []

        try:
            timeframe = _INTERVAL_MAP.get(interval, "1Day")
            bars = client.get_bars(
                symbol,
                timeframe,
                start=start.isoformat() if start else None,
                end=end.isoformat() if end else None,
                limit=limit,
            )

            metadata = DataMetadata(
                source=self.name,
                trust_score=0.90,
                latency_estimate_ms=100.0,
                update_frequency=timeframe,
                domain_type="market",
            )

            candles: list[OHLCV] = []
            for bar in bars:
                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=bar.t.to_pydatetime() if hasattr(bar.t, "to_pydatetime") else bar.t,
                        open=float(bar.o),
                        high=float(bar.h),
                        low=float(bar.l),
                        close=float(bar.c),
                        volume=float(bar.v),
                        interval=interval,
                        metadata=metadata,
                    )
                )

            return candles

        except Exception as e:
            logger.error(f"Alpaca get_ohlcv error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch real-time quote from Alpaca."""
        client = self._get_client()
        if client is None:
            return None

        try:
            quote = client.get_latest_quote(symbol)
            metadata = DataMetadata(
                source=self.name,
                trust_score=0.90,
                latency_estimate_ms=100.0,
                update_frequency="realtime",
                domain_type="market",
            )

            return Ticker(
                symbol=symbol,
                current_price=float(quote.ask_price if hasattr(quote, "ask_price") else quote.ask),
                bid=float(quote.bid_price if hasattr(quote, "bid_price") else quote.bid),
                ask=float(quote.ask_price if hasattr(quote, "ask_price") else quote.ask),
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Alpaca get_ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """Alpaca does not provide order book data for equities."""
        logger.warning(f"Alpaca: Order book not supported for {symbol}")
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=[],
            asks=[],
            metadata=DataMetadata(source=self.name, trust_score=0.0),
        )
