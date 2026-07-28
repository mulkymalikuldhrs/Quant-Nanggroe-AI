"""Crypto provider stub — delegates to data/providers/crypto_provider."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CryptoProvider:
    def __init__(self):
        self._inner: Any = None

    def _lazy_init(self):
        if self._inner is not None:
            return
        try:
            from quant_nanggroe.data.providers.crypto_provider import CryptoProvider as _NewCP
            self._inner = _NewCP()
        except Exception as exc:
            logger.debug("CryptoProvider lazy init failed: %s", exc)
            self._inner = None

    def get_klines(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> List[Dict]:
        self._lazy_init()
        if self._inner is None:
            return []
        try:
            df = self._inner.fetch_ohlcv_sync(symbol, timeframe=timeframe, limit=limit)
            if df is None or df.empty:
                return []
            records = df.to_dict("records")
            for r in records:
                if "timestamp" in r and hasattr(r["timestamp"], "timestamp"):
                    r["timestamp"] = int(r["timestamp"].timestamp())
            return records
        except Exception as exc:
            logger.debug("get_klines failed: %s", exc)
            return []

    def get_all_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        self._lazy_init()
        if self._inner is None:
            return {}
        try:
            import ccxt
            exchange = ccxt.bybit()
            tickers = exchange.fetch_tickers()
            result = {}
            for s in (symbols or ["BTC/USDT", "ETH/USDT", "SOL/USDT"]):
                norm = s.replace("USDT", "/USDT")
                if norm in tickers:
                    result[s] = tickers[norm]["last"]
                elif s in tickers:
                    result[s] = tickers[s]["last"]
            return result
        except Exception as exc:
            logger.debug("get_all_prices failed: %s", exc)
            return {}

    def __repr__(self) -> str:
        return "CryptoProvider(delegated)"
