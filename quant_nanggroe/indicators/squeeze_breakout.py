"""DhaHer Squeeze Breakout — Python port of the TradingView Pine Script.

TTM Squeeze logic:
  - Bollinger width (upper-lower)/basis < sqzThresh  => market in "squeeze" (low vol)
  - Volume spike (volume > volAvg*volMult) + directional breakout => release signal
  - bullBreak: squeeze[1] & close > max(open, close[1]) & close > upper & volSpike
  - bearBreak: squeeze[1] & close < min(open, close[1]) & close < lower & volSpike

Ported from D:/tv-indicators/dhaher-squeeze-breakout.pine (v5) for use as a
QNA regime/volatility filter or ensemble enrichment signal.

ponytail: one combined signal, no dashboard, no UI. Pure function.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def squeeze_breakout(
    df: pd.DataFrame,
    len: int = 20,
    mult: float = 2.0,
    sqz_thresh: float = 0.04,
    vol_mult: float = 2.0,
    lookback: int = 3,
) -> pd.DataFrame:
    """Return df with squeeze/breakout columns.

    Adds: bb_upper, bb_lower, bb_basis, bb_width, sqz (bool),
          vol_avg, vol_spike, bull_break, bear_break.
    """
    close = df["close"].astype(float)
    volume = df["volume"].astype(float) if "volume" in df else df.get("tick_volume", pd.Series(0, index=df.index)).astype(float)

    basis = close.rolling(len).mean()
    dev = mult * close.rolling(len).std(ddof=0)
    upper = basis + dev
    lower = basis - dev
    bb_width = (upper - lower) / basis
    sqz = bb_width < sqz_thresh

    vol_avg = volume.rolling(20).mean()
    vol_spike = volume > vol_avg * vol_mult

    prev_close = close.shift(1)
    prev_open = df["open"].astype(float).shift(1) if "open" in df else prev_close
    max_oc = np.maximum(df["open"].astype(float), prev_close)
    min_oc = np.minimum(df["open"].astype(float), prev_close)

    sqz_prev = sqz.shift(1).fillna(False)
    bull_break = sqz_prev & (close > max_oc) & (close > upper) & vol_spike
    bear_break = sqz_prev & (close < min_oc) & (close < lower) & vol_spike

    out = df.copy()
    out["bb_upper"] = upper
    out["bb_lower"] = lower
    out["bb_basis"] = basis
    out["bb_width"] = bb_width
    out["sqz"] = sqz.fillna(False)
    out["vol_avg"] = vol_avg
    out["vol_spike"] = vol_spike.fillna(False)
    out["bull_break"] = bull_break.fillna(False)
    out["bear_break"] = bear_break.fillna(False)
    return out


def latest_signal(df: pd.DataFrame) -> str:
    """Return 'BUY', 'SELL', or 'HOLD' based on the last row's breakout state."""
    if len(df) == 0:
        return "HOLD"
    last = df.iloc[-1]
    if bool(last.get("bull_break", False)):
        return "BUY"
    if bool(last.get("bear_break", False)):
        return "SELL"
    return "HOLD"
