"""
Finnhub Data Provider
=====================
Real-time US stock data, news, sentiment, SEC filings.
Free tier: 60 calls/min, real-time WebSocket (limited symbols).

API key from credentials.md (if set) or environment variable.
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger("QNA.Finnhub")


class FinnhubProvider:
    FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")

    def __init__(self, api_key: str = None):
        self.api_key = api_key or self.FINNHUB_KEY
        self.base = "https://finnhub.io/api/v1"
        self.last_call = 0
        self.min_interval = 1.0

    def _rate_limit(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

    def _get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        import urllib.request, urllib.parse
        self._rate_limit()
        params = params or {}
        params["token"] = self.api_key
        url = f"{self.base}/{endpoint}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QNA/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            log.debug(f"Finnhub {endpoint}: {e}")
            return None

    def quote(self, symbol: str) -> Optional[Dict]:
        return self._get("quote", {"symbol": symbol})

    def company_news(self, symbol: str, from_date: str, to_date: str) -> Optional[List]:
        data = self._get("company-news", {"symbol": symbol, "from": from_date, "to": to_date})
        return data if isinstance(data, list) else None

    def market_news(self, category: str = "general") -> Optional[List]:
        data = self._get("news", {"category": category})
        return data if isinstance(data, list) else None

    def sec_filings(self, symbol: str, limit: int = 10) -> Optional[List]:
        data = self._get("stock/filings", {"symbol": symbol, "limit": limit, "from": "2024-01-01"})
        if isinstance(data, dict):
            return data.get("data")
        return data if isinstance(data, list) else None

    def get_stock_candles(self, symbol: str, resolution: str = "D",
                          count: int = 100) -> Optional[List[Dict]]:
        now = int(time.time())
        data = self._get("stock/candles", {
            "symbol": symbol, "resolution": resolution,
            "from": str(now - count * 86400), "to": str(now),
        })
        if not data or data.get("s") != "ok":
            return None
        candles = []
        for i in range(len(data.get("t", []))):
            candles.append({
                "timestamp": data["t"][i],
                "open": data["o"][i], "high": data["h"][i],
                "low": data["l"][i], "close": data["c"][i],
                "volume": data["v"][i],
            })
        return candles

    def is_available(self) -> bool:
        return bool(self.api_key)

    def __repr__(self):
        return f"FinnhubProvider(key_set={bool(self.api_key)})"
