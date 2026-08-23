"""QNA Native Smart Money Concepts Engine.

Implements institutional-grade SMC algorithms natively in numpy/pandas.
No external dependency on smart-money-concepts package.

Algorithms:
    - Swing High/Low detection (fractal-based, configurable strength)
    - Fair Value Gap (FVG) — 3-candle imbalance pattern
    - Break of Structure (BOS) / Change of Character (CHoCH)
    - Order Block (OB) — last opposite candle before impulsive break
    - Liquidity Sweep — wick beyond swing then close back inside

All functions are pure (no side effects), vectorized where possible,
and return typed DataFrames suitable for downstream strategy consumption.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("QNA.SMC")


# ── Swing High/Low ──────────────────────────────────────────────────

def swing_highs_lows(
    df: pd.DataFrame,
    swing_length: int = 10,
) -> pd.DataFrame:
    """Detect swing highs and lows using fractal window approach.

    A swing high is a bar whose high is greater than the highs of
    ``swing_length`` bars on BOTH sides. Mirror logic for swing low.

    Returns DataFrame with columns:
        high_swing: bool — True at swing high bars
        low_swing: bool — True at swing low bars
        swing_high_price: float or NaN
        swing_low_price: float or NaN
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(highs)

    high_swing = np.zeros(n, dtype=bool)
    low_swing = np.zeros(n, dtype=bool)
    sh_prices = np.full(n, np.nan)
    sl_prices = np.full(n, np.nan)

    for i in range(swing_length, n - swing_length):
        # swing high: high[i] > all highs in [i-len, i+len] excluding i
        left_h = highs[i - swing_length:i]
        right_h = highs[i + 1:i + swing_length + 1]
        if highs[i] > left_h.max() and highs[i] > right_h.max():
            high_swing[i] = True
            sh_prices[i] = highs[i]

        # swing low: low[i] < all lows in window excluding i
        left_l = lows[i - swing_length:i]
        right_l = lows[i + 1:i + swing_length + 1]
        if lows[i] < left_l.min() and lows[i] < right_l.min():
            low_swing[i] = True
            sl_prices[i] = lows[i]

    result = df[[]].copy()
    result["high_swing"] = high_swing
    result["low_swing"] = low_swing
    result["swing_high_price"] = sh_prices
    result["swing_low_price"] = sl_prices
    return result


# ── Fair Value Gap (FVG) ────────────────────────────────────────────

def fair_value_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Detect 3-candle Fair Value Gap imbalances.

    Bullish FVG: low of current candle > high of candle 2 periods ago
                 (gap between candles means price moved too fast)
    Bearish FVG: high of current candle < low of candle 2 periods ago

    Returns DataFrame with columns:
        fvg_bullish: bool
        fvg_bearish: bool
        fvg_top: float — top of the gap zone
        fvg_bottom: float — bottom of the gap zone
    """
    lows = df["low"].values
    highs = df["high"].values
    n = len(df)

    bull_fvg = np.zeros(n, dtype=bool)
    bear_fvg = np.zeros(n, dtype=bool)
    fvg_top = np.full(n, np.nan)
    fvg_bottom = np.full(n, np.nan)

    for i in range(2, n):
        # Bullish FVG: current low > high from 2 candles ago
        if lows[i] > highs[i - 2]:
            bull_fvg[i] = True
            fvg_top[i] = lows[i]
            fvg_bottom[i] = highs[i - 2]

        # Bearish FVG: current high < low from 2 candles ago
        elif highs[i] < lows[i - 2]:
            bear_fvg[i] = True
            fvg_top[i] = lows[i - 2]
            fvg_bottom[i] = highs[i]

    result = df[[]].copy()
    result["fvg_bullish"] = bull_fvg
    result["fvg_bearish"] = bear_fvg
    result["fvg_top"] = fvg_top
    result["fvg_bottom"] = fvg_bottom
    return result


# ── BOS / CHoCH ─────────────────────────────────────────────────────

def bos_choch(df: pd.DataFrame, swing_length: int = 10) -> pd.DataFrame:
    """Detect Break of Structure and Change of Character.

    BOS: close breaks the PREVIOUS swing high (bullish continuation)
         or previous swing low (bearish continuation).
    CHoCH: first BOS in the OPPOSITE direction of the prevailing trend.

    Returns DataFrame with columns:
        bos_bullish: bool
        bos_bearish: bool
        choch_bullish: bool
        choch_bearish: bool
    """
    sw = swing_highs_lows(df, swing_length)
    closes = df["close"].values
    n = len(closes)

    bos_bull = np.zeros(n, dtype=bool)
    bos_bear = np.zeros(n, dtype=bool)
    choch_bull = np.zeros(n, dtype=bool)
    choch_bear = np.zeros(n, dtype=bool)

    # Track most recent confirmed swing levels
    last_sh = np.nan
    last_sl = np.nan
    trend = 0  # 1=bullish, -1=bearish, 0=undefined

    for i in range(n):
        # Update swing levels when new swings confirm
        idx = i - swing_length  # swings confirm after swing_length bars
        if idx >= 0 and sw["high_swing"].iloc[idx]:
            last_sh = sw["swing_high_price"].iloc[idx]
        if idx >= 0 and sw["low_swing"].iloc[idx]:
            last_sl = sw["swing_low_price"].iloc[idx]

        # Check BOS
        if not np.isnan(last_sh) and closes[i] > last_sh:
            if trend <= 0:
                choch_bull[i] = True
                trend = 1
            else:
                bos_bull[i] = True
            last_sh = np.nan  # consumed

        if not np.isnan(last_sl) and closes[i] < last_sl:
            if trend >= 0:
                choch_bear[i] = True
                trend = -1
            else:
                bos_bear[i] = True
            last_sl = np.nan  # consumed

    result = df[[]].copy()
    result["bos_bullish"] = bos_bull
    result["bos_bearish"] = bos_bear
    result["choch_bullish"] = choch_bull
    result["choch_bearish"] = choch_bear
    return result


# ── Order Block Detection ───────────────────────────────────────────

def order_blocks(
    df: pd.DataFrame,
    swing_length: int = 10,
    lookback: int = 5,
) -> pd.DataFrame:
    """Detect Order Blocks — last opposite candle before an impulsive move.

    Bullish OB: last bearish candle before a bullish BOS
    Bearish OB: last bullish candle before a bearish BOS

    Returns DataFrame with columns:
        ob_bullish: bool — bullish order block detected at this bar
        ob_bearish: bool — bearish order block
        ob_bull_top/bottom: price zone of the block
        ob_bear_top/bottom: price zone
    """
    bos = bos_choch(df, swing_length)
    opens = df["open"].values
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    ob_bull = np.zeros(n, dtype=bool)
    ob_bear = np.zeros(n, dtype=bool)
    ob_bull_top = np.full(n, np.nan)
    ob_bull_bot = np.full(n, np.nan)
    ob_bear_top = np.full(n, np.nan)
    ob_bear_bot = np.full(n, np.nan)

    for i in range(lookback, n):
        # Bullish OB: find last bearish candle before a bullish BOS
        if bos.loc[bos.index[i], "bos_bullish"] or bos.loc[bos.index[i], "choch_bullish"]:
            for j in range(i - 1, max(i - lookback - 1, -1), -1):
                if closes[j] < opens[j]:  # bearish candle
                    ob_bull[j] = True
                    ob_bull_top[j] = highs[j]
                    ob_bull_bot[j] = lows[j]
                    break

        # Bearish OB: find last bullish candle before a bearish BOS
        if bos.loc[bos.index[i], "bos_bearish"] or bos.loc[bos.index[i], "choch_bearish"]:
            for j in range(i - 1, max(i - lookback - 1, -1), -1):
                if closes[j] > opens[j]:  # bullish candle
                    ob_bear[j] = True
                    ob_bear_top[j] = highs[j]
                    ob_bear_bot[j] = lows[j]
                    break

    result = df[[]].copy()
    result["ob_bullish"] = ob_bull
    result["ob_bearish"] = ob_bear
    result["ob_bull_top"] = ob_bull_top
    result["ob_bull_bottom"] = ob_bull_bot
    result["ob_bear_top"] = ob_bear_top
    result["ob_bear_bottom"] = ob_bear_bot
    return result


# ── Liquidity Sweep ─────────────────────────────────────────────────

def liquidity_sweep(
    df: pd.DataFrame,
    swing_length: int = 10,
) -> pd.DataFrame:
    """Detect liquidity sweeps — wick beyond swing then close back inside.

    Bullish sweep: low wicks BELOW previous swing low but close stays above.
                   (Smart money grabbing sell-side liquidity before reversal up.)
    Bearish sweep: high wicks ABOVE previous swing high but close stays below.

    Returns DataFrame with columns:
        sweep_bullish: bool — bullish liquidity sweep
        sweep_bearish: bool — bearish liquidity sweep
    """
    sw = swing_highs_lows(df, swing_length)
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    n = len(closes)

    sweep_bull = np.zeros(n, dtype=bool)
    sweep_bear = np.zeros(n, dtype=bool)

    last_sh = np.nan
    last_sl = np.nan

    for i in range(n):
        idx = i - swing_length
        if idx >= 0 and sw["high_swing"].iloc[idx]:
            last_sh = sw["swing_high_price"].iloc[idx]
        if idx >= 0 and sw["low_swing"].iloc[idx]:
            last_sl = sw["swing_low_price"].iloc[idx]

        # Bullish sweep: low goes below swing low but close is above it
        if not np.isnan(last_sl):
            if lows[i] < last_sl and closes[i] > last_sl:
                sweep_bull[i] = True
                last_sl = np.nan  # consumed

        # Bearish sweep: high goes above swing high but close is below it
        if not np.isnan(last_sh):
            if highs[i] > last_sh and closes[i] < last_sh:
                sweep_bear[i] = True
                last_sh = np.nan  # consumed

    result = df[[]].copy()
    result["sweep_bullish"] = sweep_bull
    result["sweep_bearish"] = sweep_bear
    return result


# ── Composite Analyzer ──────────────────────────────────────────────

class SMCEngine:
    """High-level facade — runs all SMC analyses and produces a composite signal."""

    def __init__(self, swing_length: int = 10, ob_lookback: int = 5):
        self.swing_length = swing_length
        self.ob_lookback = ob_lookback

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run full SMC analysis and return structured results."""
        required = {"open", "high", "low", "close"}
        if not required.issubset(set(c.lower() for c in df.columns)):
            return {"error": f"missing columns: {required - set(c.lower() for c in df.columns)}"}

        df = df.rename(columns={c: c.lower() for c in df.columns})
        sw = swing_highs_lows(df, self.swing_length)
        fvg = fair_value_gaps(df)
        bc = bos_choch(df, self.swing_length)
        ob = order_blocks(df, self.swing_length, self.ob_lookback)
        liq = liquidity_sweep(df, self.swing_length)

        # Recent signals (last bar)
        last = {
            "bullish_ob": bool(ob["ob_bullish"].iloc[-1]) if len(ob) else False,
            "bearish_ob": bool(ob["ob_bearish"].iloc[-1]) if len(ob) else False,
            "bullish_fvg": bool(fvg["fvg_bullish"].iloc[-1]) if len(fvg) else False,
            "bearish_fvg": bool(fvg["fvg_bearish"].iloc[-1]) if len(fvg) else False,
            "bos_bullish": bool(bc["bos_bullish"].iloc[-1]),
            "bos_bearish": bool(bc["bos_bearish"].iloc[-1]),
            "choch_bullish": bool(bc["choch_bullish"].iloc[-1]),
            "choch_bearish": bool(bc["choch_bearish"].iloc[-1]),
            "sweep_bullish": bool(liq["sweep_bullish"].iloc[-1]),
            "sweep_bearish": bool(liq["sweep_bearish"].iloc[-1]),
        }

        # Composite score
        bull_count = sum(last[k] for k in last if "bullish" in k or "bull" in k)
        bear_count = sum(last[k] for k in last if "bearish" in k or "bear" in k)

        if bull_count >= 2 and bull_count > bear_count:
            direction = "buy"
            confidence = min(0.85, 0.4 + bull_count * 0.12)
        elif bear_count >= 2 and bear_count > bull_count:
            direction = "sell"
            confidence = min(0.85, 0.4 + bear_count * 0.12)
        else:
            direction = "hold"
            confidence = 0.30

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "signals": last,
            "bull_score": bull_count,
            "bear_score": bear_count,
            "n_swing_highs": int(sw["high_swing"].sum()),
            "n_swing_lows": int(sw["low_swing"].sum()),
            "n_fvg_bullish": int(fvg["fvg_bullish"].sum()),
            "n_fvg_bearish": int(fvg["fvg_bearish"].sum()),
        }
