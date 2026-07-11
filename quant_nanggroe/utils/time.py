"""Time and market hours utilities for Quant Nanggroe AI.

Handles market hours detection, timezone conversion,
and scheduling for different market types.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from enum import Enum
from zoneinfo import ZoneInfo


class MarketType(str, Enum):
    """Market type classification."""
    STOCKS_US = "stocks_us"
    FOREX = "forex"
    CRYPTO = "crypto"


# Market schedules (all times in local market timezone)
MARKET_SCHEDULES = {
    MarketType.STOCKS_US: {
        "timezone": "America/New_York",
        "open": time(9, 30),
        "close": time(16, 0),
        "weekends": False,
    },
    MarketType.FOREX: {
        "timezone": "UTC",
        "open": time(0, 0),
        "close": time(23, 59),
        "weekends": False,  # Forex closed on weekends
    },
    MarketType.CRYPTO: {
        "timezone": "UTC",
        "open": time(0, 0),
        "close": time(23, 59),
        "weekends": True,  # Crypto trades 24/7
    },
}


def is_market_open(market_type: MarketType = MarketType.CRYPTO) -> bool:
    """
    Check if a market is currently open.

    Args:
        market_type: Type of market to check

    Returns:
        True if the market is currently open
    """
    schedule = MARKET_SCHEDULES[market_type]
    tz = ZoneInfo(schedule["timezone"])
    now = datetime.now(tz)

    # Check weekend
    if not schedule["weekends"] and now.weekday() >= 5:
        return False

    # Check hours
    current_time = now.time()
    return schedule["open"] <= current_time <= schedule["close"]


def get_market_schedule(market_type: MarketType) -> dict:
    """
    Get the schedule for a market type.

    Args:
        market_type: Type of market

    Returns:
        Schedule dictionary with timezone, open, close, weekends
    """
    return MARKET_SCHEDULES[market_type]


def next_market_open(market_type: MarketType = MarketType.STOCKS_US) -> datetime:
    """
    Calculate the next market open time.

    Args:
        market_type: Type of market

    Returns:
        Datetime of the next market open
    """
    schedule = MARKET_SCHEDULES[market_type]
    tz = ZoneInfo(schedule["timezone"])
    now = datetime.now(tz)

    # Start from tomorrow
    candidate = now.replace(
        hour=schedule["open"].hour,
        minute=schedule["open"].minute,
        second=0,
        microsecond=0,
    )
    if candidate <= now:
        candidate += timedelta(days=1)

    # Skip weekends
    if not schedule["weekends"]:
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

    return candidate


def infer_market_from_symbol(symbol: str) -> MarketType:
    """
    Infer market type from symbol format.

    Args:
        symbol: Trading pair symbol

    Returns:
        Inferred market type
    """
    if "/" in symbol and any(
        symbol.endswith(f"/{quote}") for quote in ["USDT", "BUSD", "USD", "BTC", "ETH"]
    ):
        return MarketType.CRYPTO
    elif symbol.startswith("^") or symbol.endswith("=X"):
        return MarketType.FOREX
    else:
        return MarketType.STOCKS_US
