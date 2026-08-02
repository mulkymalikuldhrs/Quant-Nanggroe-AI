"""MACD histogram factor (QS013 research distilled from quant-research-kb).

Research basis (QuantScience newsletter QS013):
- 12-26-9 MACD histogram: mean rolling-30d correlation vs forward 5d
  returns ≈ **-0.237** (mean-reverting signal, sign-flip for long bias).
- PPO (normalized MACD): stronger, ≈ **-0.40**.
- 50-200-63 MACD magnitude: ≈ **-0.37**.
- Signal is strongest when combined with ATR-normalized trend filters
  and used as a *mean-reversion* overlay, not a trend-following entry.

Design (ponytail):
- Pure pandas/numpy, no TA-Lib dependency.
- Lazy-import heavy deps; module importable without polars/ffn.
- Column names follow QNA convention: lowercase, snake_case.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_macd_histogram(
    ohlcv: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Compute classic MACD line / signal / histogram columns.

    Args:
        ohlcv: DataFrame with a 'close' column.
        fast/slow/signal: EMA periods (default 12-26-9).

    Returns:
        Copy of ohlcv augmented with:
        - macd_line: EMA(fast) - EMA(slow)
        - signal_line: EMA(signal) of macd_line
        - macd_histogram: macd_line - signal_line
    """
    df = ohlcv.copy()
    close = df["close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    df["macd_line"] = macd_line
    df["signal_line"] = signal_line
    df["macd_histogram"] = macd_line - signal_line
    return df


def compute_ppo(
    ohlcv: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Percentage Price Oscillator: normalized MACD (QS013: corr ≈ -0.40).

    PPO = (EMA_fast - EMA_slow) / EMA_slow * 100
    """
    df = ohlcv.copy()
    close = df["close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    ppo = (ema_fast - ema_slow) / ema_slow * 100.0
    signal_line = ppo.ewm(span=signal, adjust=False).mean()
    df["ppo"] = ppo
    df["ppo_signal"] = signal_line
    df["ppo_histogram"] = ppo - signal_line
    return df


def rolling_corr_forward_returns(
    signal: pd.Series,
    close: pd.Series,
    window: int = 30,
    forward: int = 5,
) -> pd.Series:
    """Rolling correlation between signal (t) and forward returns (t+fwd).

    Mirrors QS013 methodology: corr(signal_t, ret_{t+5}) over a 30-day
    window. Mean ≈ -0.237 for 12-26-9 MACD histogram on equities.
    """
    fwd_returns = close.pct_change(periods=forward).shift(-forward)
    return signal.rolling(window).corr(fwd_returns)
