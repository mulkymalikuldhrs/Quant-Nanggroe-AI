"""Reddit Retail Mania Provider — mention spike detection from social media.

Port pattern from TradeBobbyTerminal/dashboard/reddit-mania.js.
Scrapes r/wallstreetbets, r/CryptoCurrency, r/stocks for $TICKER mentions.
No API key needed. 1800s TTL. Graceful fallback — never crashes.

Note: Reddit rate-limits datacenter IPs. If all sources fail, returns empty data.
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=1800)

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

REDDIT_HOSTS = ["https://old.reddit.com", "https://www.reddit.com"]

SUBS = [
    ("wallstreetbets", 50),
    ("stocks", 30),
    ("CryptoCurrency", 30),
    ("options", 25),
]

TICKER_RE = re.compile(r"\$?\b[A-Z]{2,5}\b")

STOP_TICKERS = {
    "A", "I", "M", "S", "U", "X", "TV", "OK", "DM", "CEO", "CFO", "IPO",
    "ETF", "FOMO", "YOLO", "AI", "API", "APR", "AUG", "BUY", "BTW", "CAD",
    "EOD", "EOY", "EPS", "EUR", "FED", "GBP", "IDK", "IRA", "IRS", "JPY",
    "JUL", "JUN", "LOL", "MOM", "NOV", "OCT", "OMG", "SEC", "SEP", "TBH",
    "USD", "USA", "WSB", "UI", "UK", "US", "EU", "PR", "HR", "PM", "AM",
    "OP", "TLDR", "EDIT", "YTD", "ATH", "ATL", "MIA", "BOJ", "ECB", "GDP",
    "CPI", "PCE", "PPI", "NEW", "OLD", "TOP", "LOW", "HIGH", "BIG", "WIN",
    "LOSS", "GAIN", "CALL", "PUT", "LONG", "SHORT", "BULL", "BEAR", "PUMP",
    "DUMP", "GO", "NO", "YES", "OUT", "OFF", "ON", "UP", "OWN", "GET",
    "BAD", "RED", "RIP", "LFG", "VS", "IT", "ITS", "IMO", "LMK", "ROI",
    "ASAP", "ESG", "FUD", "FYI", "HQ", "NFA", "PSA", "RH", "SP", "OTC",
    "CFD", "DIP", "FY", "HOLD", "SELL", "BTFD", "ROFL", "HOPE", "MOON",
    "BAGS", "PORN", "GME", "AMC",
}


def _safe_fetch(url: str, timeout: int = 10) -> Optional[Any]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": BROWSER_UA,
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Fetch failed %s: %s", url, exc)
        return None


def _fetch_sub_posts(sub_name: str, limit: int) -> list[dict[str, Any]]:
    for host in REDDIT_HOSTS:
        url = f"{host}/r/{sub_name}/new.json?limit={limit}&raw_json=1"
        j = _safe_fetch(url)
        if j is None:
            continue
        children = j.get("data", {}).get("children")
        if isinstance(children, list):
            return [c["data"] for c in children if isinstance(c, dict)]
    return []


def _extract_tickers(text: str) -> list[str]:
    if not text:
        return []
    matches = TICKER_RE.findall(text)
    result = []
    for m in matches:
        t = m.lstrip("$")
        if len(t) >= 2 and len(t) <= 5 and t not in STOP_TICKERS:
            result.append(t)
    return result


class RedditManiaProvider:
    def __init__(self) -> None:
        self._cache = _CACHE
        self._history_snapshots: list[dict[str, Any]] = []

    def fetch_mania(self) -> dict[str, Any]:
        cache_key = "reddit_mania"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        counts: dict[str, int] = {}
        recent: dict[str, list[dict[str, Any]]] = {}
        total_posts = 0

        for sub_name, limit in SUBS:
            posts = _fetch_sub_posts(sub_name, limit)
            for p in posts:
                total_posts += 1
                title = p.get("title") or ""
                selftext = (p.get("selftext") or "")[:300]
                text = f"{title} {selftext}"
                tickers = _extract_tickers(text)
                for t in tickers:
                    counts[t] = counts.get(t, 0) + 1
                    if t not in recent:
                        recent[t] = []
                    if len(recent[t]) < 3:
                        recent[t].append({
                            "sub": sub_name,
                            "title": title[:100],
                            "score": p.get("score", 0),
                            "url": f"https://reddit.com{p.get('permalink', '')}",
                            "created": p.get("created_utc", 0),
                        })
            time.sleep(0.5)

        if total_posts == 0:
            result: dict[str, Any] = {
                "top_tickers": [],
                "total_mentions": 0,
                "posts_scanned": 0,
                "mania_level": "UNKNOWN",
                "source": "none",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "all subreddit fetches failed",
            }
            self._cache.set(cache_key, result)
            return result

        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:25]

        last_snapshot = (
            self._history_snapshots[-1] if self._history_snapshots else {"counts": {}}
        )
        prev_counts = last_snapshot.get("counts", {})

        top_tickers = []
        for t, c in ranked:
            prev_c = prev_counts.get(t, 0)
            delta = c - prev_c
            spike_factor = round(c / prev_c, 2) if prev_c > 0 else (99 if c > 2 else 1)
            top_tickers.append({
                "symbol": t,
                "mentions": c,
                "previous": prev_c,
                "delta": delta,
                "spike_factor": spike_factor,
                "samples": recent.get(t, []),
            })

        self._history_snapshots.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "counts": {r["symbol"]: r["mentions"] for r in top_tickers},
        })
        self._history_snapshots = self._history_snapshots[-48:]

        total_mentions = sum(r["mentions"] for r in top_tickers)
        if total_mentions > 100:
            mania_level = "EXTREME"
        elif total_mentions > 60:
            mania_level = "ELEVATED"
        elif total_mentions > 30:
            mania_level = "NORMAL"
        else:
            mania_level = "CALM"

        result = {
            "top_tickers": top_tickers,
            "total_mentions": total_mentions,
            "posts_scanned": total_posts,
            "mania_level": mania_level,
            "source": "reddit",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._cache.set(cache_key, result)
        return result

    def get_top_tickers(self, limit: int = 10) -> list[dict[str, Any]]:
        data = self.fetch_mania()
        return data.get("top_tickers", [])[:limit]

    def get_spikes(self) -> list[dict[str, Any]]:
        data = self.fetch_mania()
        tickers = data.get("top_tickers", [])
        return [t for t in tickers if t.get("spike_factor", 0) >= 2]
