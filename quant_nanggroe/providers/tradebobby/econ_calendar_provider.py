"""Economic Calendar Provider — rule-based recurring US macro events.

No API key required. Computes upcoming events from deterministic rules:
NFP, CPI, FOMC, Weekly Claims, EIA Crude, PCE, Retail Sales.

Each event carries severity, affected symbols, and T-minus countdown.
Results cached for 3600s.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone, time as dt_time
from typing import Any

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

_CACHE = TTLCache(default_ttl=3600)

_ET = timezone(timedelta(hours=-5))  # US Eastern (fixed offset, no DST)
_ET_EDT = timezone(timedelta(hours=-4))  # US Eastern Daylight

# Weekday constants
_MON, _TUE, _WED, _THU, _FRI, _SAT, _SUN = range(7)

# ── Event definitions ────────────────────────────────────────────────

_EVENTS: list[dict[str, Any]] = [
    {
        "name": "Non-Farm Payrolls (NFP)",
        "short": "NFP",
        "severity": "HIGH",
        "time_et": "08:30",
        "affects": ["^GSPC", "^NDX", "^DJI", "DX-Y.NYB", "^TNX", "^VIX", "GC=F"],
        "rule": "first_friday",
    },
    {
        "name": "Consumer Price Index (CPI)",
        "short": "CPI",
        "severity": "HIGH",
        "time_et": "08:30",
        "affects": ["^GSPC", "^NDX", "DX-Y.NYB", "^TNX", "^VIX", "GC=F"],
        "rule": "second_wednesday",
    },
    {
        "name": "FOMC Rate Decision",
        "short": "FOMC",
        "severity": "HIGH",
        "time_et": "14:00",
        "affects": ["^GSPC", "^NDX", "^DJI", "DX-Y.NYB", "^TNX", "^FVX", "^VIX", "GC=F", "IEF", "LQD"],
        "rule": "third_wednesday",
    },
    {
        "name": "Initial Jobless Claims",
        "short": "Claims",
        "severity": "LOW",
        "time_et": "08:30",
        "affects": ["^GSPC", "^NDX", "DX-Y.NYB"],
        "rule": "weekly_thursday",
    },
    {
        "name": "EIA Crude Oil Inventory",
        "short": "EIA",
        "severity": "LOW",
        "time_et": "10:30",
        "affects": ["CL=F", "BZ=F", "XLE"],
        "rule": "weekly_wednesday",
    },
    {
        "name": "Personal Consumption Expenditures (PCE)",
        "short": "PCE",
        "severity": "MEDIUM",
        "time_et": "08:30",
        "affects": ["^GSPC", "^NDX", "DX-Y.NYB", "^TNX", "^VIX"],
        "rule": "last_business_day",
    },
    {
        "name": "Advance Retail Sales",
        "short": "Retail Sales",
        "severity": "MEDIUM",
        "time_et": "08:30",
        "affects": ["^GSPC", "^NDX", "XLY", "XLP"],
        "rule": "first_business_day_after_15th",
    },
]


# ── Date calculation helpers ──────────────────────────────────────────


def _is_business_day(d: datetime) -> bool:
    return d.weekday() < 5


def _next_business_day(d: datetime) -> datetime:
    nxt = d + timedelta(days=1)
    while not _is_business_day(nxt):
        nxt += timedelta(days=1)
    return nxt


def _prev_business_day(d: datetime) -> datetime:
    prev = d - timedelta(days=1)
    while not _is_business_day(prev):
        prev -= timedelta(days=1)
    return prev


def _first_friday(year: int, month: int) -> datetime:
    """First Friday of given month."""
    d = datetime(year, month, 1)
    while d.weekday() != _FRI:
        d += timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime:
    """Nth occurrence of weekday in month (1-indexed)."""
    d = datetime(year, month, 1)
    count = 0
    while True:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
        d += timedelta(days=1)


def _last_business_day(year: int, month: int) -> datetime:
    """Last business day of month."""
    if month == 12:
        d = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = datetime(year, month + 1, 1) - timedelta(days=1)
    while not _is_business_day(d):
        d -= timedelta(days=1)
    return d


def _first_business_day_after_15th(year: int, month: int) -> datetime:
    """First business day after the 15th of month."""
    d = datetime(year, month, 16)
    while not _is_business_day(d):
        d += timedelta(days=1)
    return d


def _parse_time(time_str: str) -> dt_time:
    h, m = map(int, time_str.split(":"))
    return dt_time(h, m)


def _resolve_event_date(event: dict[str, Any], reference: datetime) -> datetime | None:
    """Compute the next occurrence date for a given event rule."""
    year, month = reference.year, reference.month
    rule = event["rule"]

    if rule == "first_friday":
        d = _first_friday(year, month)
    elif rule == "second_wednesday":
        d = _nth_weekday(year, month, _WED, 2)
    elif rule == "third_wednesday":
        d = _nth_weekday(year, month, _WED, 3)
    elif rule == "weekly_thursday":
        # Next Thursday from today
        d = reference
        while d.weekday() != _THU:
            d += timedelta(days=1)
    elif rule == "weekly_wednesday":
        # Next Wednesday from today
        d = reference
        while d.weekday() != _WED:
            d += timedelta(days=1)
    elif rule == "last_business_day":
        d = _last_business_day(year, month)
    elif rule == "first_business_day_after_15th":
        d = _first_business_day_after_15th(year, month)
    else:
        return None

    # Attach time
    t = _parse_time(event["time_et"])
    return d.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)


def _candidates_for_window(
    event: dict[str, Any],
    now_utc: datetime,
    hours: int,
) -> list[datetime]:
    """Return all candidate datetimes within [now, now+hours]."""
    candidates: list[datetime] = []
    t = _parse_time(event["time_et"])
    # Check current month and next month to handle edge cases
    for offset_month in range(2):
        m = now_utc.month + offset_month
        y = now_utc.year
        if m > 12:
            m -= 12
            y += 1

        rule = event["rule"]
        if rule == "first_friday":
            d = _first_friday(y, m)
        elif rule == "second_wednesday":
            d = _nth_weekday(y, m, _WED, 2)
        elif rule == "third_wednesday":
            d = _nth_weekday(y, m, _WED, 3)
        elif rule == "weekly_thursday":
            d = datetime(y, m, now_utc.day)
            while d.weekday() != _THU:
                d += timedelta(days=1)
            if d.month != m:
                continue
        elif rule == "weekly_wednesday":
            d = datetime(y, m, now_utc.day)
            while d.weekday() != _WED:
                d += timedelta(days=1)
            if d.month != m:
                continue
        elif rule == "last_business_day":
            d = _last_business_day(y, m)
        elif rule == "first_business_day_after_15th":
            d = _first_business_day_after_15th(y, m)
        else:
            continue

        dt = d.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        # Convert to UTC for comparison
        dt_utc = dt.replace(tzinfo=_ET).astimezone(timezone.utc)
        window_end = now_utc + timedelta(hours=hours)
        if now_utc <= dt_utc <= window_end:
            candidates.append(dt_utc)

    return candidates


# ── Provider class ────────────────────────────────────────────────────


class EconCalendarProvider:
    """Rule-based economic calendar. No API key needed.

    Computes upcoming US macro events from deterministic rules.
    Each event includes severity, affected symbols, and T-minus countdown.
    Results cached for 3600s.
    """

    def __init__(self) -> None:
        self._cache = _CACHE

    def get_upcoming(self, hours: int = 48) -> list[dict[str, Any]]:
        """Return upcoming events within `hours` window, sorted by time.

        Each event dict contains:
            name, short, severity, datetime_utc, datetime_et,
            t_minus, t_minus_display, affects, rule
        """
        cache_key = f"econ_calendar:upcoming:{hours}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        now_utc = datetime.now(timezone.utc)
        upcoming: list[dict[str, Any]] = []

        for event in _EVENTS:
            try:
                candidates = _candidates_for_window(event, now_utc, hours)
            except Exception as exc:
                logger.warning("Econ calendar rule '%s' failed: %s", event["short"], exc)
                continue

            for dt_utc in candidates:
                delta = dt_utc - now_utc
                total_minutes = int(delta.total_seconds() // 60)
                h, m = divmod(total_minutes, 60)
                t_minus_display = f"{h}h {m:02d}m"

                dt_et = dt_utc.astimezone(_ET)
                upcoming.append({
                    "name": event["name"],
                    "short": event["short"],
                    "severity": event["severity"],
                    "datetime_utc": dt_utc.isoformat(),
                    "datetime_et": dt_et.strftime("%Y-%m-%d %H:%M ET"),
                    "t_minus_minutes": total_minutes,
                    "t_minus_display": t_minus_display,
                    "affects": event["affects"],
                    "rule": event["rule"],
                })

        upcoming.sort(key=lambda e: e["datetime_utc"])
        self._cache.set(cache_key, upcoming)
        return upcoming

    def get_event_map(self) -> dict[str, dict[str, Any]]:
        """Return static event definitions keyed by short name."""
        cache_key = "econ_calendar:event_map"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        result = {
            e["short"]: {
                "name": e["name"],
                "severity": e["severity"],
                "affects": e["affects"],
                "rule": e["rule"],
            }
            for e in _EVENTS
        }
        self._cache.set(cache_key, result)
        return result

    def get_high_impact_within(self, hours: int = 24) -> list[dict[str, Any]]:
        """Return only HIGH severity events within window."""
        return [
            e for e in self.get_upcoming(hours=hours)
            if e["severity"] == "HIGH"
        ]


# ponytail: US-only, no DST handling (fixed -5/-4), add intl events when needed.
