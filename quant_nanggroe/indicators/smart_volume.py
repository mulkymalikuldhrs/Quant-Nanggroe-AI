"""DhaHer Smart Volume — Python port of the TradingView Pine Script.

Logic:
  volAvg   = SMA(volume, 20)
  volRatio = volume / volAvg
  spikeUp  = volRatio > vol_mult and close > open
  spikeDn  = volRatio > vol_mult and close < open
  validUp  = spikeUp and rsi < 70   (not overbought)
  validDn  = spikeDn and rsi > 30   (not oversold)

Confirmation indicator: returns 'BUY'/'SELL'/'HOLD' on the last bar's
smart-volume signal. Use as ensemble enrichment (boost conviction on volume).

Ported from D:/tv-indicators/dhaher-smart-volume.pine (v5).
ponytail: single combined filter. No dashboard.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def smart_volume_signal(
    df: pd.DataFrame,
    vol_mult: float = 2.0,
    rsi_len: int = 14,
) -> pd.DataFrame:
    close = df["close"].astype(float)
    volume = (
        df["volume"].astype(float)
        if "volume" in df
        else df.get("tick_volume", pd.Series(0, index=df.index)).astype(float)
    )
    open_ = df["open"].astype(float) if "open" in df else close.shift(1)

    vol_avg = volume.rolling(20).mean()
    vol_ratio = volume / vol_avg
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(rsi_len).mean()
    loss = (-delta.clip(upper=0)).rolling(rsi_len).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).fillna(50)

    spike_up = vol_ratio > vol_mult
    spike_dn = vol_ratio > vol_mult
    valid_up = spike_up & (close > open_) & (rsi < 70)
    valid_dn = spike_dn & (close < open_) & (rsi > 30)

    out = df.copy()
    out["vol_ratio"] = vol_ratio
    out["rsi14"] = rsi
    out["sv_valid_up"] = valid_up.fillna(False)
    out["sv_valid_dn"] = valid_dn.fillna(False)
    return out


def latest_signal(df: pd.DataFrame) -> str:
    if len(df) == 0:
        return "HOLD"
    last = df.iloc[-1]
    if bool(last.get("sv_valid_up", False)):
        return "BUY"
    if bool(last.get("sv_valid_dn", False)):
        return "SELL"
    return "HOLD"
