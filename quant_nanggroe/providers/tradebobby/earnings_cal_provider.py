"""Earnings Calendar Provider — NASDAQ earnings API.

Ported from TradeBobbyTerminal/dashboard/earnings-cal.js.
No API key needed. 43200s TTL cache (12h). Filters high-impact tickers.
Graceful fallback — never crashes.
"""
from __future__ import annotations

import datetime
import json
import logging
import urllib.request
from typing import Any

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=43200)

NASDAQ_EARNINGS = "https://api.nasdaq.com/api/calendar/earnings"

HIGH_IMPACT = frozenset({
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "BAC", "GS", "MS", "WFC", "C",
    "AVGO", "AMD", "INTC", "TSM", "MU", "ASML", "LRCX", "AMAT", "QCOM", "MRVL", "NXPI",
    "XOM", "CVX", "COP", "OXY", "SLB", "EOG", "PXD",
    "CRM", "ORCL", "ADBE", "NOW", "IBM", "UBER", "PYPL", "SNOW",
    "WMT", "HD", "COST", "MCD", "SBUX", "NKE", "DIS", "LULU",
    "UNH", "PFE", "LLY", "MRK", "JNJ", "ABBV",
    "NFLX", "BA", "CAT", "GE", "BRK.B", "BRK.A",
    "COIN", "MSTR", "RIOT", "MARA", "PLTR", "RBLX",
})

MAG7 = frozenset({"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"})


def _fmt_date(d: datetime.date) -> str:
    return d.isoformat()


def _fetch_date(date_str: str) -> list[dict[str, Any]]:
    url = f"{NASDAQ_EARNINGS}?date={date_str}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            j = json.loads(resp.read().decode())
        rows = j.get("data", {}).get("rows") if isinstance(j, dict) else None
        return rows if isinstance(rows, list) else []
    except Exception as exc:
        logger.debug("Earnings fetch failed %s: %s", date_str, exc)
        return []


class EarningsCalendarProvider:
    def __init__(self) -> None:
        self._cache = _CACHE

    def get_earnings(self) -> dict[str, Any]:
        cache_key = "earnings_all"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        today = datetime.date.today()
        events: list[dict[str, Any]] = []
        mag7: list[dict[str, Any]] = []

        for i in range(14):
            d = today + datetime.timedelta(days=i)
            date_str = _fmt_date(d)
            rows = _fetch_date(date_str)
            for row in rows:
                sym = (row.get("symbol") or "").upper()
                if sym not in HIGH_IMPACT:
                    continue
                event = {
                    "date": date_str,
                    "symbol": sym,
                    "name": row.get("name"),
                    "time": row.get("time"),
                    "eps_forecast": row.get("epsForecast"),
                    "last_year_eps": row.get("lastYearEPS"),
                    "market_cap": row.get("marketCap"),
                    "fiscal_q": row.get("fiscalQuarterEnding"),
                    "impact": "EXTREME" if sym in MAG7 else "HIGH",
                    "is_mag7": sym in MAG7,
                }
                events.append(event)
                if sym in MAG7:
                    mag7.append(event)

        events.sort(key=lambda e: e["date"])
        mag7.sort(key=lambda e: e["date"])

        result = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "events": events,
            "mag7": mag7,
        }
        self._cache.set(cache_key, result)
        return result

    def get_upcoming_high_impact(self) -> list[dict[str, Any]]:
        cache_key = "earnings_upcoming"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        all_data = self.get_earnings()
        today = datetime.date.today()
        cutoff = today + datetime.timedelta(days=7)

        filtered = [
            e for e in all_data.get("events", [])
            if e["symbol"] in HIGH_IMPACT and today <= datetime.date.fromisoformat(e["date"]) <= cutoff
        ]
        self._cache.set(cache_key, filtered)
        return filtered

    def get_earnings_pulse(self) -> dict[str, Any]:
        all_data = self.get_earnings()
        upcoming = self.get_upcoming_high_impact()
        mag7_events = all_data.get("mag7", [])

        week_mag7 = [e for e in mag7_events if datetime.date.fromisoformat(e["date"]) <= datetime.date.today() + datetime.timedelta(days=7)]

        impact_counts: dict[str, int] = {}
        for e in upcoming:
            impact_type = e.get("impact", "HIGH")
            impact_counts[impact_type] = impact_counts.get(impact_type, 0) + 1

        return {
            "total_key_events": len(all_data.get("events", [])),
            "upcoming_7d": len(upcoming),
            "mag7_next_7d": len(week_mag7),
            "impact_breakdown": impact_counts,
            "mag7_events": week_mag7,
            "upcoming_events": upcoming,
            "all_events": all_data.get("events", []),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
