"""Input validation utilities for Quant Nanggroe AI.

Provides validation functions for common inputs like symbols,
periods, and OHLCV data.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np

from quant_nanggroe.types.market import OHLCV


# Standard symbol pattern: uppercase letters, numbers, hyphens, slashes, dots
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\-/.]{0,30}[A-Z0-9]$")


class ValidationError(ValueError):
    """Raised when input validation fails."""


def validate_symbol(symbol: str) -> str:
    """Validate and normalize a trading symbol.

    Args:
        symbol: Symbol string to validate.

    Returns:
        Normalized uppercase symbol string.

    Raises:
        ValidationError: If the symbol is invalid.
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty")

    normalized = symbol.strip().upper()

    if len(normalized) < 1 or len(normalized) > 32:
        raise ValidationError(f"Symbol length must be 1–32 chars, got {len(normalized)}")

    if not _SYMBOL_PATTERN.match(normalized):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Must contain only uppercase letters, numbers, hyphens, slashes, and dots."
        )

    return normalized


def validate_period(period: int, min_period: int = 1, max_period: int = 1000) -> int:
    """Validate a lookback period.

    Args:
        period: Period to validate.
        min_period: Minimum allowed period.
        max_period: Maximum allowed period.

    Returns:
        Validated period.

    Raises:
        ValidationError: If the period is out of range.
    """
    if not isinstance(period, int) or period < min_period or period > max_period:
        raise ValidationError(
            f"Period must be an integer between {min_period} and {max_period}, got {period}"
        )
    return period


def validate_ohlcv(candles: list[OHLCV]) -> list[OHLCV]:
    """Validate a list of OHLCV candles for consistency.

    Checks:
    - Each candle has high >= low
    - Each candle has high >= open and high >= close
    - Each candle has low <= open and low <= close
    - Timestamps are in ascending order

    Args:
        candles: List of OHLCV candles to validate.

    Returns:
        The same list if valid.

    Raises:
        ValidationError: If any candle is invalid.
    """
    if not candles:
        raise ValidationError("Candle list cannot be empty")

    for i, c in enumerate(candles):
        if c.high < c.low:
            raise ValidationError(
                f"Candle {i}: high ({c.high}) < low ({c.low})"
            )
        if c.high < c.open:
            raise ValidationError(
                f"Candle {i}: high ({c.high}) < open ({c.open})"
            )
        if c.high < c.close:
            raise ValidationError(
                f"Candle {i}: high ({c.high}) < close ({c.close})"
            )
        if c.low > c.open:
            raise ValidationError(
                f"Candle {i}: low ({c.low}) > open ({c.open})"
            )
        if c.low > c.close:
            raise ValidationError(
                f"Candle {i}: low ({c.low}) > close ({c.close})"
            )

    # Check ascending timestamps
    for i in range(1, len(candles)):
        if candles[i].timestamp < candles[i - 1].timestamp:
            raise ValidationError(
                f"Candle {i}: timestamp {candles[i].timestamp} < "
                f"previous {candles[i-1].timestamp}"
            )

    return candles


def validate_price_series(
    closes: np.ndarray,
    min_length: int = 1,
) -> np.ndarray:
    """Validate a price series array.

    Args:
        closes: Price series array.
        min_length: Minimum required length.

    Returns:
        Validated array.

    Raises:
        ValidationError: If the array is invalid.
    """
    arr = np.asarray(closes, dtype=float)

    if len(arr) < min_length:
        raise ValidationError(
            f"Price series must have at least {min_length} elements, got {len(arr)}"
        )

    if np.any(arr <= 0):
        raise ValidationError("Price series must not contain non-positive values")

    if np.any(np.isnan(arr)):
        raise ValidationError("Price series must not contain NaN values")

    if np.any(np.isinf(arr)):
        raise ValidationError("Price series must not contain Inf values")

    return arr
