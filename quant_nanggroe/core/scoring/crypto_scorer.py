from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache
from quant_nanggroe.core.config.pair_config import SYMBOL_TO_ASSET_CLASS, AssetClass
from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

BINANCE_FAPI = "https://fapi.binance.com"

SYMBOL_TO_BINANCE: dict[str, str] = {
    "BTCUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT",
    "SOLUSD": "SOLUSDT",
}

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=300)


class CryptoScorer(BaseScorer):
    weight: float = 0.08

    def __init__(self) -> None:
        self._cache = _CACHE

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        symbol: str = ctx.get("symbol", "")
        asset_class = SYMBOL_TO_ASSET_CLASS.get(symbol.upper())

        if asset_class != AssetClass.CRYPTO:
            return ScorerResult(
                score=0.0,
                confidence=0.0,
                metadata={"symbol": symbol, "reason": "not_crypto"},
            )

        binance_symbol = SYMBOL_TO_BINANCE.get(symbol.upper(), symbol.upper().replace("USD", "USDT"))

        funding = self._get_funding_rate(binance_symbol)
        oi = self._get_open_interest(binance_symbol)
        price_change_pct = ctx.get("price_change_pct", 0.0)

        metadata: dict[str, Any] = {
            "symbol": symbol,
            "binance_symbol": binance_symbol,
        }

        if funding is None and oi is None:
            return ScorerResult(score=0.0, confidence=0.0, metadata={**metadata, "reason": "no_data"})

        score = 0.0
        confidence = 0.0
        signals = 0

        if funding is not None:
            fr = funding.get("lastFundingRate", 0)
            fr_pct = float(fr) * 100
            metadata["funding_rate_pct"] = round(fr_pct, 6)

            if fr_pct < -0.01:
                score += 40.0
                confidence += 0.4
                signals += 1
            elif fr_pct > 0.01:
                score -= 40.0
                confidence += 0.4
                signals += 1
            else:
                score += 0.0
                confidence += 0.1
                signals += 1

        if oi is not None:
            oi_value = float(oi.get("openInterest", 0))
            metadata["open_interest"] = oi_value

            if abs(price_change_pct) > 0.1 and oi_value > 0:
                if price_change_pct > 0:
                    score += 30.0
                    confidence += 0.3
                else:
                    score -= 30.0
                    confidence += 0.3
                signals += 1

        if signals > 0:
            confidence = _clamp(confidence / signals, 0.0, 1.0)
        else:
            confidence = 0.0

        final_score = _clamp(score, -100.0, 100.0)
        return ScorerResult(score=final_score, confidence=confidence, metadata=metadata)

    def _get_funding_rate(self, symbol: str) -> Optional[dict[str, Any]]:
        cache_key = f"funding:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            url = f"{BINANCE_FAPI}/fapi/v1/premiumIndex?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                self._cache.set(cache_key, data, ttl=300)
                return data
        except Exception as exc:
            logger.debug("Funding rate fetch failed for %s: %s", symbol, exc)
            return None

    def _get_open_interest(self, symbol: str) -> Optional[dict[str, Any]]:
        cache_key = f"oi:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            url = f"{BINANCE_FAPI}/fapi/v1/openInterest?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                self._cache.set(cache_key, data, ttl=300)
                return data
        except Exception as exc:
            logger.debug("Open Interest fetch failed for %s: %s", symbol, exc)
            return None
