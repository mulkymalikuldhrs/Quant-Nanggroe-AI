"""Enhanced Regime Detection — composite of HMM + GARCH vol + ADX trend.

Produces a single regime label (bull_trend/bear_trend/ranging/crisis)
from multiple independent signals, each scored 0-1 and combined.

Replaces the old single-indicator approach (just ADX or just HMM) with
a robust ensemble that's harder to fool.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("QNA.Regime")


@dataclass(frozen=True)
class RegimeResult:
    regime: str            # "bull_trend" | "bear_trend" | "ranging" | "crisis"
    confidence: float      # 0-1
    scores: Dict[str, float]  # individual component scores


def _adx(highs: np.ndarray, lows: np.ndarray,
         closes: np.ndarray, period: int = 14) -> float:
    """Average Directional Index — measures TREND STRENGTH (not direction).
    Returns 0-100. >25 = strong trend, <20 = ranging."""
    n = len(closes)
    if n < period * 2:
        return 0.0

    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        h_diff = highs[i] - highs[i - 1]
        l_diff = lows[i - 1] - lows[i]
        tr[i] = max(highs[i] - lows[i], abs(h_diff), abs(l_diff))
        if h_diff > l_diff and h_diff > 0:
            plus_dm[i] = h_diff
        elif l_diff > h_diff and l_diff > 0:
            minus_dm[i] = l_diff

    # Smooth with EMA
    alpha = 1.0 / period
    atr = np.zeros(n)
    pdm_s = np.zeros(n)
    mdm_s = np.zeros(n)
    for i in range(1, n):
        atr[i] = atr[i-1] + alpha * (tr[i] - atr[i-1])
        pdm_s[i] = pdm_s[i-1] + alpha * (plus_dm[i] - pdm_s[i-1])
        mdm_s[i] = mdm_s[i-1] + alpha * (minus_dm[i] - mdm_s[i-1])

    # Avoid division by zero
    safe_atr = np.where(atr > 0, atr, 1e-10)
    plus_di = 100 * pdm_s / safe_atr
    minus_di = 100 * mdm_s / safe_atr

    dx_sum = plus_di + minus_di
    safe_dx = np.where(dx_sum > 0, dx_sum, 1e-10)
    dx = 100 * np.abs(plus_di - minus_di) / safe_dx

    # ADX = smoothed DX
    adx_arr = np.zeros(n)
    for i in range(period, n):
        adx_arr[i] = adx_arr[i-1] + alpha * (dx[i] - adx_arr[i-1])

    return float(np.clip(adx_arr[-1], 0, 100))


def _garch_vol_regime(closes: np.ndarray) -> float:
    """Simplified GARCH-style rolling volatility score.
    Returns normalized volatility percentile (0=calm, 1=extreme)."""
    rets = np.diff(np.log(np.maximum(closes, 1e-10)))
    if len(rets) < 20:
        return 0.5

    # Rolling std over last 20 bars vs longer baseline
    short_vol = np.std(rets[-20:])
    long_vol = np.std(rets[-min(len(rets), 100):])
    ratio = short_vol / max(long_vol, 1e-10)

    # Map ratio to 0-1: ratio<0.8=calm, ratio>1.5=extreme
    return float(np.clip((ratio - 0.8) / 0.7, 0, 1))


def _hmm_trend_score(closes: np.ndarray) -> float:
    """Simple momentum-based trend score (proxy for HMM state).
    Returns -1 to 1 where positive=bullish momentum."""
    if len(closes) < 50:
        return 0.0
    fast_ma = np.mean(closes[-10:])
    slow_ma = np.mean(closes[-50:])
    denom = max(abs(slow_ma), 1e-10)
    return float(np.clip((fast_ma - slow_ma) / denom * 10, -1, 1))


def detect_enhanced_regime(
    df: pd.DataFrame,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
) -> RegimeResult:
    """Composite regime detection from OHLCV data.

    Logic:
        1. ADX > threshold → trending; else → ranging
        2. HMM trend score sign → bull or bear
        3. GARCH vol score > 0.7 → crisis override
        4. Composite confidence from component agreement

    Args:
        df: OHLCV DataFrame.
        adx_period: ADX calculation period.
        adx_threshold: minimum ADX for "trending" classification.

    Returns:
        RegimeResult with regime label, confidence, and component scores.
    """
    required = {"high", "low", "close"}
    cols = {c.lower() for c in df.columns}
    if not required.issubset(cols):
        return RegimeResult("ranging", 0.0, {"error": -1})

    df = df.rename(columns={c: c.lower() for c in df.columns})
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values

    if len(closes) < 50:
        return RegimeResult("ranging", 0.0, {"error": -2})

    # Component 1: Trend strength (ADX)
    adx_val = _adx(highs, lows, closes, adx_period)
    is_trending = adx_val > adx_threshold
    trend_strength_score = min(adx_val / 50.0, 1.0)

    # Component 2: Direction (momentum proxy for HMM)
    hmm_score = _hmm_trend_score(closes)
    direction_bullish = hmm_score > 0.05
    direction_bearish = hmm_score < -0.05

    # Component 3: Volatility regime
    vol_score = _garch_vol_regime(closes)
    is_crisis = vol_score > 0.75

    # Composite decision tree
    if is_crisis:
        regime = "crisis"
        confidence = min(vol_score, 1.0)
    elif is_trending and direction_bullish:
        regime = "bull_trend"
        confidence = min(trend_strength_score * abs(hmm_score) + 0.3, 1.0)
    elif is_trending and direction_bearish:
        regime = "bear_trend"
        confidence = min(trend_strength_score * abs(hmm_score) + 0.3, 1.0)
    else:
        regime = "ranging"
        confidence = round(1.0 - trend_strength_score * 0.5, 4)

    scores = {
        "adx": round(adx_val, 2),
        "trend_strength": round(trend_strength_score, 4),
        "hmm_direction": round(hmm_score, 4),
        "volatility": round(vol_score, 4),
        "is_trending": int(is_trending),
        "is_crisis": int(is_crisis),
    }

    logger.debug("Regime: %s conf=%.2f scores=%s", regime, confidence, scores)
    return RegimeResult(regime=regime, confidence=round(confidence, 4), scores=scores)
