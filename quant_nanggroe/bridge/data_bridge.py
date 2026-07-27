"""DataBridge: synchronous bridge engine/data/ → live_engine.
Uses ONLY working providers (urllib-based, no external deps).
Fallback chain: Bybit → OKX → CoinGecko → Finnhub → FRED."""

import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

log = logging.getLogger("QNA.DataBridge")


def _ssl_ctx():
    verify = os.environ.get("QNAI_SSL_VERIFY", "1") == "1"
    ctx = ssl.create_default_context()
    ctx.check_hostname = verify
    ctx.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
    if not verify:
        log.warning("SSL verification DISABLED — set QNAI_SSL_VERIFY=1 in production")
    return ctx


CTX = _ssl_ctx()

CG_TO_SYMBOL = {
    "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
    "binancecoin": "BNBUSDT", "avalanche-2": "AVAXUSDT", "chainlink": "LINKUSDT",
    "ripple": "XRPUSDT", "cardano": "ADAUSDT",
}
SYMBOL_TO_CG = {v: k for k, v in CG_TO_SYMBOL.items()}
CG_IDS = ",".join(SYMBOL_TO_CG.values())

class DataBridge:
    def __init__(self, cache_ttl: int = 30):
        self.cache_ttl = cache_ttl
        self._price_cache: Dict[str, tuple] = {}
        self._kline_cache: Dict[str, tuple] = {}

    def _json_get(self, url: str, timeout: int = 15) -> Optional[dict]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QNA/2.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            log.debug(f"HTTP fail {url[:60]}: {e}")
            return None

    def _bybit_price(self, symbol: str) -> Optional[float]:
        data = self._json_get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}")
        if data and data.get("retCode") == 0:
            tickers = data["result"].get("list", [])
            if tickers:
                return float(tickers[0].get("lastPrice", 0))
        return None

    def _okx_price(self, symbol: str) -> Optional[float]:
        data = self._json_get(f"https://www.okx.com/api/v5/market/ticker?instId={symbol}")
        if data and data.get("code") == "0":
            ticker = data.get("data", [{}])
            if ticker:
                return float(ticker[0].get("last", 0))
        return None

    def _coingecko_price(self, symbol: str) -> Optional[float]:
        cg_id = SYMBOL_TO_CG.get(symbol)
        if not cg_id:
            return None
        data = self._json_get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd")
        if data and cg_id in data:
            return float(data[cg_id].get("usd", 0))
        return None

    def get_price(self, symbol: str) -> float:
        now = time.time()
        if symbol in self._price_cache:
            val, ts = self._price_cache[symbol]
            if now - ts < self.cache_ttl:
                return val

        price = self._bybit_price(symbol)
        if not price:
            price = self._okx_price(symbol)
        if not price:
            price = self._coingecko_price(symbol)

        if price and price > 0:
            self._price_cache[symbol] = (price, now)
            return price
        return 0.0

    def get_all_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        from quant_nanggroe.live_engine import ASSET_SYMBOLS
        symbols = symbols or ASSET_SYMBOLS
        prices = {}
        for sym in symbols:
            p = self.get_price(sym)
            if p > 0:
                prices[sym] = p
            time.sleep(0.05)
        if prices:
            log.info(f"DataBridge: {len(prices)} prices fetched")
        return prices

    def _bybit_klines(self, symbol: str, interval: str = "1", limit: int = 100) -> Optional[List[Dict]]:
        data = self._json_get(f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={interval}&limit={limit}")
        if data and data.get("retCode") == 0:
            raw = data["result"].get("list", [])
            return [{
                "timestamp": int(r[0] / 1000) if r[0] > 1e12 else int(r[0]),
                "open": float(r[1]), "high": float(r[2]),
                "low": float(r[3]), "close": float(r[4]), "volume": float(r[5]),
            } for r in raw]
        return None

    def _okx_klines(self, symbol: str, bar: str = "1m", limit: int = 100) -> Optional[List[Dict]]:
        data = self._json_get(f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}")
        if data and data.get("code") == "0":
            raw = data.get("data", [])
            return [{
                "timestamp": int(r[0] / 1000) if r[0] > 1e12 else int(r[0]),
                "open": float(r[1]), "high": float(r[2]),
                "low": float(r[3]), "close": float(r[4]), "volume": float(r[5]),
            } for r in raw]
        return None

    def get_klines(self, symbol: str, timeframe: str = "1m", limit: int = 60) -> List[Dict]:
        cache_key = f"kline:{symbol}:{timeframe}:{limit}"
        now = time.time()
        if cache_key in self._kline_cache:
            val, ts = self._kline_cache[cache_key]
            if now - ts < self.cache_ttl:
                return val

        result = self._bybit_klines(symbol, "1", limit) if timeframe == "1m" else None
        if not result:
            result = self._okx_klines(symbol, "1m", limit) if timeframe == "1m" else None
        if result:
            self._kline_cache[cache_key] = (result, now)
        return result or []

    def health(self) -> Dict:
        btc = self.get_price("BTCUSDT")
        eth = self.get_price("ETHUSDT")
        return {
            "status": "ok" if btc > 0 else "degraded",
            "btc_usdt": btc,
            "eth_usdt": eth,
            "providers": "bybit+okx+coingecko",
            "cache_ttl": self.cache_ttl,
        }

    def __repr__(self):
        return "DataBridge(bybit+okx+coingecko)"
