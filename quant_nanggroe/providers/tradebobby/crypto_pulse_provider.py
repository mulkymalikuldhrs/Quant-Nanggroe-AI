"""Crypto Pulse Provider — Fear & Greed, dominance, funding rates.

Ported from TradeBobbyTerminal/dashboard/crypto-pulse.js.
No API key needed. 300s TTL cache. Graceful fallback — never crashes.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=300)

ALTERNATIVE_FNG = "https://api.alternative.me/fng/?limit=8"
COINGECKO_GLOBAL = "https://api.coingecko.com/api/v3/global"
BINANCE_FAPI = "https://fapi.binance.com"

WANTED_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT", "SUIUSDT", "TONUSDT",
]


def _safe_fetch(url: str, timeout: int = 10) -> Optional[Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Fetch failed %s: %s", url, exc)
        return None


class CryptoPulseProvider:
    def __init__(self) -> None:
        self._cache = _CACHE

    def get_fear_greed(self) -> Optional[dict[str, Any]]:
        cache_key = "fear_greed"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        j = _safe_fetch(ALTERNATIVE_FNG)
        if not j or not isinstance(j.get("data"), list):
            return None

        items = []
        for d in j["data"]:
            items.append({
                "value": int(d.get("value", 0)),
                "classification": d.get("value_classification", ""),
                "timestamp": int(d.get("timestamp", 0)) * 1000,
            })

        if not items:
            return None

        cur = items[0]
        prev = items[1] if len(items) > 1 else None
        week = items[6] if len(items) > 6 else None

        result = {
            "current": cur["value"],
            "classification": cur["classification"],
            "change_1d": (cur["value"] - prev["value"]) if prev else 0,
            "change_7d": (cur["value"] - week["value"]) if week else 0,
            "history": items,
        }
        self._cache.set(cache_key, result)
        return result

    def get_dominance(self) -> Optional[dict[str, Any]]:
        cache_key = "dominance"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        j = _safe_fetch(COINGECKO_GLOBAL)
        if not j or not isinstance(j.get("data"), dict):
            return None

        data = j["data"]
        mcap_pct = data.get("market_cap_percentage") or {}
        result = {
            "btc_dominance": round(float(mcap_pct.get("btc", 0)), 2),
            "eth_dominance": round(float(mcap_pct.get("eth", 0)), 2),
            "total_mcap_usd": data.get("total_market_cap", {}).get("usd", 0),
            "total_volume_usd": data.get("total_volume", {}).get("usd", 0),
            "mcap_change_24h": round(float(data.get("market_cap_change_percentage_24h_usd", 0)), 2),
            "active_cryptos": data.get("active_cryptocurrencies", 0),
        }
        self._cache.set(cache_key, result)
        return result

    def get_funding_rates(self) -> Optional[dict[str, Any]]:
        cache_key = "funding_rates"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        j = _safe_fetch(f"{BINANCE_FAPI}/fapi/v1/premiumIndex")
        if not isinstance(j, list):
            return None

        tracked: dict[str, dict[str, Any]] = {}
        for t in j:
            sym = t.get("symbol", "")
            if sym not in WANTED_PAIRS:
                continue
            fr = float(t.get("lastFundingRate", 0))
            tracked[sym] = {
                "symbol": sym,
                "mark": float(t.get("markPrice", 0)),
                "index": float(t.get("indexPrice", 0)),
                "funding": fr,
                "funding_pct": round(fr * 100, 4),
                "next_funding": t.get("nextFundingTime", 0),
            }

        all_usdt = [
            {
                "symbol": t.get("symbol", ""),
                "funding": float(t.get("lastFundingRate", 0)),
                "funding_pct": round(float(t.get("lastFundingRate", 0)) * 100, 4),
            }
            for t in j
            if isinstance(t.get("symbol"), str) and t["symbol"].endswith("USDT")
        ]

        all_sorted_pos = sorted(all_usdt, key=lambda x: x["funding"], reverse=True)
        all_sorted_neg = sorted(all_usdt, key=lambda x: x["funding"])

        result = {
            "tracked": tracked,
            "top_long": all_sorted_pos[:6],
            "top_short": all_sorted_neg[:6],
        }
        self._cache.set(cache_key, result)
        return result

    def get_crypto_pulse(self) -> dict[str, Any]:
        fg = self.get_fear_greed()
        dom = self.get_dominance()
        fund = self.get_funding_rates()

        regime = "NEUTRAL"
        signal = ""
        if fg:
            cur = fg.get("current", 50)
            if cur <= 20:
                regime = "EXTREME-FEAR"
                signal = "Contrarian LONG zone (historical bottom)"
            elif cur <= 35:
                regime = "FEAR"
                signal = "Accumulation zone"
            elif cur <= 50:
                regime = "NEUTRAL"
                signal = "No edge"
            elif cur <= 65:
                regime = "GREED"
                signal = "Reduce risk"
            elif cur <= 80:
                regime = "GREED-HIGH"
                signal = "Take profit"
            else:
                regime = "EXTREME-GREED"
                signal = "Contrarian SHORT zone (historical top)"

        funding_signal = ""
        if fund:
            btc_fr = fund.get("tracked", {}).get("BTCUSDT", {}).get("funding_pct")
            if btc_fr is not None:
                if btc_fr > 0.05:
                    funding_signal = "BTC longs paying — bullish positioning crowded (squeeze SHORT risk)"
                elif btc_fr < -0.02:
                    funding_signal = "BTC shorts paying — bearish positioning crowded (squeeze LONG risk)"
                else:
                    funding_signal = "BTC funding balanced"

        import datetime
        return {
            "fear_greed": fg,
            "dominance": dom,
            "funding": fund,
            "regime": regime,
            "signal": signal,
            "funding_signal": funding_signal,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
