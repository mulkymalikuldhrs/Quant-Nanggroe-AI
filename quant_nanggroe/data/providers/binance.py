"""Binance data provider.

Uses the ccxt library for Binance market data access.
Supports crypto spot and futures markets.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

import ccxt.async_support as ccxt

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, OrderBookLevel, Ticker, TimeFrame

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    TimeFrame.M1: "1m",
    TimeFrame.M5: "5m",
    TimeFrame.M15: "15m",
    TimeFrame.M30: "30m",
    TimeFrame.H1: "1h",
    TimeFrame.H4: "4h",
    TimeFrame.D1: "1d",
    TimeFrame.W1: "1w",
    TimeFrame.MO1: "1M",
}


class BinanceProvider(DataProvider):
    """
    Binance data provider using ccxt.

    Provides real-time and historical data for crypto markets.
    Requires API key for private endpoints; public data works without key.
    Priority: 1 (primary for crypto).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
        **kwargs,
    ):
        super().__init__(name="binance", priority=1, **kwargs)
        self._exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        if testnet:
            self._exchange.set_sandbox_mode(True)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from Binance."""
        try:
            interval = TIMEFRAME_MAP.get(timeframe, "1d")
            since = int(start.timestamp() * 1000) if start else None
            ohlcv_data = await self._exchange.fetch_ohlcv(
                symbol, interval, since=since, limit=limit
            )

            result = []
            for candle in ohlcv_data:
                ohlcv = OHLCV(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(candle[0] / 1000),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                )
                result.append(ohlcv)

            self.mark_success()
            return result

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance OHLCV error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker from Binance."""
        try:
            data = await self._exchange.fetch_ticker(symbol)
            t = Ticker(
                symbol=symbol,
                timestamp=datetime.now(),
                last_price=float(data.get("last", 0)),
                bid=float(data["bid"]) if data.get("bid") else None,
                ask=float(data["ask"]) if data.get("ask") else None,
                high_24h=float(data["high"]) if data.get("high") else None,
                low_24h=float(data["low"]) if data.get("low") else None,
                volume_24h=float(data["baseVolume"]) if data.get("baseVolume") else None,
                change_pct_24h=float(data["percentage"]) if data.get("percentage") else None,
                vwap=float(data["vwap"]) if data.get("vwap") else None,
            )
            self.mark_success()
            return t

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Fetch order book from Binance."""
        try:
            data = await self._exchange.fetch_order_book(symbol, limit=limit)
            bids = [OrderBookLevel(price=float(b[0]), quantity=float(b[1])) for b in data["bids"]]
            asks = [OrderBookLevel(price=float(a[0]), quantity=float(a[1])) for a in data["asks"]]

            spread = None
            mid_price = None
            if bids and asks:
                spread = asks[0].price - bids[0].price
                mid_price = (asks[0].price + bids[0].price) / 2

            ob = OrderBook(
                symbol=symbol,
                timestamp=datetime.now(),
                bids=bids,
                asks=asks,
                spread=spread,
                mid_price=mid_price,
            )
            self.mark_success()
            return ob

        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Binance orderbook error for {symbol}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check Binance connectivity."""
        try:
            await self._exchange.fetch_time()
            self._is_available = True
            return True
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False

    async def close(self) -> None:
        """Close the exchange connection."""
        await self._exchange.close()
