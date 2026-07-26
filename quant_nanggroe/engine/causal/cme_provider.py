"""
CME Price Provider — Futures & Spot Price Data with Returns Cache
==================================================================
Provides live and cached price data for CME futures symbols and their
spot/retail equivalents. Supports DCC-GARCH returns cache by computing
log returns from price history.

Yahoo Finance compatibility fix: Futures symbols (GC1!, ES1!) are
converted to Yahoo format (GC=F, ES=F) automatically via _yahoo_symbol().
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CME_FUTURES_MAP = {
    "GC1!": "XAUUSD",     "SI1!": "XAGUSD",
    "ES1!": "US500",      "NQ1!": "NAS100",
    "YM1!": "US30",       "6E1!": "EURUSD",
    "6B1!": "GBPUSD",     "6J1!": "USDJPY",
    "6A1!": "AUDUSD",     "6C1!": "USDCAD",
    "6S1!": "USDCHF",     "ZB1!": "US30Y",
    "ZN1!": "US10Y",      "CL1!": "USOIL",
    "NG1!": "NATGAS",     "BTC1!": "BTCUSD",
    "ETH1!": "ETHUSD",
}
SPOT_TO_FUTURES = {v: k for k, v in CME_FUTURES_MAP.items()}

# Yahoo Finance symbol mapping for CME futures
YAHOO_FUTURES_MAP = {
    "GC1!": "GC=F",       "SI1!": "SI=F",
    "ES1!": "ES=F",       "NQ1!": "NQ=F",
    "YM1!": "YM=F",       "6E1!": "6E=F",
    "6B1!": "6B=F",       "6J1!": "6J=F",
    "6A1!": "6A=F",       "6C1!": "6C=F",
    "6S1!": "6S=F",       "ZB1!": "ZB=F",
    "ZN1!": "ZN=F",       "CL1!": "CL=F",
    "NG1!": "NG=F",       "BTC1!": "BTC=F",
    "ETH1!": "ETH=F",
}


class CMEPriceProvider:
    """
    Price data provider for CME futures and spot equivalents.

    Features:
        - Symbol resolution (futures <-> spot)
        - Yahoo Finance compatible formatting
        - Price fetching via EnginePriceProvider (spot) + yfinance (futures)
        - Returns computation (log returns)
        - Caching with TTL
    """

    DEFAULT_WATCHLIST = [
        "GC1!", "SI1!", "ES1!", "NQ1!", "YM1!",
        "6E1!", "6B1!", "6J1!", "CL1!", "ZB1!", "BTC1!",
    ]

    MAX_RETURNS_ROWS = 500

    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self._price_cache: Dict[str, Tuple[float, float]] = {}
        self._klines_cache: Dict[str, Tuple[float, List[Dict]]] = {}
        self._returns_cache: Dict[str, pd.DataFrame] = {}
        self._last_update: Optional[datetime] = None
        self._engine_provider: Any = None
        self._lazy_providers()

    def _lazy_providers(self):
        if self._engine_provider is not None:
            return
        try:
            from quant_nanggroe.engine_bridge import EnginePriceProvider
            self._engine_provider = EnginePriceProvider(cache_ttl=self.cache_ttl)
        except Exception as e:
            logger.debug("CME: EnginePriceProvider unavailable: %s", e)

    # ── Symbol resolution ──────────────────────────────────────────

    @staticmethod
    def futures_to_spot(futures_symbol: str) -> Optional[str]:
        return CME_FUTURES_MAP.get(futures_symbol.upper())

    @staticmethod
    def spot_to_futures(spot_symbol: str) -> Optional[str]:
        return SPOT_TO_FUTURES.get(spot_symbol.upper())

    @staticmethod
    def to_yahoo(symbol: str) -> str:
        """Convert CME futures symbol to Yahoo Finance format."""
        upper = symbol.upper()
        if upper in YAHOO_FUTURES_MAP:
            return YAHOO_FUTURES_MAP[upper]
        # Spot forex for Yahoo
        spot = CME_FUTURES_MAP.get(upper)
        if spot:
            return f"{spot}=X"
        return f"{upper}=X" if len(upper) <= 7 else upper

    @staticmethod
    def resolve(symbol: str) -> str:
        upper = symbol.upper()
        if upper in CME_FUTURES_MAP:
            return upper
        if upper in SPOT_TO_FUTURES:
            return SPOT_TO_FUTURES[upper]
        return upper

    # ── Price fetching ─────────────────────────────────────────────

    def get_price(self, symbol: str) -> Optional[float]:
        sym = self.resolve(symbol)
        cached = self._price_cache.get(sym)
        if cached and (time.time() - cached[0]) < self.cache_ttl:
            return cached[1]

        price = self._fetch_price(sym)
        if price is not None and price > 0:
            self._price_cache[sym] = (time.time(), price)
            return price
        return None

    def _fetch_price(self, symbol: str) -> Optional[float]:
        # Backend 1: EnginePriceProvider (prefers spot symbols)
        if self._engine_provider is not None:
            try:
                spot = self.futures_to_spot(symbol) or symbol
                price = self._engine_provider.get_price(spot)
                if price is not None and price > 0:
                    return float(price)
            except Exception:
                pass

        # Backend 2: yfinance (uses Yahoo-compatible symbol)
        try:
            import yfinance as yf
            yahoo_sym = self.to_yahoo(symbol)
            ticker = yf.Ticker(yahoo_sym)
            data = ticker.history(period="2d", interval="1m")
            if data is not None and not data.empty:
                return float(data["Close"].iloc[-1])
        except Exception:
            pass

        return None

    def get_klines(
        self, symbol: str, interval: str = "1h", limit: int = 100
    ) -> List[Dict]:
        sym = self.resolve(symbol)
        cache_key = f"{sym}:{interval}:{limit}"
        cached = self._klines_cache.get(cache_key)
        if cached and (time.time() - cached[0]) < self.cache_ttl:
            return cached[1]

        candles = self._fetch_klines(sym, interval, limit)
        if candles:
            self._klines_cache[cache_key] = (time.time(), candles)
        return candles

    def _fetch_klines(self, symbol: str, interval: str, limit: int) -> List[Dict]:
        # Backend 1: EnginePriceProvider (spot)
        if self._engine_provider is not None:
            try:
                spot = self.futures_to_spot(symbol) or symbol
                candles = self._engine_provider.get_klines(spot, interval=interval, limit=limit)
                if candles:
                    return candles
            except Exception:
                pass

        # Backend 2: yfinance with proper symbol format
        try:
            import yfinance as yf
            tf_map = {"1m": "1m", "5m": "5m", "15m": "15m",
                      "30m": "30m", "1h": "1h", "4h": "1h", "1d": "1d"}
            period_map = {"1m": "7d", "5m": "1mo", "15m": "1mo",
                          "30m": "1mo", "1h": "1mo", "4h": "6mo", "1d": "1y"}
            yahoo_sym = self.to_yahoo(symbol)
            ticker = yf.Ticker(yahoo_sym)
            data = ticker.history(period=period_map.get(interval, "1mo"),
                                   interval=tf_map.get(interval, "1h"))
            if data is not None and not data.empty:
                candles = []
                for idx, row in data.iterrows():
                    candles.append({
                        "timestamp": int(idx.timestamp()),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row["Volume"]),
                    })
                return candles[-limit:]
        except Exception:
            pass
        return []

    # ── Returns computation ─────────────────────────────────────────

    def get_returns(
        self,
        symbols: Optional[List[str]] = None,
        interval: str = "1h",
        lookback: int = 100,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        syms = symbols or list(self.DEFAULT_WATCHLIST)
        cache_key = f"returns:{','.join(sorted(syms))}:{interval}:{lookback}"

        if not force_refresh and cache_key in self._returns_cache:
            return self._returns_cache[cache_key]

        close_data: Dict[str, List[float]] = {}
        for sym in syms:
            candles = self.get_klines(sym, interval=interval, limit=lookback + 1)
            if candles and len(candles) >= 30:
                close_data[sym] = [c["close"] for c in candles]

        if len(close_data) < 2:
            return pd.DataFrame()

        min_len = min(len(v) for v in close_data.values())
        aligned = {sym: prices[-min_len:] for sym, prices in close_data.items()}
        df = pd.DataFrame(aligned)
        log_returns = np.log(df / df.shift(1)).dropna()

        if len(log_returns) < 10:
            return pd.DataFrame()

        self._returns_cache[cache_key] = log_returns
        self._last_update = datetime.now()
        return log_returns

    # ── Status ─────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "provider": "CMEPriceProvider",
            "cached_prices": len(self._price_cache),
            "cached_returns": len(self._returns_cache),
            "watchlist_size": len(self.DEFAULT_WATCHLIST),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "engine_provider_available": self._engine_provider is not None,
        }

    def get_all_prices(self) -> Dict[str, float]:
        prices: Dict[str, float] = {}
        for sym in self.DEFAULT_WATCHLIST:
            price = self.get_price(sym)
            if price is not None:
                prices[sym] = price
        return prices

    def clear_cache(self):
        self._price_cache.clear()
        self._klines_cache.clear()
        self._returns_cache.clear()


__all__ = ["CMEPriceProvider", "CME_FUTURES_MAP", "SPOT_TO_FUTURES", "YAHOO_FUTURES_MAP"]
