"""Time and market hours utilities for Quant Nanggroe AI.

Provides helpers for market hours detection, timezone handling,
and time-based calculations.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Optional


def utc_now() -> datetime:
    """Return current UTC time as a timezone-aware datetime.

    Returns:
        Current UTC datetime.
    """
    return datetime.now(tz=timezone.utc)


def is_market_open(
    exchange: str = "NYSE",
    dt: Optional[datetime] = None,
) -> bool:
    """Check if a market is currently open.

    Supports major exchanges with simplified schedules.
    Does not account for holidays — use a proper market calendar
    for production.

    Args:
        exchange: Exchange name (NYSE, NASDAQ, BINANCE, etc.).
        dt: Datetime to check (defaults to current UTC time).

    Returns:
        True if the market is open at the given time.
    """
    if dt is None:
        dt = utc_now()

    # Crypto markets: always open
    if exchange.upper() in ("BINANCE", "COINBASE", "KRAKEN", "BYBIT"):
        return True

    # US equity markets: Mon–Fri, 9:30–16:00 ET
    if exchange.upper() in ("NYSE", "NASDAQ", "ALPACA"):
        # Convert to Eastern Time (ET = UTC-5)
        et_hour = (dt.hour - 5) % 24
        et_minute = dt.minute
        et_weekday = dt.weekday()

        # Weekend check
        if et_weekday >= 5:
            return False

        # Market hours: 9:30–16:00 ET
        current_et_minutes = et_hour * 60 + et_minute
        open_minutes = 9 * 60 + 30  # 9:30
        close_minutes = 16 * 60  # 16:00

        return open_minutes <= current_et_minutes < close_minutes

    # Default: assume closed
    return False


def next_market_open(
    exchange: str = "NYSE",
    dt: Optional[datetime] = None,
) -> datetime:
    """Calculate the next market open time.

    Args:
        exchange: Exchange name.
        dt: Reference datetime (defaults to current UTC time).

    Returns:
        Datetime of the next market open.
    """
    if dt is None:
        dt = utc_now()

    # Crypto: always open
    if exchange.upper() in ("BINANCE", "COINBASE", "KRAKEN", "BYBIT"):
        return dt

    # US equity markets
    if exchange.upper() in ("NYSE", "NASDAQ", "ALPACA"):
        # Try each subsequent day until we find a weekday
        for delta in range(8):
            candidate = dt + timedelta(days=delta)
            if candidate.weekday() < 5:  # Mon–Fri
                # Market opens at 9:30 ET = 14:30 UTC
                open_time = candidate.replace(
                    hour=14, minute=30, second=0, microsecond=0, tzinfo=timezone.utc
                )
                if open_time > dt:
                    return open_time

    return dt + timedelta(hours=1)


def timeframe_to_seconds(timeframe: str) -> int:
    """Convert a timeframe string to seconds.

    Supports formats like '1m', '5m', '1h', '4h', '1d', '1w'.

    Args:
        timeframe: Timeframe string.

    Returns:
        Number of seconds in the timeframe.
    """
    mapping = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "1w": 604800,
        "1M": 2592000,
    }
    return mapping.get(timeframe, 86400)


def seconds_to_timeframe(seconds: int) -> str:
    """Convert seconds to the closest standard timeframe string.

    Args:
        seconds: Number of seconds.

    Returns:
        Timeframe string.
    """
    mapping = {
        60: "1m",
        300: "5m",
        900: "15m",
        1800: "30m",
        3600: "1h",
        14400: "4h",
        86400: "1d",
        604800: "1w",
        2592000: "1M",
    }
    # Find closest timeframe
    closest = min(mapping.keys(), key=lambda x: abs(x - seconds))
    return mapping[closest]
