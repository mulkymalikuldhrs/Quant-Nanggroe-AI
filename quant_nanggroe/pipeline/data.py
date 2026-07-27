"""
Unified Data Provider
=====================
Provides a single interface for price/klines data across all asset classes.
Delegates to:
  - EnginePriceProvider (engine_bridge.py) for crypto
  - hedge_fund utils (get_historical_mt5, etc.) for forex
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

log = logging.getLogger("QNA-Pipeline-Data")


class UnifiedDataProvider:
    """Single data provider that delegates to the right backend per asset class."""

    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self._engine_provider: Any = None
        self._cache: dict[str, tuple[float, Any]] = {}

    def _get_engine_provider(self):
        if self._engine_provider is not None:
            return self._engine_provider
        try:
            from quant_nanggroe.engine_bridge import EnginePriceProvider
            self._engine_provider = EnginePriceProvider(cache_ttl=self.cache_ttl)
        except Exception as e:
            log.debug("EnginePriceProvider unavailable: %s", e)
            self._engine_provider = None
        return self._engine_provider

    def _cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is not None and (time.time() - entry[0]) < self.cache_ttl:
            return entry[1]
        return None

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = (time.time(), value)

    def get_price(self, symbol: str) -> Optional[float]:
        cache_key = f"price:{symbol}"
        cached = self._cached(cache_key)
        if cached is not None:
            return cached

        provider = self._get_engine_provider()
        if provider is not None:
            price = provider.get_price(symbol)
            if price is not None and price > 0:
                self._set_cache(cache_key, price)
                return price

        try:
            from quant_nanggroe.hedge_fund.hedge_fund import get_historical_mt5
            rates = get_historical_mt5(symbol, count=1)
            if rates and len(rates) > 0:
                price = float(rates[0].close if hasattr(rates[0], "close") else rates[0].get("close", 0))
                if price > 0:
                    self._set_cache(cache_key, price)
                    return price
        except Exception as e:
            log.debug("get_historical_mt5 price fail for %s: %s", symbol, e)

        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if data is not None and not data.empty:
                price = float(data["Close"].iloc[-1])
                if price > 0:
                    self._set_cache(cache_key, price)
                    return price
        except Exception:
            pass

        return None

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> list[dict]:
        cache_key = f"klines:{symbol}:{interval}:{limit}"
        cached = self._cached(cache_key)
        if cached is not None:
            return cached

        provider = self._get_engine_provider()
        if provider is not None:
            try:
                candles = provider.get_klines(symbol, interval=interval, limit=limit)
                if candles and len(candles) > 0:
                    self._set_cache(cache_key, candles)
                    return candles
            except Exception as e:
                log.debug("EnginePriceProvider klines fail for %s: %s", symbol, e)

        try:
            from quant_nanggroe.hedge_fund.hedge_fund import get_historical_mt5
            mt5_interval = self._interval_to_mt5tf(interval)
            rates = get_historical_mt5(symbol, timeframe=mt5_interval, count=limit)
            if rates and len(rates) > 0:
                candles = []
                for r in rates:
                    if hasattr(r, "_asdict"):
                        r = r._asdict()
                    candles.append({
                        "timestamp": int(r.get("time", r.get("timestamp", 0))),
                        "open": float(r.get("open", 0)),
                        "high": float(r.get("high", 0)),
                        "low": float(r.get("low", 0)),
                        "close": float(r.get("close", 0)),
                        "volume": float(r.get("volume", 0)),
                        "tick_volume": float(r.get("tick_volume", 0)),
                        "spread": int(r.get("spread", 0)),
                    })
                if candles:
                    self._set_cache(cache_key, candles)
                    return candles
        except Exception as e:
            log.debug("MT5 klines fail for %s: %s", symbol, e)

        return []

    def get_all_prices(self) -> dict[str, float]:
        cache_key = "all_prices"
        cached = self._cached(cache_key)
        if cached is not None:
            return cached

        provider = self._get_engine_provider()
        if provider is not None:
            try:
                prices = provider.get_all_prices()
                if prices:
                    self._set_cache(cache_key, prices)
                    return prices
            except Exception as e:
                log.debug("get_all_prices fail: %s", e)

        return {}

    @staticmethod
    def _interval_to_mt5tf(interval: str) -> int:
        mapping = {
            "1m": 1, "2m": 2, "3m": 3, "5m": 5, "10m": 10, "15m": 15,
            "20m": 20, "30m": 30, "1h": 60, "2h": 120, "3h": 180, "4h": 240,
            "6h": 360, "8h": 480, "12h": 720, "1d": 1440, "1w": 10080,
            "1mn": 43200,
        }
        return mapping.get(interval, 60)
