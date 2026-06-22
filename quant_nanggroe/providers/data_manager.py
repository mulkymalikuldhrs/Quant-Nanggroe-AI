"""
Unified Data Manager
=====================
Combines all data providers into a single interface.
Auto-fallback: if one provider fails, tries the next.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

log = logging.getLogger("QNA.DataManager")

from .crypto_provider import CryptoProvider
from .finnhub_provider import FinnhubProvider
from .macro_provider import MacroProvider


class DataManager:
    def __init__(self, cg_api_key: str = ""):
        self.crypto = CryptoProvider()
        self.finnhub = FinnhubProvider()
        self.macro = MacroProvider()
        self._cg_api_key = cg_api_key

        self._coingecko_session = None
        self._polygon_session = None
        self._all_prices_cache = {}
        self._cache_time = 0
        self._cache_ttl = 30  # 30s price cache to avoid rate limits

    def _init_coingecko(self):
        if self._coingecko_session is not None:
            return
        import ssl
        import urllib.request
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self._coingecko_session = urllib.request.build_opener()
        headers = [
            ("User-Agent", "QNA/1.0"),
            ("Accept", "application/json"),
        ]
        if self._cg_api_key:
            headers.append(("x-cg-demo-api-key", self._cg_api_key))
        self._coingecko_session.addheaders = headers

    def _init_polygon(self):
        if self._polygon_session is not None:
            return
        import urllib.request
        self._polygon_session = urllib.request.build_opener()
        self._polygon_session.addheaders = [
            ("User-Agent", "QNA/1.0"),
            ("Accept", "application/json"),
        ]

    def _polygon_crypto_price(self) -> Dict[str, float]:
        """Fetch crypto prices from Polygon.io (free: 5 calls/min)."""
        api_key = "EDpwwAxMscUJ7_og3OnxZQVrToEWw7MR"
        self._init_polygon()
        result = {}
        from .proxy import get_json
        cg_to_poly = {
            "X:BTCUSD": "BTCUSDT", "X:ETHUSD": "ETHUSDT",
            "X:SOLUSD": "SOLUSDT", "X:BNBUSD": "BNBUSDT",
            "X:AVAXUSD": "AVAXUSDT", "X:LINKUSD": "LINKUSDT",
            "X:XRPUSD": "XRPUSDT", "X:ADAUSD": "ADAUSDT",
        }
        for poly_ticker, sym in cg_to_poly.items():
            url = f"https://api.polygon.io/v2/snapshot/locale/global/markets/crypto/tickers/{poly_ticker}?apiKey={api_key}"
            data = get_json(url)
            if data and data.get("status") == "OK":
                ticker = data.get("ticker", {})
                day = ticker.get("day", {})
                price = day.get("c") or ticker.get("lastTrade", {}).get("p")
                if price:
                    result[sym] = float(price)
        return result

    def _coingecko_get(self, url: str, max_retries: int = 2) -> Optional[Dict]:
        # Unified GET using the proxy helper. This respects rate‑limiting and
        # optionally routes through the configured SOCKS5/HTTP proxy.
        from .proxy import get_json
        self._rate_limit_cg()
        for attempt in range(max_retries):
            data = get_json(url)
            if data is not None:
                return data
            if attempt == max_retries - 1:
                return None
            time.sleep(2)

    _last_cg_call = 0

    def _rate_limit_cg(self):
        now = time.time()
        elapsed = now - self._last_cg_call
        min_gap = 1.2 if self._cg_api_key else 2.5
        if elapsed < min_gap:
            time.sleep(min_gap - elapsed)
        self.__class__._last_cg_call = time.time()

    def get_crypto_prices(self, coin_ids: str) -> Dict[str, float]:
        import ssl, urllib.request
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_ids}&vs_currencies=usd"
        data = self._coingecko_get(url)
        if data:
            result = {}
            mapping = {
                "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
                "binancecoin": "BNBUSDT", "avalanche-2": "AVAXUSDT",
                "chainlink": "LINKUSDT", "cardano": "ADAUSDT", "ripple": "XRPUSDT",
            }
            for cg_id, sym in mapping.items():
                if cg_id in data and "usd" in data[cg_id]:
                    result[sym] = data[cg_id]["usd"]
            return result
        return {}

    def get_klines(self, symbol: str, timeframe: str = "1m",
                   limit: int = 100) -> List[Dict]:
        result = self.crypto.get_klines(symbol, timeframe, limit)
        if result:
            return result

        return result or []

    def get_all_prices(self) -> Dict[str, float]:
        now = time.time()
        if self._all_prices_cache and now - self._cache_time < self._cache_ttl:
            return self._all_prices_cache

        prices = {}
        coin_ids = ("bitcoin,ethereum,solana,binancecoin,avalanche-2,"
                     "chainlink,cardano,ripple")

        try:
            cg_prices = self.get_crypto_prices(coin_ids)
            prices.update(cg_prices)
        except Exception:
            pass

        if len(prices) < 3:
            try:
                bybit_prices = self.crypto.get_all_prices(
                    ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
                     "AVAXUSDT", "LINKUSDT", "XRPUSDT", "ADAUSDT"])
                for sym, p in bybit_prices.items():
                    if sym not in prices or prices.get(sym, 0) == 0:
                        prices[sym] = p
            except Exception:
                pass

        if len(prices) < 3:
            try:
                poly_prices = self._polygon_crypto_price()
                for sym, p in poly_prices.items():
                    if sym not in prices or prices.get(sym, 0) == 0:
                        prices[sym] = p
            except Exception:
                pass

        if prices:
            self._all_prices_cache = prices
            self._cache_time = now

        return prices

    def get_macro_snapshot(self) -> Dict:
        return self.macro.get_macro_snapshot()

    def get_news_sentiment(self, symbol: str = None) -> List[Dict]:
        if self.finnhub.is_available():
            if symbol:
                news = self.finnhub.company_news(symbol, "2026-06-01", "2026-06-21")
            else:
                news = self.finnhub.market_news("general")
            return news or []
        return []

    def stats(self) -> Dict:
        return {
            "crypto_provider": repr(self.crypto),
            "finnhub_available": self.finnhub.is_available(),
            "macro_available": self.macro.is_available(),
        }

    def __repr__(self):
        return f"DataManager(crypto=bybit+okx+coingecko,finnhub={self.finnhub.is_available()},macro={self.macro.is_available()})"
