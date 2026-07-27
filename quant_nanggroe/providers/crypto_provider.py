"""
Multi-Exchange Crypto Data Provider (no ccxt)
===============================================
Direct REST API calls to Bybit, OKX, Kraken, CoinGecko.
No external dependencies beyond urllib + json (stdlib).
"""

import logging
import os
import time
from typing import Dict, List, Optional

log = logging.getLogger("QNA.CryptoProvider")


_CTX = None


def _get_ctx():
    global _CTX
    if _CTX is None:
        import ssl
        verify = os.environ.get("QNAI_SSL_VERIFY", "1") == "1"
        _CTX = ssl.create_default_context()
        _CTX.check_hostname = verify
        _CTX.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
        if not verify:
            log.warning("SSL verification DISABLED — set QNAI_SSL_VERIFY=1 in production")
    return _CTX


def _json_get(url: str, timeout: int = 15, verify: bool = False) -> Optional[dict]:
    # Use the unified proxy helper for network requests. This respects the
    # PROXY_SOCKS5 environment variable if set, otherwise falls back to a
    # direct request. SSL verification is disabled globally (handled inside
    # the helper) to work around mismatched certificates.
    from .proxy import get_json
    return get_json(url, timeout=timeout)


def _parse_klines(raw: list) -> List[Dict]:
    return [{
        "timestamp": int(float(r[0]) / 1000) if float(r[0]) > 1e12 else int(float(r[0])),
        "open": float(r[1]), "high": float(r[2]),
        "low": float(r[3]), "close": float(r[4]),
        "volume": float(r[5]),
    } for r in raw]


class CryptoProvider:
    def __init__(self):
        pass

    def _bybit_klines(self, symbol: str, interval: str = "1",
                      limit: int = 100) -> Optional[List[Dict]]:
        url = (f"https://api.bybit.com/v5/market/kline"
               f"?category=spot&symbol={symbol}&interval={interval}&limit={limit}")
        data = _json_get(url)
        if data and data.get("retCode") == 0:
            return _parse_klines(data["result"].get("list", []))
        return None

    def _okx_klines(self, symbol: str, bar: str = "1m",
                    limit: int = 100) -> Optional[List[Dict]]:
        url = (f"https://www.okx.com/api/v5/market/candles"
               f"?instId={symbol}&bar={bar}&limit={limit}")
        data = _json_get(url)
        if data and data.get("code") == "0":
            return _parse_klines(data.get("data", []))
        return None

    def _bybit_ticker(self, symbol: str) -> Optional[float]:
        url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
        data = _json_get(url)
        if data and data.get("retCode") == 0:
            tickers = data["result"].get("list", [])
            if tickers:
                return float(tickers[0].get("lastPrice", 0))
        return None

    def _okx_ticker(self, symbol: str) -> Optional[float]:
        url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}"
        data = _json_get(url)
        if data and data.get("code") == "0":
            ticker = data.get("data", [{}])
            if ticker:
                return float(ticker[0].get("last", 0))
        return None

    def _bybit_funding(self, symbol: str) -> Optional[float]:
        """Fetch funding rate for USDT perpetuals."""
        url = (f"https://api.bybit.com/v5/market/tickers"
               f"?category=linear&symbol={symbol}")
        data = _json_get(url)
        if data and data.get("retCode") == 0:
            tickers = data["result"].get("list", [])
            if tickers:
                fr = tickers[0].get("fundingRate")
                return float(fr) if fr else None
        return None

    def _cg_klines(self, coin_id: str, days: int = 1) -> Optional[List[Dict]]:
        url = (f"https://api.coingecko.com/api/v3/coins/{coin_id}"
               f"/market_chart?vs_currency=usd&days={days}")
        data = _json_get(url)
        if data and "prices" in data:
            prices = data["prices"]
            return [{
                "timestamp": int(p[0] / 1000),
                "open": p[1], "high": p[1],
                "low": p[1], "close": p[1], "volume": 0,
            } for p in prices]
        return None

    def get_klines(self, symbol: str, timeframe: str = "1m",
                   limit: int = 100) -> List[Dict]:
        """Try Bybit first, fall back to OKX, then CoinGecko."""
        if timeframe == "1m":
            result = self._bybit_klines(symbol, "1", limit)
            if result:
                return result
            result = self._okx_klines(symbol, "1m", limit)
            if result:
                return result

            cg_id = {
                "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum",
                "SOLUSDT": "solana", "BNBUSDT": "binancecoin",
                "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink",
                "XRPUSDT": "ripple", "ADAUSDT": "cardano",
            }.get(symbol)
            if cg_id:
                result = self._cg_klines(cg_id, 1)
                if result:
                    step = max(1, len(result) // limit)
                    return result[::step]
        return []

    def get_ticker(self, symbol: str) -> Optional[float]:
        price = self._bybit_ticker(symbol)
        if price:
            return price
        return self._okx_ticker(symbol)

    def get_all_prices(self, symbols: List[str]) -> Dict[str, float]:
        prices = {}
        for sym in symbols:
            price = self.get_ticker(sym)
            if price:
                prices[sym] = price
            time.sleep(0.1)
        return prices

    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Perpetual funding rate for symbol (e.g. BTCUSDT)."""
        return self._bybit_funding(symbol)

    def __repr__(self):
        return "CryptoProvider(bybit+okx+coingecko)"
