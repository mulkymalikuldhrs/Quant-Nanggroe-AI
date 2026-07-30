from __future__ import annotations

import logging
import urllib.request
import json
from typing import Any, Optional
from collections import defaultdict

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=120)

WATCHED_SYMBOLS = [
    "XAUUSD", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD",
    "USDJPY", "USDCAD", "AUDUSD", "GBPJPY", "XAGUSD",
    "SOLUSDT", "WTI", "SPX500", "NAS100", "NVDA",
]

BINANCE_WS = "wss://fapi.binance.com"


def _classify_divergence(cvd: float, price_change: float) -> str:
    if price_change > 0 and cvd < 0:
        return "HIDDEN_DISTRIBUTION"
    if price_change < 0 and cvd > 0:
        return "HIDDEN_ACCUMULATION"
    if price_change > 0 and cvd > 0:
        return "CONFIRMED_ACCUMULATION"
    if price_change < 0 and cvd < 0:
        return "CONFIRMED_DISTRIBUTION"
    return "NEUTRAL"


def _fetch_binance_ticker(symbol: str) -> Optional[dict[str, Any]]:
    url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Binance ticker failed %s: %s", symbol, exc)
        return None


class CVDProvider:
    def __init__(self) -> None:
        self._cache = _CACHE

    def get_cvd_snapshot(self) -> dict[str, Any]:
        cache_key = "cvd:snapshot"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        results: list[dict[str, Any]] = []
        for sym in WATCHED_SYMBOLS:
            ticker = _fetch_binance_ticker(sym.replace("USD", "USDT"))
            if ticker is None:
                ticker = _fetch_binance_ticker(sym.replace("BTC", "BTCUSDT").replace("ETH", "ETHUSDT")
                                                if "BTC" in sym or "ETH" in sym else None)
            if ticker is None:
                results.append({
                    "symbol": sym,
                    "price": 0.0,
                    "cvd_delta": 0.0,
                    "classification": "NO_DATA",
                    "divergence": "NO_DATA",
                })
                continue

            price = float(ticker.get("lastPrice", 0))
            volume = float(ticker.get("quoteVolume", 0))
            change_pct = float(ticker.get("priceChangePercent", 0))
            taker_buy_vol = float(ticker.get("takerBuyQuoteAssetVolume", 0))
            taker_sell_vol = volume - taker_buy_vol if volume > taker_buy_vol else 0
            cvd = taker_buy_vol - taker_sell_vol

            total_vol = taker_buy_vol + taker_sell_vol
            if total_vol > 0:
                cvd_ratio = cvd / total_vol
                if cvd_ratio > 0.15:
                    classification = "AGGRESSIVE_BUYING"
                elif cvd_ratio > 0.05:
                    classification = "BUYING"
                elif cvd_ratio < -0.15:
                    classification = "AGGRESSIVE_SELLING"
                elif cvd_ratio < -0.05:
                    classification = "SELLING"
                else:
                    classification = "NEUTRAL"
            else:
                classification = "NO_DATA"

            divergence = _classify_divergence(cvd, change_pct)

            results.append({
                "symbol": sym,
                "price": round(price, 2),
                "cvd_delta": round(cvd, 2),
                "classification": classification,
                "divergence": divergence,
                "volume_24h": round(volume, 2),
                "change_pct": round(change_pct, 2),
            })

        output = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "symbols": results,
        }
        self._cache.set(cache_key, output)
        return output
