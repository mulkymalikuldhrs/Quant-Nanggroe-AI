"""
Edge Case Handler — Defensive Wrappers for Engine Modules
=========================================================

Provides input validation at module boundaries, NaN/None handling for
financial data, empty dataframe handling, division-by-zero protection,
and overflow protection for large numbers.

Usage::

    from quant_nanggroe.engine.core.edge_case_handler import (
        safe_divide, validate_dataframe, validate_returns,
        safe_kelly_fraction, safe_price, defensive_wrapper,
    )

    @defensive_wrapper(fallback_value=0.0)
    def compute_metric(data):
        ...
"""

from __future__ import annotations

import functools
import logging
import math
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

import numpy as np
import pandas as pd

from quant_nanggroe.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Constants ─────────────────────────────────────────────────────────
MAX_FLOAT = 1e308
MIN_FLOAT = 1e-308
MAX_ABS_RETURN = 10.0   # 1000% daily return cap
MAX_LEVERAGE = 10.0
MAX_POSITION_SIZE = 1e9
MAX_PRICE = 1e12
MIN_PRICE = 1e-12
MIN_VOLUME = 0
MAX_TRADE_HISTORY = 100_000


# ── Numeric Safety ────────────────────────────────────────────────────

def safe_divide(
    a: float,
    b: float,
    default: float = 0.0,
    allow_zero: bool = False,
) -> float:
    """Safe division with zero-divisor protection.

    Args:
        a: Numerator.
        b: Denominator.
        default: Value returned if division is unsafe.
        allow_zero: If True, returns 0.0 when denominator is zero.

    Returns:
        Result of a / b, or default on failure.
    """
    try:
        if b is None or math.isnan(b) or math.isinf(b):
            return default if not allow_zero else 0.0
        if a is None or math.isnan(a) or math.isinf(a):
            return default
        if abs(b) < MIN_FLOAT:
            return default if not allow_zero else 0.0
        result = a / b
        if math.isinf(result) or math.isnan(result):
            return default
        if abs(result) > MAX_FLOAT:
            return default
        return result
    except (TypeError, ValueError, ZeroDivisionError):
        return default


def safe_sqrt(x: float, default: float = 0.0) -> float:
    """Safe square root — returns default for negative inputs."""
    try:
        if x is None or math.isnan(x):
            return default
        if x < 0:
            return default
        result = math.sqrt(x)
        return default if math.isinf(result) else result
    except (TypeError, ValueError):
        return default


def safe_log(x: float, default: float = 0.0) -> float:
    """Safe natural log — returns default for non-positive inputs."""
    try:
        if x is None or math.isnan(x) or x <= 0:
            return default
        result = math.log(x)
        return default if math.isinf(result) else result
    except (TypeError, ValueError):
        return default


def safe_pow(base: float, exp: float, default: float = 0.0) -> float:
    """Safe power operation with overflow protection."""
    try:
        if base is None or exp is None:
            return default
        if math.isnan(base) or math.isnan(exp):
            return default
        result = base ** exp
        if math.isinf(result) or math.isnan(result):
            return default
        if abs(result) > MAX_FLOAT:
            return default
        return result
    except (TypeError, ValueError, OverflowError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a value to [low, high]."""
    try:
        if value is None or math.isnan(value):
            return low
        return max(low, min(high, value))
    except TypeError:
        return low


# ── DataFrame Validation ─────────────────────────────────────────────

def validate_dataframe(
    df: Optional[pd.DataFrame],
    required_columns: Optional[List[str]] = None,
    min_rows: int = 1,
    name: str = "data",
) -> pd.DataFrame:
    """Validate and sanitize a DataFrame input.

    Args:
        df: Input DataFrame.
        required_columns: Columns that must be present.
        min_rows: Minimum number of rows required.
        name: Name for error messages.

    Returns:
        Validated and sanitized DataFrame.

    Raises:
        ValueError: If DataFrame is empty or missing required columns.
    """
    if df is None:
        raise ValueError(f"{name}: DataFrame is None — cannot proceed")

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name}: Expected DataFrame, got {type(df).__name__}")

    if df.empty:
        raise ValueError(f"{name}: DataFrame is empty — no data to process")

    if len(df) < min_rows:
        raise InsufficientDataError(required=min_rows, actual=len(df), indicator=name)

    if required_columns:
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"{name}: Missing required columns: {missing}")

    return df


def validate_price_dataframe(
    df: Optional[pd.DataFrame],
    symbol: str = "UNKNOWN",
    min_rows: int = 2,
) -> pd.DataFrame:
    """Validate a price DataFrame with common OHLCV columns.

    Replaces inf with NaN and ensures a DatetimeIndex.
    """
    df = validate_dataframe(df, min_rows=min_rows, name=f"price({symbol})")
    df = df.copy()
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception as exc:
            raise ValueError(f"Cannot convert index to datetime for {symbol}: {exc}")
    return df


def sanitize_numeric_column(
    series: pd.Series,
    name: str = "value",
    clip_low: Optional[float] = None,
    clip_high: Optional[float] = None,
    fill_method: str = "ffill",
) -> pd.Series:
    """Sanitize a numeric Series: replace inf, handle NaN, clip extremes."""
    if series is None or len(series) == 0:
        return pd.Series([], dtype=float)

    s = series.copy()
    s = s.replace([np.inf, -np.inf], np.nan)

    if fill_method == "ffill":
        s = s.ffill()
    elif fill_method == "bfill":
        s = s.bfill()
    elif fill_method == "zero":
        s = s.fillna(0.0)
    elif fill_method == "drop":
        s = s.dropna()

    if clip_low is not None or clip_high is not None:
        s = s.clip(lower=clip_low, upper=clip_high)

    return s


# ── Return Series Validation ─────────────────────────────────────────

def validate_returns(
    returns: Optional[Union[pd.Series, np.ndarray, List[float]]],
    name: str = "returns",
    min_length: int = 2,
) -> pd.Series:
    """Validate and sanitize a return series.

    - Replaces inf with NaN
    - Drops NaN
    - Clips extreme values beyond 10 standard deviations

    Raises:
        ValueError: If insufficient data after sanitization.
    """
    if returns is None:
        raise ValueError(f"{name}: returns is None")

    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    elif isinstance(returns, list):
        returns = pd.Series(returns)

    if not isinstance(returns, pd.Series):
        raise TypeError(f"{name}: Expected Series, got {type(returns).__name__}")

    if len(returns) == 0:
        raise ValueError(f"{name}: Empty return series")

    cleaned = returns.replace([np.inf, -np.inf], np.nan).dropna()

    if len(cleaned) < min_length:
        raise InsufficientDataError(
            required=min_length, actual=len(cleaned), indicator=name
        )

    std = cleaned.std()
    if std > 0:
        cleaned = cleaned.clip(-10 * std, 10 * std)

    return cleaned


# ── Financial Data Validators ─────────────────────────────────────────

def safe_price(price: Optional[float], symbol: str = "UNKNOWN") -> Optional[float]:
    """Validate a single price value.

    Returns None if price is invalid.
    """
    if price is None:
        return None
    try:
        p = float(price)
        if math.isnan(p) or math.isinf(p):
            return None
        if p < 0:
            return None
        if p > MAX_PRICE:
            return None
        return p
    except (TypeError, ValueError):
        return None


def safe_volume(volume: Optional[float]) -> Optional[float]:
    """Validate a volume value. Returns None if invalid."""
    if volume is None:
        return None
    try:
        v = float(volume)
        if math.isnan(v) or math.isinf(v):
            return None
        if v < MIN_VOLUME:
            return None
        return v
    except (TypeError, ValueError):
        return None


def safe_kelly_fraction(f: Optional[float]) -> float:
    """Validate and clamp a Kelly fraction to [0.0, 1.0]."""
    if f is None:
        return 0.0
    try:
        val = float(f)
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return max(0.0, min(1.0, val))
    except (TypeError, ValueError):
        return 0.0


def validate_weights(
    weights: Optional[Dict[str, float]],
    name: str = "weights",
) -> Dict[str, float]:
    """Validate and normalize a weights dictionary.

    Normalizes weights to sum to 1.0. Raises on empty or all-zero.
    """
    if not weights:
        raise ValueError(f"{name}: Empty weights dict")

    cleaned = {}
    for k, v in weights.items():
        try:
            val = float(v)
            if not (math.isnan(val) or math.isinf(val)):
                cleaned[k] = val
        except (TypeError, ValueError):
            continue

    if not cleaned:
        raise ValueError(f"{name}: No valid weights after sanitization")

    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError(f"{name}: Sum of weights must be positive, got {total}")

    return {k: v / total for k, v in cleaned.items()}


def validate_trade_history(
    history: Optional[List[float]],
    min_trades: int = 10,
    name: str = "trade_history",
) -> List[float]:
    """Validate a trade history list for Kelly calculations."""
    if history is None:
        raise ValueError(f"{name}: None — cannot compute Kelly without trade history")

    if len(history) < min_trades:
        raise InsufficientDataError(
            required=min_trades, actual=len(history), indicator=name
        )

    if len(history) > MAX_TRADE_HISTORY:
        logger.warning(
            f"{name}: Truncating trade history from {len(history)} to {MAX_TRADE_HISTORY}"
        )
        history = history[-MAX_TRADE_HISTORY:]

    cleaned = []
    for t in history:
        try:
            val = float(t)
            if not (math.isnan(val) or math.isinf(val)):
                cleaned.append(val)
        except (TypeError, ValueError):
            continue

    if len(cleaned) < min_trades:
        raise InsufficientDataError(
            required=min_trades, actual=len(cleaned), indicator=name
        )

    return cleaned


# ── Overflow Protection ───────────────────────────────────────────────

def safe_cumprod(returns: pd.Series) -> pd.Series:
    """Compute cumulative product with overflow protection."""
    if returns is None or len(returns) == 0:
        return pd.Series([], dtype=float)

    safe_rets = returns.clip(-MAX_ABS_RETURN, MAX_ABS_RETURN)
    result = (1 + safe_rets).cumprod()
    result = result.replace([np.inf, -np.inf], np.nan)
    return result


def safe_sum(values: Union[List[float], pd.Series], default: float = 0.0) -> float:
    """Safe summation with overflow protection."""
    if values is None or len(values) == 0:
        return default
    try:
        arr = np.array(values, dtype=np.float64)
        arr = np.where(np.isinf(arr) | np.isnan(arr), 0.0, arr)
        result = float(np.sum(arr))
        if math.isinf(result) or math.isnan(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


# ── Defensive Wrapper Decorator ───────────────────────────────────────

def defensive_wrapper(
    fallback_value: Any = None,
    log_errors: bool = True,
    reraise: bool = False,
    max_retries: int = 0,
    retry_delay: float = 0.1,
) -> Callable:
    """Decorator that wraps a function with defensive error handling.

    Catches exceptions and returns a fallback value instead of crashing.

    Args:
        fallback_value: Value to return on exception.
        log_errors: Whether to log the exception.
        reraise: If True, re-raise after logging.
        max_retries: Number of retries on transient failures.
        retry_delay: Base delay between retries in seconds.

    Example::

        @defensive_wrapper(fallback_value=0.0)
        def compute_sharpe(returns):
            return returns.mean() / returns.std()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if result is None and fallback_value is not None:
                        return fallback_value
                    return result
                except (InsufficientDataError, ValueError) as exc:
                    last_exception = exc
                    if log_errors:
                        logger.warning(
                            f"[{func.__name__}] Attempt {attempt + 1} failed: {exc}"
                        )
                    if attempt < max_retries:
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                except Exception as exc:
                    last_exception = exc
                    if log_errors:
                        logger.error(
                            f"[{func.__name__}] Unexpected error: {exc}\n"
                            f"{traceback.format_exc()}"
                        )
                    break

            if reraise and last_exception is not None:
                raise last_exception

            return fallback_value

        wrapper._original_func = func  # type: ignore[attr-defined]
        return wrapper
    return decorator


def defensive_dataframe_op(
    func: Callable,
    df: pd.DataFrame,
    fallback: Optional[pd.DataFrame] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Execute a DataFrame operation with defensive fallback.

    Returns fallback (empty DataFrame by default) on any error.
    """
    try:
        result = func(df, **kwargs)
        if result is None:
            return fallback if fallback is not None else pd.DataFrame()
        return result
    except Exception as exc:
        logger.error(f"[{func.__name__}] DataFrame operation failed: {exc}")
        return fallback if fallback is not None else pd.DataFrame()


# ── Module Boundary Validators ────────────────────────────────────────

def validate_market_data_input(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    operation: str = "backtest",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate paired market data + signals inputs at module boundaries.

    Args:
        prices: Price DataFrame.
        signals: Signal DataFrame.
        operation: Operation name for error messages.

    Returns:
        Tuple of (validated_prices, validated_signals).

    Raises:
        ValueError: If inputs are invalid.
    """
    if prices is None or prices.empty:
        raise ValueError(f"{operation}: prices DataFrame is empty or None")

    if signals is None or signals.empty:
        raise ValueError(f"{operation}: signals DataFrame is empty or None")

    if len(prices) != len(signals):
        raise ValueError(
            f"{operation}: Length mismatch — prices={len(prices)}, signals={len(signals)}"
        )

    if not prices.index.equals(signals.index):
        logger.warning(
            f"{operation}: Index mismatch — aligning signals to prices index"
        )
        signals = signals.reindex(prices.index).fillna(0.0)

    return prices, signals


def validate_position_size(
    size: float,
    equity: float,
    max_fraction: float = 0.02,
    name: str = "position",
) -> float:
    """Validate and cap position size relative to equity."""
    if math.isnan(size) or math.isinf(size):
        return 0.0

    if equity <= 0:
        return 0.0

    notional = abs(size)
    max_notional = equity * max_fraction

    if notional > max_notional:
        capped = max_notional / (abs(size) / size if size != 0 else 1.0)
        logger.warning(
            f"{name}: Position size {size} capped to {capped} "
            f"(max_fraction={max_fraction})"
        )
        return capped

    return size
