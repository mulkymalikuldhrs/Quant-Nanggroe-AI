from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache
from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"

logger = logging.getLogger(__name__)

_NEWS_CACHE = TTLCache(default_ttl=300)


class NewsScorer(BaseScorer):
    weight: float = 0.02

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._cache = _NEWS_CACHE

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        symbol = ctx.get("symbol", "")
        api_key = self._api_key or ctx.get("alpha_vantage_key") or "demo"
        if api_key == "demo":
            return ScorerResult(score=0.0, confidence=0.0, metadata={"reason": "no_api_key"})

        items = self._fetch_news_sentiment(symbol, api_key)
        if not items:
            return ScorerResult(score=0.0, confidence=0.0, metadata={"reason": "no_news_data"})

        sentiment_scores = []
        for item in items:
            score_val = float(item.get("overall_sentiment_score", 0))
            sentiment_scores.append(score_val)

        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        score = _clamp(avg_sentiment * 100, -100.0, 100.0)
        confidence = min(len(sentiment_scores) / 20.0, 1.0) * min(abs(avg_sentiment) * 2, 1.0)

        return ScorerResult(
            score=score,
            confidence=confidence,
            metadata={
                "symbol": symbol,
                "article_count": len(items),
                "avg_sentiment": round(avg_sentiment, 4),
                "source": "alpha_vantage_news_sentiment",
            },
        )

    def _fetch_news_sentiment(self, symbol: str, api_key: str) -> list[dict[str, Any]]:
        cache_key = f"news:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            tickers = symbol.upper().replace("USD", "/USD")
            params = (
                f"function=NEWS_SENTIMENT"
                f"&tickers={tickers}"
                f"&apikey={api_key}"
                f"&limit=50"
                f"&sort=RELEVANCE"
            )
            url = f"{ALPHA_VANTAGE_BASE}?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if "feed" not in data:
                return []

            items = []
            for item in data["feed"]:
                if not isinstance(item, dict):
                    continue
                items.append(item)

            self._cache.set(cache_key, items, ttl=300)
            return items

        except Exception as exc:
            logger.debug("News sentiment fetch failed for %s: %s", symbol, exc)
            return []
