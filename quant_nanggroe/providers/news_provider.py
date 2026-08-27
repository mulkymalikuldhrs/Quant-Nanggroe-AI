"""News sentiment provider: per-symbol news sentiment scores.

Extracts news sentiment pipeline pattern from AI-Trader (Alpha Vantage).
Falls back to free public news APIs (no API key needed).
Returns news sentiment score for each symbol.
Graceful fallback — never crashes.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_NEWS_CACHE = TTLCache(default_ttl=600)

# Positive / negative keyword lists for simple keyword-based sentiment
_BULLISH_KEYWORDS = [
    "upgrade", "outperform", "beat", "growth", "bullish", "positive",
    "record", "profit", "surge", "rally", "breakout", "strong",
    "momentum", "expansion", "innovation", "partnership", "acquisition",
    "dividend", "buyback", "approval", "breakthrough",
]
_BEARISH_KEYWORDS = [
    "downgrade", "underperform", "miss", "decline", "bearish", "negative",
    "loss", "drop", "crash", "sell-off", "weak", "downturn",
    "recession", "inflation", "rate hike", "default", "bankruptcy",
    "layoff", "investigation", "lawsuit", "volatile",
]


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _alpha_vantage_news_sentiment(
    symbols: list[str],
    api_key: Optional[str] = None,
) -> Optional[list[dict[str, Any]]]:
    """Fetch news with ticker-level sentiment from Alpha Vantage.

    Requires ALPHA_VANTAGE_API_KEY. Returns normalized news items or None.
    """
    import urllib.parse
    from urllib.request import Request, urlopen

    if not api_key:
        return None

    tickers = ",".join(symbols)
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": tickers,
        "sort": "LATEST",
        "limit": 50,
        "apikey": api_key,
    }
    url = f"https://www.alphavantage.co/query?{urllib.parse.urlencode(params)}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("AV news fetch failed: %s", exc)
        return None

    feed = payload.get("feed") if isinstance(payload, dict) else None
    if not isinstance(feed, list):
        return None

    items = []
    for item in feed:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        if not title:
            continue
        ticker_sentiment = []
        for entry in item.get("ticker_sentiment") or []:
            if not isinstance(entry, dict):
                continue
            ticker = (entry.get("ticker") or "").strip()
            if ticker:
                ticker_sentiment.append({
                    "ticker": ticker,
                    "relevance_score": float(entry.get("relevance_score") or 0),
                    "sentiment_score": float(entry.get("ticker_sentiment_score") or 0),
                    "sentiment_label": entry.get("ticker_sentiment_label"),
                })
        items.append({
            "title": title,
            "summary": (item.get("summary") or "").strip(),
            "time_published": item.get("time_published", ""),
            "overall_sentiment_score": float(item.get("overall_sentiment_score") or 0),
            "overall_sentiment_label": item.get("overall_sentiment_label"),
            "ticker_sentiment": ticker_sentiment,
            "source": "alpha_vantage_news",
        })
    return items


def _fetch_rss_financial_news() -> Optional[list[dict[str, Any]]]:
    """Fetch financial headlines via RSS. No API key needed."""
    import xml.etree.ElementTree as ET
    from urllib.request import Request, urlopen

    rss_urls = [
        ("https://feeds.content.dowjones.io/public/rss/mw_topstories",
         "marketwatch"),
        ("https://www.cnbc.com/id/100003114/device/rss/rss.html",
         "cnbc"),
    ]

    items: list[dict[str, Any]] = []
    for url, source_name in rss_urls:
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=8) as resp:
                raw = resp.read()
            root = ET.fromstring(raw)
            # RSS 2.0: channel → item
            for item_elem in root.iter("item"):
                title = ""
                desc = ""
                for child in item_elem:
                    tag = child.tag.split("}")[-1]  # strip namespace
                    if tag == "title":
                        title = (child.text or "").strip()
                    elif tag == "description":
                        desc = (child.text or "").strip()
                if not title:
                    continue
                items.append({
                    "title": title,
                    "summary": desc[:500] if desc else "",
                    "source": source_name,
                    "overall_sentiment_score": 0.0,
                    "overall_sentiment_label": "neutral",
                    "ticker_sentiment": [],
                })
            break  # one successful RSS feed is enough
        except Exception as exc:
            logger.debug("RSS %s failed: %s", source_name, exc)

    return items if items else None


def _keyword_sentiment_for_symbol(
    symbol: str,
    news_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score news items for a specific symbol using keyword analysis."""
    sym = _normalize_symbol(symbol)
    relevant: list[dict[str, Any]] = []
    for item in news_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        text_upper = text.upper()
        # direct ticker mention or company name heuristics
        if sym not in text_upper and sym.replace(".", "") not in text_upper:
            continue
        relevant.append(item)

    if not relevant:
        return {
            "symbol": sym,
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
            "news_count": 0,
            "source": "keyword_fallback",
        }

    scores = []
    for item in relevant:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        bull_count = sum(1 for kw in _BULLISH_KEYWORDS if kw in text)
        bear_count = sum(1 for kw in _BEARISH_KEYWORDS if kw in text)
        net = (bull_count - bear_count) / max(bull_count + bear_count, 1)
        scores.append(net)

    avg_score = sum(scores) / len(scores)
    if avg_score > 0.3:
        label = "bullish"
    elif avg_score < -0.3:
        label = "bearish"
    else:
        label = "neutral"

    return {
        "symbol": sym,
        "sentiment_score": round(avg_score, 4),
        "sentiment_label": label,
        "news_count": len(relevant),
        "source": "keyword_analysis",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_news_sentiment(
    symbol: str,
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """Return news sentiment dict for a single symbol.

    Tiers:
        1. Alpha Vantage NEWS_SENTIMENT (needs api_key)
        2. RSS financial news → keyword sentiment analysis
        3. Zero-value fallback (no crash)
    """
    sym = _normalize_symbol(symbol)
    cache_key = f"news_sent:{sym}"
    cached = _NEWS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Tier 1: Alpha Vantage
    av_key = api_key or os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    try:
        items = _alpha_vantage_news_sentiment([sym], api_key=av_key)
        if items:
            ticker_scores = [
                ts["sentiment_score"]
                for item in items
                for ts in item.get("ticker_sentiment", [])
                if ts.get("ticker", "").upper() == sym
            ]
            if ticker_scores:
                avg = sum(ticker_scores) / len(ticker_scores)
                scaled = avg * 100  # -1..1 → -100..100
                label = "bullish" if avg > 0.15 else ("bearish" if avg < -0.15 else "neutral")
                result = {
                    "symbol": sym,
                    "sentiment_score": round(scaled, 2),
                    "sentiment_label": label,
                    "news_count": len(items),
                    "source": "alpha_vantage_news",
                }
                _NEWS_CACHE.set(cache_key, result)
                return result
    except Exception as exc:
        logger.debug("AV news sentiment for %s failed: %s", sym, exc)

    # Tier 2: RSS + keyword
    try:
        rss_items = _fetch_rss_financial_news()
        if rss_items:
            result = _keyword_sentiment_for_symbol(sym, rss_items)
        else:
            # residual: zero news found
            result = {
                "symbol": sym,
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "news_count": 0,
                "source": "rss_fallback",
            }
        _NEWS_CACHE.set(cache_key, result)
        return result
    except Exception as exc:
        logger.debug("RSS sentiment for %s failed: %s", sym, exc)

    result = {
        "symbol": sym,
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "news_count": 0,
        "source": "unavailable",
    }
    _NEWS_CACHE.set(cache_key, result)
    return result


def fetch_batch_news_sentiment(
    symbols: list[str],
    api_key: Optional[str] = None,
) -> dict[str, dict[str, Any]]:
    """Fetch sentiment for multiple symbols. Prefers AV batch request."""
    syms = [_normalize_symbol(s) for s in symbols]
    results: dict[str, dict[str, Any]] = {}

    # Try AV batch first
    av_key = api_key or os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    try:
        items = _alpha_vantage_news_sentiment(syms, api_key=av_key)
        if items:
            for sym in syms:
                ticker_scores = [
                    ts["sentiment_score"]
                    for item in items
                    for ts in item.get("ticker_sentiment", [])
                    if ts.get("ticker", "").upper() == sym
                ]
                if ticker_scores:
                    avg = sum(ticker_scores) / len(ticker_scores)
                    scaled = avg * 100
                    label = "bullish" if avg > 0.15 else ("bearish" if avg < -0.15 else "neutral")
                    results[sym] = {
                        "symbol": sym,
                        "sentiment_score": round(scaled, 2),
                        "sentiment_label": label,
                        "news_count": len(items),
                        "source": "alpha_vantage_news",
                    }
                    _NEWS_CACHE.set(f"news_sent:{sym}", results[sym])
            remaining = [s for s in syms if s not in results]
        else:
            remaining = syms
    except Exception:
        remaining = syms

    # Fallback per symbol
    if remaining:
        rss_items = _fetch_rss_financial_news()
        for sym in remaining:
            if rss_items:
                result = _keyword_sentiment_for_symbol(sym, rss_items)
            else:
                result = {
                    "symbol": sym,
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                    "news_count": 0,
                    "source": "unavailable",
                }
            results[sym] = result
            _NEWS_CACHE.set(f"news_sent:{sym}", result)

    return results


