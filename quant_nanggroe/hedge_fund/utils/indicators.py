"""Technical analysis indicators.

Provides DataFrame-based calculations that work without MT5,
plus MT5-specific helpers when available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.hedge_fund.utils.config import MT5_AVAILABLE, mt5


def calc_atr(df: pd.DataFrame | str = None, period: int = 14, tf: int = 1, symbol: str = "EURUSD") -> float | None:
    """Calculate Average True Range.

    Args:
        df: OHLCV DataFrame with 'high', 'low', 'close' columns, OR symbol string for MT5.
        period: ATR period (default: 14).
        tf: MT5 timeframe (only used if df is a symbol string).
        symbol: MT5 symbol (only used if df is a symbol string).

    Returns:
        ATR value or None if insufficient data.
    """
    # DataFrame-based calculation (preferred)
    if isinstance(df, pd.DataFrame):
        if len(df) < period + 1:
            return None
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        trs = []
        for i in range(1, len(high)):
            tr = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
            trs.append(tr)
        if len(trs) < period:
            return None
        return float(np.mean(trs[-period:]))

    # MT5 fallback (legacy interface)
    if not MT5_AVAILABLE:
        return None
    sym = df if isinstance(df, str) else symbol
    r = mt5.copy_rates_from_pos(sym, tf, 0, period + 2)
    if r is None or len(r) < period + 1:
        return None
    trs = []
    for i in range(-period, 0):
        h, lo, pc = r[i][2], r[i][3], r[i - 1][4]
        trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    return sum(trs) / len(trs)


def calc_rsi(df: pd.DataFrame, period: int = 14) -> float | None:
    """Calculate Relative Strength Index.

    Args:
        df: DataFrame with 'close' column.
        period: RSI period (default: 14).

    Returns:
        RSI value (0-100) or None if insufficient data.
    """
    if "close" not in df.columns or len(df) < period + 1:
        return None
    closes = df["close"].values
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def calc_sma(df: pd.DataFrame, period: int = 20, column: str = "close") -> float | None:
    """Calculate Simple Moving Average.

    Args:
        df: DataFrame with price column.
        period: SMA period (default: 20).
        column: Column name to use (default: 'close').

    Returns:
        SMA value or None if insufficient data.
    """
    if column not in df.columns or len(df) < period:
        return None
    return float(df[column].iloc[-period:].mean())


def calc_ema(df: pd.DataFrame, period: int = 20, column: str = "close") -> float | None:
    """Calculate Exponential Moving Average.

    Args:
        df: DataFrame with price column.
        period: EMA period (default: 20).
        column: Column name to use (default: 'close').

    Returns:
        EMA value or None if insufficient data.
    """
    if column not in df.columns or len(df) < period:
        return None
    return float(df[column].ewm(span=period, adjust=False).mean().iloc[-1])


def calc_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> dict | None:
    """Calculate Bollinger Bands.

    Args:
        df: DataFrame with 'close' column.
        period: SMA period (default: 20).
        std_dev: Standard deviation multiplier (default: 2.0).

    Returns:
        Dict with 'upper', 'middle', 'lower' bands, or None if insufficient data.
    """
    if "close" not in df.columns or len(df) < period:
        return None
    closes = df["close"].iloc[-period:]
    middle = float(closes.mean())
    std = float(closes.std())
    return {
        "upper": middle + std_dev * std,
        "middle": middle,
        "lower": middle - std_dev * std,
    }
