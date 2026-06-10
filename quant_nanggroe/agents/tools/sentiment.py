"""
Sentiment Tool — News & Social Sentiment Analysis for Agents
=============================================================
Provides keyword-based sentiment scoring from news headlines,
event classification (MACRO, SCHEDULED, SHOCK, NOISE), and
structured sentiment data with confidence scores.

Designed to work with multiple news API backends (Alpha Vantage,
Polygon, etc.) with graceful fallback when APIs are unavailable.

LangChain @tool functions are also exposed for direct agent consumption.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from quant_nanggroe.config.settings import get_settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# News Event Type
# ══════════════════════════════════════════════════════════════════════

class NewsEventType(str, Enum):
    """Classification of news events by impact type."""
    MACRO = "MACRO"
    SCHEDULED = "SCHEDULED"
    SHOCK = "SHOCK"
    NOISE = "NOISE"


# ══════════════════════════════════════════════════════════════════════
# Keyword-based sentiment lexicon
# ══════════════════════════════════════════════════════════════════════

_BULLISH_KEYWORDS: Dict[str, float] = {
    "surge": 0.8,
    "soar": 0.8,
    "rally": 0.7,
    "breakout": 0.7,
    "bullish": 0.7,
    "upgrade": 0.6,
    "beat expectations": 0.7,
    "exceeds": 0.6,
    "strong demand": 0.6,
    "all-time high": 0.8,
    "record high": 0.8,
    "buy rating": 0.5,
    "outperform": 0.6,
    "growth": 0.5,
    "profit": 0.4,
    "revenue beat": 0.6,
    "positive outlook": 0.6,
    "gaining": 0.5,
    "recovery": 0.5,
    "accumulation": 0.5,
    "support level": 0.3,
    "oversold": 0.4,
    "bounce": 0.4,
    "momentum": 0.4,
    "whale buy": 0.7,
    "institutional buying": 0.6,
}

_BEARISH_KEYWORDS: Dict[str, float] = {
    "crash": -0.9,
    "plunge": -0.8,
    "dump": -0.7,
    "sell-off": -0.7,
    "bearish": -0.7,
    "downgrade": -0.6,
    "miss expectations": -0.6,
    "recession": -0.7,
    "bankruptcy": -0.9,
    "liquidation": -0.7,
    "capitulation": -0.8,
    "death cross": -0.6,
    "resistance": -0.3,
    "overbought": -0.4,
    "decline": -0.5,
    "loss": -0.4,
    "warning": -0.4,
    "risk": -0.3,
    "uncertainty": -0.3,
    "whale sell": -0.7,
    "institutional selling": -0.6,
    "regulation": -0.4,
    "ban": -0.6,
    "hack": -0.8,
    "exploit": -0.7,
    "default": -0.7,
}

# Event classification keywords
_MACRO_KEYWORDS = {
    "fed", "federal reserve", "interest rate", "inflation", "cpi", "gdp",
    "employment", "nonfarm", "fomc", "ecb", "boj", "monetary policy",
    "quantitative easing", "taper", "recession", "stimulus", "treasury",
    "bond yield", "yield curve",
}

_SCHEDULED_KEYWORDS = {
    "earnings", "report", "quarterly", "fda", "approval", "meeting",
    "conference", "summit", "ipo", "listing", "dividend", "split",
    "halving", "unlock", "airdrop", "mainnet launch",
}

_SHOCK_KEYWORDS = {
    "hack", "exploit", "breach", "crash", "black swan", "emergency",
    "ceasefire", "war", "sanctions", "embargo", "default", "ban",
    "flash crash", "circuit breaker", "halt", "suspend",
}


class _NewsClassifier:
    """Classify news items by event type and compute sentiment scores."""

    @staticmethod
    def classify_event(headline: str) -> NewsEventType:
        """
        Classify a news headline into an event type.

        Args:
            headline: News headline text.

        Returns:
            NewsEventType enum value.
        """
        lower = headline.lower()

        shock_matches = sum(1 for kw in _SHOCK_KEYWORDS if kw in lower)
        macro_matches = sum(1 for kw in _MACRO_KEYWORDS if kw in lower)
        scheduled_matches = sum(1 for kw in _SCHEDULED_KEYWORDS if kw in lower)

        # Priority: SHOCK > MACRO > SCHEDULED > NOISE
        if shock_matches >= 1:
            return NewsEventType.SHOCK
        if macro_matches >= 1:
            return NewsEventType.MACRO
        if scheduled_matches >= 1:
            return NewsEventType.SCHEDULED
        return NewsEventType.NOISE

    @staticmethod
    def score_headline(headline: str) -> tuple[float, float]:
        """
        Score a news headline for sentiment and confidence.

        Args:
            headline: News headline text.

        Returns:
            Tuple of (sentiment_score, confidence).
            sentiment_score: -1.0 to +1.0
            confidence: 0.0 to 1.0
        """
        lower = headline.lower()

        bullish_score = 0.0
        bearish_score = 0.0
        match_count = 0

        for keyword, weight in _BULLISH_KEYWORDS.items():
            if keyword in lower:
                bullish_score += weight
                match_count += 1

        for keyword, weight in _BEARISH_KEYWORDS.items():
            if keyword in lower:
                bearish_score += abs(weight)
                match_count += 1

        if match_count == 0:
            return 0.0, 0.1  # Neutral with low confidence

        # Net sentiment score
        net = bullish_score - bearish_score
        # Normalize to [-1, 1]
        max_possible = max(bullish_score + bearish_score, 1.0)
        normalized = max(-1.0, min(1.0, net / max_possible))

        # Confidence based on number and strength of keyword matches
        confidence = min(match_count / 5.0, 1.0) * min(
            (bullish_score + bearish_score) / 3.0, 1.0
        )

        return round(normalized, 4), round(max(confidence, 0.1), 4)


class _SimpleCache:
    """Minimal TTL cache for sentiment results."""

    def __init__(self, ttl: int = 300) -> None:
        self._store: Dict[str, tuple[Any, float]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        val, ts = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return val

    def set(self, key: str, val: Any) -> None:
        self._store[key] = (val, time.monotonic())


class SentimentTool:
    """
    Sentiment analysis tool for agent consumption.

    Aggregates news headlines from multiple sources, classifies events,
    and produces structured sentiment data with confidence scores.

    When no news APIs are configured or available, the tool gracefully
    degrades and returns low-confidence neutral sentiment.

    Usage::

        tool = SentimentTool()
        result = await tool.analyze("AAPL")
        print(result["overall_score"])  # -1.0 to +1.0
        print(result["confidence"])     # 0.0 to 1.0
    """

    def __init__(self, cache_ttl: int = 300) -> None:
        """
        Initialize the SentimentTool.

        Args:
            cache_ttl: Cache TTL in seconds for sentiment results (default 300).
        """
        self._settings = get_settings()
        self._cache = _SimpleCache(ttl=cache_ttl)
        self._classifier = _NewsClassifier()

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze sentiment for a symbol from news and social data.

        Fetches news headlines, classifies events, scores sentiment,
        and returns a comprehensive sentiment analysis dict.

        Args:
            symbol: Ticker symbol to analyze.

        Returns:
            Dict with:
              - 'symbol': The analyzed symbol
              - 'overall_score': Weighted sentiment score (-1.0 to +1.0)
              - 'confidence': Overall confidence (0.0 to 1.0)
              - 'news_items': List of scored news items
              - 'social_sentiment': Social media sentiment summary
              - 'event_breakdown': Count of events by type
              - 'timestamp': Analysis timestamp
        """
        cache_key = f"sentiment:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # Fetch news from available sources
        raw_headlines = await self._fetch_news(symbol)

        # Score each headline
        scored_items = self._score_news_items(raw_headlines, symbol)

        # Aggregate overall sentiment
        overall = self._aggregate_sentiment(scored_items)

        # Social sentiment (simplified keyword-based)
        social = self._compute_social_sentiment(symbol, raw_headlines)

        # Event type breakdown
        event_breakdown = self._count_event_types(scored_items)

        result = {
            "symbol": symbol,
            "overall_score": overall["score"],
            "confidence": overall["confidence"],
            "label": overall["label"],
            "news_items": scored_items,
            "news_count": len(scored_items),
            "social_sentiment": social,
            "event_breakdown": event_breakdown,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._cache.set(cache_key, result)
        return result

    # ── News fetching ─────────────────────────────────────────────────

    async def _fetch_news(self, symbol: str) -> List[Dict[str, str]]:
        """
        Fetch news headlines from available sources.

        Tries Alpha Vantage → Polygon → yfinance news.
        Returns list of dicts with 'headline', 'source', 'date'.

        Args:
            symbol: Ticker symbol.

        Returns:
            List of news headline dicts.
        """
        headlines: List[Dict[str, str]] = []

        # Try Alpha Vantage
        try:
            av_headlines = await self._fetch_alpha_vantage_news(symbol)
            headlines.extend(av_headlines)
        except Exception as exc:
            logger.debug("Alpha Vantage news fetch failed for %s: %s", symbol, exc)

        # Try Polygon
        if not headlines:
            try:
                poly_headlines = await self._fetch_polygon_news(symbol)
                headlines.extend(poly_headlines)
            except Exception as exc:
                logger.debug("Polygon news fetch failed for %s: %s", symbol, exc)

        # Fallback: yfinance ticker news
        if not headlines:
            try:
                yf_headlines = await self._fetch_yfinance_news(symbol)
                headlines.extend(yf_headlines)
            except Exception as exc:
                logger.debug("yfinance news fetch failed for %s: %s", symbol, exc)

        return headlines[:25]  # Cap at 25 headlines

    async def _fetch_alpha_vantage_news(self, symbol: str) -> List[Dict[str, str]]:
        """Fetch news from Alpha Vantage."""
        import urllib.request
        import json as _json

        api_key = self._settings.alpha_vantage_api_key
        if not api_key:
            raise ValueError("Alpha Vantage API key not configured")

        url = (
            f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
            f"&tickers={symbol}&apikey={api_key}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "QuantNanggroeAI/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())

        headlines: List[Dict[str, str]] = []
        for item in data.get("feed", []):
            headlines.append({
                "headline": item.get("title", ""),
                "source": item.get("source", "alphavantage"),
                "date": item.get("time_published", ""),
            })
        return headlines

    async def _fetch_polygon_news(self, symbol: str) -> List[Dict[str, str]]:
        """Fetch news from Polygon.io."""
        import urllib.request
        import json as _json

        api_key = self._settings.polygon_api_key
        if not api_key:
            raise ValueError("Polygon API key not configured")

        url = (
            f"https://api.polygon.io/v2/reference/news"
            f"?ticker={symbol}&apiKey={api_key}&limit=15"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "QuantNanggroeAI/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())

        headlines: List[Dict[str, str]] = []
        for item in data.get("results", []):
            headlines.append({
                "headline": item.get("title", ""),
                "source": item.get("publisher", {}).get("name", "polygon"),
                "date": item.get("published_utc", ""),
            })
        return headlines

    async def _fetch_yfinance_news(self, symbol: str) -> List[Dict[str, str]]:
        """Fetch news from yfinance as a fallback."""
        try:
            import yfinance as yf
        except ImportError:
            return []

        ticker = yf.Ticker(symbol)
        news_data = ticker.news or []

        headlines: List[Dict[str, str]] = []
        for item in news_data[:15]:
            headlines.append({
                "headline": item.get("title", ""),
                "source": "yfinance",
                "date": str(item.get("providerPublishTime", "")),
            })
        return headlines

    # ── Scoring & aggregation ─────────────────────────────────────────

    def _score_news_items(
        self, raw_headlines: List[Dict[str, str]], symbol: str
    ) -> List[Dict[str, Any]]:
        """
        Score each news headline for sentiment and event classification.

        Args:
            raw_headlines: List of headline dicts.
            symbol: Ticker symbol for context.

        Returns:
            List of scored news items.
        """
        scored: List[Dict[str, Any]] = []

        for item in raw_headlines:
            headline = item.get("headline", "")
            if not headline:
                continue

            sentiment, confidence = self._classifier.score_headline(headline)
            event_type = self._classifier.classify_event(headline)

            # Check if headline is directly about the symbol
            symbol_relevance = 1.0 if symbol.upper() in headline.upper() else 0.5

            scored.append({
                "headline": headline,
                "source": item.get("source", "unknown"),
                "date": item.get("date", ""),
                "sentiment": sentiment,
                "confidence": round(confidence * symbol_relevance, 4),
                "event_type": event_type.value,
            })

        return scored

    @staticmethod
    def _aggregate_sentiment(scored_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate individual news scores into an overall sentiment score.

        Uses confidence-weighted average and applies time decay
        approximation (more recent headlines weighted more).

        Args:
            scored_items: List of scored news items.

        Returns:
            Dict with 'score', 'confidence', 'label'.
        """
        if not scored_items:
            return {
                "score": 0.0,
                "confidence": 0.0,
                "label": "NEUTRAL",
            }

        # Confidence-weighted average
        total_weight = 0.0
        weighted_sum = 0.0

        for idx, item in enumerate(scored_items):
            # Time-decay approximation: earlier items (older) get less weight
            recency_weight = 1.0 - (idx / (len(scored_items) + 1)) * 0.3
            weight = item["confidence"] * recency_weight
            weighted_sum += item["sentiment"] * weight
            total_weight += weight

        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        overall_score = max(-1.0, min(1.0, overall_score))

        # Overall confidence
        avg_confidence = sum(i["confidence"] for i in scored_items) / len(scored_items)
        # Boost confidence with more data points
        data_confidence = min(len(scored_items) / 10.0, 1.0)
        overall_confidence = round((avg_confidence * 0.6 + data_confidence * 0.4), 4)

        # Label
        if overall_score > 0.2:
            label = "BULLISH"
        elif overall_score < -0.2:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        return {
            "score": round(overall_score, 4),
            "confidence": round(overall_confidence, 4),
            "label": label,
        }

    @staticmethod
    def _compute_social_sentiment(
        symbol: str, headlines: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Compute simplified social sentiment.

        In production, this would connect to Twitter/Reddit APIs.
        For now, provides a structured placeholder with basic inference
        from available headline volume and sentiment.

        Args:
            symbol: Ticker symbol.
            headlines: Available headlines for context.

        Returns:
            Dict with social sentiment summary.
        """
        # Placeholder: derive a rough signal from headline volume
        volume_score = min(len(headlines) / 15.0, 1.0)

        # Calculate a simple net sentiment from headlines
        positive_count = 0
        negative_count = 0
        for h in headlines:
            text = h.get("headline", "").lower()
            if any(kw in text for kw in _BULLISH_KEYWORDS):
                positive_count += 1
            if any(kw in text for kw in _BEARISH_KEYWORDS):
                negative_count += 1

        total = positive_count + negative_count
        social_score = (positive_count - negative_count) / total if total > 0 else 0.0

        return {
            "platform": "aggregated",
            "mention_volume": len(headlines),
            "volume_score": round(volume_score, 4),
            "social_score": round(social_score, 4),
            "positive_mentions": positive_count,
            "negative_mentions": negative_count,
            "note": "Derived from news headlines; connect social APIs for live data",
        }

    @staticmethod
    def _count_event_types(
        scored_items: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Count events by type."""
        breakdown: Dict[str, int] = {e.value: 0 for e in NewsEventType}
        for item in scored_items:
            etype = item.get("event_type", "NOISE")
            breakdown[etype] = breakdown.get(etype, 0) + 1
        return breakdown


# ══════════════════════════════════════════════════════════════════════
# Singleton instance for @tool functions
# ══════════════════════════════════════════════════════════════════════

_default_st: SentimentTool | None = None


def _get_default_st() -> SentimentTool:
    """Get or create the default SentimentTool instance."""
    global _default_st
    if _default_st is None:
        _default_st = SentimentTool()
    return _default_st


# ══════════════════════════════════════════════════════════════════════
# LangChain @tool functions for agent consumption
# ══════════════════════════════════════════════════════════════════════


@tool
async def analyze_sentiment(symbol: str) -> str:
    """
    Analyze sentiment for a trading symbol from news and social data.

    Fetches news headlines from Alpha Vantage, Polygon, or yfinance,
    classifies events (MACRO, SCHEDULED, SHOCK, NOISE), scores
    sentiment using keyword analysis, and returns structured results.

    Args:
        symbol: Ticker symbol to analyze (e.g., 'AAPL', 'BTC/USDT')

    Returns:
        JSON string with overall sentiment score (-1.0 to +1.0),
        confidence, label (BULLISH/BEARISH/NEUTRAL), scored news
        items, social sentiment, and event breakdown.
    """
    try:
        st = _get_default_st()
        result = await st.analyze(symbol)
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.error("analyze_sentiment tool error: %s", exc)
        return json.dumps({"error": f"Sentiment analysis failed: {exc}", "symbol": symbol})
