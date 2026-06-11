"""Input validation utilities for Quant Nanggroe AI.

Validates trading symbols, timeframes, quantities, and other inputs
before they enter the system.
"""

from __future__ import annotations

import re
from typing import Optional

from quant_nanggroe.types.market import TimeFrame


# Symbol patterns
CRYPTO_PATTERN = re.compile(r"^[A-Z0-9]{2,10}/[A-Z0-9]{2,10}$")
STOCK_PATTERN = re.compile(r"^[A-Z]{1,5}$")
FOREX_PATTERN = re.compile(r"^[A-Z]{3}=X$|^/[A-Z]{3}$")


def validate_symbol(symbol: str, market: Optional[str] = None) -> bool:
    """
    Validate a trading symbol format.

    Args:
        symbol: Symbol to validate
        market: Optional market type hint ('crypto', 'stocks', 'forex')

    Returns:
        True if the symbol is valid
    """
    if not symbol or not isinstance(symbol, str):
        return False
    symbol = symbol.strip().upper()

    if market == "crypto":
        return bool(CRYPTO_PATTERN.match(symbol))
    elif market == "stocks":
        return bool(STOCK_PATTERN.match(symbol))
    elif market == "forex":
        return bool(FOREX_PATTERN.match(symbol))
    else:
        # Accept any reasonable format
        return bool(
            CRYPTO_PATTERN.match(symbol)
            or STOCK_PATTERN.match(symbol)
            or FOREX_PATTERN.match(symbol)
            or len(symbol) <= 20
        )


def validate_timeframe(timeframe: str) -> bool:
    """
    Validate a timeframe string.

    Args:
        timeframe: Timeframe to validate

    Returns:
        True if the timeframe is valid
    """
    try:
        TimeFrame(timeframe)
        return True
    except ValueError:
        return False


def validate_quantity(quantity: float, min_qty: float = 0.0) -> bool:
    """
    Validate a trade quantity.

    Args:
        quantity: Quantity to validate
        min_qty: Minimum allowed quantity

    Returns:
        True if the quantity is valid
    """
    return isinstance(quantity, (int, float)) and quantity > min_qty


def validate_price(price: float) -> bool:
    """
    Validate a price value.

    Args:
        price: Price to validate

    Returns:
        True if the price is valid (positive and finite)
    """
    import math
    return isinstance(price, (int, float)) and price > 0 and math.isfinite(price)
