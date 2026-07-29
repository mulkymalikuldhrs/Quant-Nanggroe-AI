from __future__ import annotations

import logging
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache, cached
from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)

FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=180&format=json"

_FNG_CACHE = TTLCache(default_ttl=300)


class SentimentScorer(BaseScorer):
    weight: float = 0.10

    def __init__(self, use_api: bool = True):
        self._use_api = use_api

    @cached(_FNG_CACHE, key_prefix="fng", ttl=300)
    def _fetch_fear_greed(self) -> Optional[int]:
        if not self._use_api:
            return None
        try:
            import json
            import urllib.request

            with urllib.request.urlopen(FEAR_GREED_URL, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if "data" in data and len(data["data"]) > 0:
                    return int(data["data"][0].get("value", 50))
        except Exception as exc:
            logger.debug("Fear & Greed fetch failed: %s", exc)
        return None

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        fng_value: Optional[int] = ctx.get("fear_greed_index")
        if fng_value is None:
            fng_value = self._fetch_fear_greed()

        if fng_value is None:
            return ScorerResult(score=0.0, confidence=0.0, metadata={"source": "unavailable"})

        normalized = (fng_value - 50.0) / 50.0
        score = _clamp(normalized * -100, -100.0, 100.0)
        confidence = min(abs(normalized), 1.0)

        return ScorerResult(
            score=score,
            confidence=confidence,
            metadata={"fear_greed_value": fng_value, "source": "alternative.me"},
        )
