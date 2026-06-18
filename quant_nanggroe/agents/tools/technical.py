"""
Technical Analysis Tool — Full Indicator Suite for Agents
==========================================================
Wraps quant_nanggroe.utils.math calculations and augments the result with
Smart Money Concepts (SMC) signals, trend classification, computed
fields (EMA trend, trend strength, price changes, volume ratio),
and support/resistance level detection.

All calculations are 100% deterministic — no AI, no approximation.

LangChain @tool functions are also exposed for direct agent consumption.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, *args, **kwargs):
        """No-op fallback when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

from quant_nanggroe.exceptions import DataError, InsufficientDataError
from quant_nanggroe.agents.tools.market_data import MarketDataTool, _get_default_mdt

logger = logging.getLogger(__name__)

# Minimum bars needed for a meaningful full analysis
_MIN_BARS = 50


# ══════════════════════════════════════════════════════════════════════
# Deterministic Technical Indicator Calculations
# ══════════════════════════════════════════════════════════════════════

def _sma(data: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average."""
    if len(data) < period:
        return [None] * len(data)
    arr = np.array(data, dtype=float)
    result: List[Optional[float]] = [None] * (period - 1)
    for i in range(period - 1, len(arr)):
        result.append(round(float(np.mean(arr[i - period + 1:i + 1])), 6))
    return result


def _ema(data: List[float], period: int) -> List[Optional[float]]:
    """Exponential Moving Average."""
    if len(data) < period:
        return [None] * len(data)
    arr = np.array(data, dtype=float)
    result: List[Optional[float]] = [None] * (period - 1)
    # Seed with SMA
    seed = float(np.mean(arr[:period]))
    result.append(round(seed, 6))
    multiplier = 2.0 / (period + 1)
    ema_val = seed
    for i in range(period, len(arr)):
        ema_val = (arr[i] - ema_val) * multiplier + ema_val
        result.append(round(ema_val, 6))
    return result


def _rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    arr = np.array(closes, dtype=float)
    deltas = np.diff(arr)

    result: List[Optional[float]] = [None] * (period)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100.0 - (100.0 / (1.0 + rs)), 4))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100.0 - (100.0 / (1.0 + rs)), 4))

    return result


def _macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Dict[str, List[Optional[float]]]:
    """MACD indicator."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    macd_line: List[Optional[float]] = []
    for f, s in zip(ema_fast, ema_slow):
        if f is not None and s is not None:
            macd_line.append(round(f - s, 6))
        else:
            macd_line.append(None)

    # Signal line: EMA of MACD line
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal:
        signal_line: List[Optional[float]] = [None] * len(macd_line)
    else:
        signal_line = _ema(valid_macd, signal)
        # Pad front with None to align
        signal_line = [None] * (len(macd_line) - len(signal_line)) + signal_line

    histogram: List[Optional[float]] = []
    for m, s in zip(macd_line, signal_line):
        if m is not None and s is not None:
            histogram.append(round(m - s, 6))
        else:
            histogram.append(None)

    return {
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram,
    }


def _adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Dict[str, Any]:
    """Average Directional Index."""
    if len(closes) < period * 2 + 1:
        return {"adx": None, "plus_di": None, "minus_di": None}

    arr_h = np.array(highs, dtype=float)
    arr_l = np.array(lows, dtype=float)
    arr_c = np.array(closes, dtype=float)

    # True Range
    tr = np.maximum(
        arr_h[1:] - arr_l[1:],
        np.maximum(
            np.abs(arr_h[1:] - arr_c[:-1]),
            np.abs(arr_l[1:] - arr_c[:-1]),
        ),
    )

    # Directional Movement
    up_move = arr_h[1:] - arr_h[:-1]
    down_move = arr_l[:-1] - arr_l[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # Smooth with Wilder's method
    atr = np.zeros(len(tr))
    plus_di_arr = np.zeros(len(tr))
    minus_di_arr = np.zeros(len(tr))

    if len(tr) >= period:
        atr[period - 1] = np.sum(tr[:period])
        plus_di_arr[period - 1] = np.sum(plus_dm[:period])
        minus_di_arr[period - 1] = np.sum(minus_dm[:period])

        for i in range(period, len(tr)):
            atr[i] = atr[i - 1] - (atr[i - 1] / period) + tr[i]
            plus_di_arr[i] = plus_di_arr[i - 1] - (plus_di_arr[i - 1] / period) + plus_dm[i]
            minus_di_arr[i] = minus_di_arr[i - 1] - (minus_di_arr[i - 1] / period) + minus_dm[i]

        # DI values — suppress division warnings for zero ATR periods
        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di_vals = np.where(atr > 0, 100 * plus_di_arr / atr, 0.0)
            minus_di_vals = np.where(atr > 0, 100 * minus_di_arr / atr, 0.0)

            # DX and ADX
            dx = np.where(
                (plus_di_vals + minus_di_vals) > 0,
                100 * np.abs(plus_di_vals - minus_di_vals) / (plus_di_vals + minus_di_vals),
                0.0,
            )

        # ADX is smoothed DX
        adx_vals = np.zeros(len(dx))
        adx_start = period * 2 - 2
        if len(dx) > adx_start + period:
            adx_vals[adx_start + period - 1] = np.mean(dx[adx_start:adx_start + period])
            for i in range(adx_start + period, len(dx)):
                adx_vals[i] = (adx_vals[i - 1] * (period - 1) + dx[i]) / period

            last_idx = len(dx) - 1
            return {
                "adx": round(float(adx_vals[last_idx]), 4),
                "plus_di": round(float(plus_di_vals[last_idx]), 4),
                "minus_di": round(float(minus_di_vals[last_idx]), 4),
            }

    return {"adx": None, "plus_di": None, "minus_di": None}


def _bollinger_bands(
    closes: List[float],
    period: int = 20,
    num_std: float = 2.0,
) -> Dict[str, Any]:
    """Bollinger Bands."""
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None, "width": None, "percent_b": None}

    arr = np.array(closes, dtype=float)
    recent = arr[-period:]
    middle = float(np.mean(recent))
    std = float(np.std(recent, ddof=1))
    upper = middle + num_std * std
    lower = middle - num_std * std

    current = arr[-1]
    width = (upper - lower) / middle if middle > 0 else None
    percent_b = (current - lower) / (upper - lower) if (upper - lower) > 0 else None

    return {
        "upper": round(upper, 6),
        "middle": round(middle, 6),
        "lower": round(lower, 6),
        "width": round(width, 4) if width is not None else None,
        "percent_b": round(percent_b, 4) if percent_b is not None else None,
    }


def _stochastic(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    k_period: int = 14,
    d_period: int = 3,
) -> Dict[str, Any]:
    """Stochastic Oscillator."""
    if len(closes) < k_period:
        return {"k": None, "d": None}

    k_values: List[float] = []
    for i in range(k_period - 1, len(closes)):
        high_slice = highs[i - k_period + 1:i + 1]
        low_slice = lows[i - k_period + 1:i + 1]
        hh = max(high_slice)
        ll = min(low_slice)
        if hh == ll:
            k_values.append(50.0)
        else:
            k_values.append(((closes[i] - ll) / (hh - ll)) * 100)

    if len(k_values) >= d_period:
        d_value = sum(k_values[-d_period:]) / d_period
    else:
        d_value = k_values[-1] if k_values else None

    return {
        "k": round(k_values[-1], 4) if k_values else None,
        "d": round(d_value, 4) if d_value is not None else None,
    }


def _atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Optional[float]:
    """Average True Range."""
    if len(closes) < period + 1:
        return None

    tr_values = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_values.append(tr)

    if len(tr_values) < period:
        return None

    # Wilder's smoothing
    atr_val = sum(tr_values[:period]) / period
    for i in range(period, len(tr_values)):
        atr_val = (atr_val * (period - 1) + tr_values[i]) / period

    return round(atr_val, 6)


def _compute_all_indicators(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
) -> Dict[str, Any]:
    """Compute all technical indicators from OHLCV data."""
    n = len(closes)

    # SMAs
    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    sma_200 = _sma(closes, 200)

    # EMAs
    ema_9 = _ema(closes, 9)
    ema_20 = _ema(closes, 20)
    ema_50 = _ema(closes, 50)
    ema_200 = _ema(closes, 200)

    # RSI
    rsi_14 = _rsi(closes, 14)

    # MACD
    macd_result = _macd(closes)

    # ADX
    adx_result = _adx(highs, lows, closes)

    # Bollinger Bands
    bb = _bollinger_bands(closes)

    # Stochastic
    stoch = _stochastic(highs, lows, closes)

    # ATR
    atr_val = _atr(highs, lows, closes)

    # OBV
    obv = _obv(closes, volumes)

    # VWAP (simplified)
    vwap = _vwap(closes, volumes)

    return {
        "sma_20": sma_20[-1] if n >= 20 else None,
        "sma_50": sma_50[-1] if n >= 50 else None,
        "sma_200": sma_200[-1] if n >= 200 else None,
        "ema_9": ema_9[-1] if n >= 9 else None,
        "ema_20": ema_20[-1] if n >= 20 else None,
        "ema_50": ema_50[-1] if n >= 50 else None,
        "ema_200": ema_200[-1] if n >= 200 else None,
        "rsi_14": rsi_14[-1] if rsi_14[-1] is not None else None,
        "macd": {
            "macd_line": macd_result["macd_line"][-1],
            "signal_line": macd_result["signal_line"][-1],
            "histogram": macd_result["histogram"][-1],
        },
        "adx": adx_result,
        "bollinger_bands": bb,
        "stochastic": stoch,
        "atr": atr_val,
        "obv": obv,
        "vwap": vwap,
        "current_price": closes[-1],
    }


def _obv(closes: List[float], volumes: List[float]) -> Optional[float]:
    """On-Balance Volume."""
    if len(closes) < 2:
        return None
    obv_val = 0.0
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv_val += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv_val -= volumes[i]
    return round(obv_val, 2)


def _vwap(closes: List[float], volumes: List[float]) -> Optional[float]:
    """Volume Weighted Average Price (simplified)."""
    if not closes or not volumes:
        return None
    total_volume = sum(volumes)
    if total_volume == 0:
        return None
    vwap_val = sum(c * v for c, v in zip(closes, volumes)) / total_volume
    return round(vwap_val, 6)


# ══════════════════════════════════════════════════════════════════════
# SMC Detection
# ══════════════════════════════════════════════════════════════════════

class _SMCDetector:
    """
    Smart Money Concepts detector — BOS & CHoCH from swing pivots.

    This is a deterministic implementation that identifies:
      - Break of Structure (BOS): Price breaks a previous swing in the
        direction of the prevailing trend → trend continuation signal.
      - Change of Character (CHoCH): Price breaks a previous swing
        *against* the prevailing trend → trend reversal signal.
    """

    @staticmethod
    def detect(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        lookback: int = 5,
    ) -> Dict[str, Any]:
        """
        Detect SMC signals from OHLC data.

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            lookback: Swing pivot lookback period (default 5).

        Returns:
            Dict with 'signals' list, 'latest_signal', 'structure_state'.
        """
        n = len(closes)
        if n < lookback * 2 + 1:
            return {
                "signals": [],
                "latest_signal": None,
                "structure_state": "NEUTRAL",
            }

        # Step 1: Identify swing highs and lows
        swing_highs: List[tuple[int, float]] = []
        swing_lows: List[tuple[int, float]] = []

        for i in range(lookback, n - lookback):
            is_high = all(highs[i] >= highs[i - j] for j in range(1, lookback + 1)) and \
                      all(highs[i] >= highs[i + j] for j in range(1, lookback + 1))
            is_low = all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)) and \
                     all(lows[i] <= lows[i + j] for j in range(1, lookback + 1))

            if is_high:
                swing_highs.append((i, highs[i]))
            if is_low:
                swing_lows.append((i, lows[i]))

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {
                "signals": [],
                "latest_signal": None,
                "structure_state": "NEUTRAL",
            }

        # Step 2: Determine trend from swing structure
        higher_highs = sum(
            1 for i in range(1, len(swing_highs))
            if swing_highs[i][1] > swing_highs[i - 1][1]
        )
        higher_lows = sum(
            1 for i in range(1, len(swing_lows))
            if swing_lows[i][1] > swing_lows[i - 1][1]
        )

        bull_swings = higher_highs + higher_lows
        bear_swings = (len(swing_highs) - 1 - higher_highs) + (len(swing_lows) - 1 - higher_lows)

        is_bullish_trend = bull_swings > bear_swings

        # Step 3: Detect BOS and CHoCH
        signals: List[Dict[str, Any]] = []

        last_close = closes[-1]
        recent_swing_high = swing_highs[-1]
        recent_swing_low = swing_lows[-1]

        if last_close > recent_swing_high[1]:
            if is_bullish_trend:
                signals.append({
                    "type": "BOS",
                    "direction": "BULL",
                    "level": recent_swing_high[1],
                    "bar_index": n - 1,
                    "description": "Break of Structure — bullish continuation above swing high",
                })
            else:
                signals.append({
                    "type": "CHoCH",
                    "direction": "BULL",
                    "level": recent_swing_high[1],
                    "bar_index": n - 1,
                    "description": "Change of Character — bearish to bullish reversal above swing high",
                })

        if last_close < recent_swing_low[1]:
            if not is_bullish_trend:
                signals.append({
                    "type": "BOS",
                    "direction": "BEAR",
                    "level": recent_swing_low[1],
                    "bar_index": n - 1,
                    "description": "Break of Structure — bearish continuation below swing low",
                })
            else:
                signals.append({
                    "type": "CHoCH",
                    "direction": "BEAR",
                    "level": recent_swing_low[1],
                    "bar_index": n - 1,
                    "description": "Change of Character — bullish to bearish reversal below swing low",
                })

        latest_signal = signals[-1] if signals else None
        structure_state = "BULL" if is_bullish_trend else "BEAR" if bear_swings > bull_swings else "NEUTRAL"

        return {
            "signals": signals,
            "latest_signal": latest_signal,
            "structure_state": structure_state,
            "swing_highs": [{"bar": idx, "price": price} for idx, price in swing_highs[-5:]],
            "swing_lows": [{"bar": idx, "price": price} for idx, price in swing_lows[-5:]],
        }


# ══════════════════════════════════════════════════════════════════════
# Support / Resistance Detection
# ══════════════════════════════════════════════════════════════════════

class _SupportResistanceDetector:
    """
    Support and resistance level detection using swing pivot clustering.

    Groups nearby swing levels into zones and ranks them by the number
    of times price has reacted from each zone.
    """

    @staticmethod
    def detect(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        lookback: int = 5,
        tolerance_pct: float = 0.005,
    ) -> Dict[str, Any]:
        """
        Detect support and resistance levels.

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            lookback: Pivot lookback period.
            tolerance_pct: Clustering tolerance as percentage.

        Returns:
            Dict with 'support_levels', 'resistance_levels',
            'nearest_support', 'nearest_resistance'.
        """
        n = len(closes)
        if n < lookback * 2 + 1:
            return {
                "support_levels": [],
                "resistance_levels": [],
                "nearest_support": None,
                "nearest_resistance": None,
            }

        # Collect pivot points
        pivot_highs: List[float] = []
        pivot_lows: List[float] = []

        for i in range(lookback, n - lookback):
            if all(highs[i] >= highs[i - j] for j in range(1, lookback + 1)):
                pivot_highs.append(highs[i])
            if all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)):
                pivot_lows.append(lows[i])

        # Cluster into levels
        resistance_levels = _SupportResistanceDetector._cluster_levels(
            pivot_highs, tolerance_pct
        )
        support_levels = _SupportResistanceDetector._cluster_levels(
            pivot_lows, tolerance_pct
        )

        # Find nearest levels to current price
        current = closes[-1]
        nearest_support = None
        nearest_resistance = None

        below_price = [s for s in support_levels if s["price"] < current]
        above_price = [r for r in resistance_levels if r["price"] > current]

        if below_price:
            nearest = max(below_price, key=lambda s: s["price"])
            nearest_support = nearest
        if above_price:
            nearest = min(above_price, key=lambda r: r["price"])
            nearest_resistance = nearest

        return {
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
        }

    @staticmethod
    def _cluster_levels(
        levels: List[float], tolerance_pct: float
    ) -> List[Dict[str, Any]]:
        """Cluster nearby price levels into zones."""
        if not levels:
            return []

        sorted_levels = sorted(levels)
        clusters: List[List[float]] = [[sorted_levels[0]]]

        for level in sorted_levels[1:]:
            cluster_avg = sum(clusters[-1]) / len(clusters[-1])
            if abs(level - cluster_avg) / cluster_avg <= tolerance_pct:
                clusters[-1].append(level)
            else:
                clusters.append([level])

        result: List[Dict[str, Any]] = []
        for cluster in clusters:
            avg_price = sum(cluster) / len(cluster)
            result.append({
                "price": round(avg_price, 6),
                "touches": len(cluster),
                "strength": min(len(cluster) / 5.0, 1.0),  # Normalized 0-1
            })

        return sorted(result, key=lambda x: x["touches"], reverse=True)


# ══════════════════════════════════════════════════════════════════════
# TechnicalAnalysisTool class
# ══════════════════════════════════════════════════════════════════════

class TechnicalAnalysisTool:
    """
    Full technical analysis tool for agent consumption.

    Combines deterministic indicator calculations with Smart Money
    Concepts detection, trend classification, support/resistance
    levels, and computed derivative fields.

    Usage::

        tool = TechnicalAnalysisTool(market_data_tool=mdt)
        result = await tool.analyze("AAPL", "1d")
        print(result["trend"]["direction"])  # "BULL" | "BEAR" | "NEUTRAL"
    """

    def __init__(self, market_data_tool: Any | None = None) -> None:
        """
        Initialize the TechnicalAnalysisTool.

        Args:
            market_data_tool: Optional MarketDataTool instance for
                auto-fetching data. If None, raw data must be provided.
        """
        self._market_data = market_data_tool
        self._smc = _SMCDetector()
        self._sr = _SupportResistanceDetector()

    async def analyze(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 200,
    ) -> Dict[str, Any]:
        """
        Run full technical analysis on a symbol.

        Fetches OHLCV data (if a MarketDataTool was provided), runs all
        indicator calculations, SMC detection, support/resistance, and
        computes trend + derivative fields.

        Args:
            symbol: Ticker symbol to analyze.
            timeframe: Candle interval.
            limit: Number of candles to analyze.

        Returns:
            Comprehensive analysis dict with keys:
              - 'symbol', 'timeframe', 'timestamp'
              - 'indicators': Raw indicator output
              - 'smc': Smart Money Concepts signals
              - 'support_resistance': S/R levels
              - 'trend': direction, strength, ema_trend
              - 'derived': price_change_1d, price_change_5d, volume_ratio

        Raises:
            DataError: If data cannot be fetched.
            InsufficientDataError: If not enough bars for analysis.
        """
        if self._market_data is None:
            raise DataError(
                "No MarketDataTool configured — provide one at init or "
                "use analyze_raw() with pre-fetched data."
            )

        ohlcv_result = await self._market_data.get_ohlcv(symbol, timeframe, limit)
        candles = ohlcv_result.get("candles", [])

        if len(candles) < _MIN_BARS:
            raise InsufficientDataError(_MIN_BARS, len(candles), "full_technical_analysis")

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c["volume"] for c in candles]

        return self.analyze_raw(closes, highs, lows, volumes, symbol, timeframe)

    def analyze_raw(
        self,
        closes: List[float],
        highs: List[float] | None = None,
        lows: List[float] | None = None,
        volumes: List[float] | None = None,
        symbol: str = "UNKNOWN",
        timeframe: str = "1d",
    ) -> Dict[str, Any]:
        """
        Run full technical analysis on raw price arrays.

        This is the synchronous path — useful when data is already available.

        Args:
            closes: Close price series (minimum 50 bars).
            highs: High price series (defaults to closes).
            lows: Low price series (defaults to closes).
            volumes: Volume series (defaults to flat 1.0).
            symbol: Symbol label for the result dict.
            timeframe: Timeframe label for the result dict.

        Returns:
            Comprehensive analysis dict.
        """
        if len(closes) < _MIN_BARS:
            raise InsufficientDataError(_MIN_BARS, len(closes), "full_technical_analysis")

        highs = highs or closes
        lows = lows or closes
        volumes = volumes or [1.0] * len(closes)

        # ── Core indicator calculations ───────────────────────────────
        indicators = _compute_all_indicators(closes, highs, lows, volumes)

        # ── SMC detection ─────────────────────────────────────────────
        smc_result = self._smc.detect(highs, lows, closes)

        # ── Support / Resistance ──────────────────────────────────────
        sr_result = self._sr.detect(highs, lows, closes)

        # ── Trend classification ──────────────────────────────────────
        trend = self._classify_trend(closes, indicators)

        # ── Derived fields ────────────────────────────────────────────
        derived = self._compute_derived(closes, volumes)

        # ── Assemble final result ─────────────────────────────────────
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bars_analyzed": len(closes),
            "indicators": indicators,
            "smc": smc_result,
            "support_resistance": sr_result,
            "trend": trend,
            "derived": derived,
        }

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _classify_trend(
        closes: List[float], indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify trend direction and strength from EMA alignment + ADX.

        EMA trend logic:
          - BULL: EMA9 > EMA20 > EMA50 (aligned bullish)
          - BEAR: EMA9 < EMA20 < EMA50 (aligned bearish)
          - NEUTRAL: EMAs are not aligned

        Strength:
          - ADX > 25: strong trend
          - ADX 20-25: moderate trend
          - ADX < 20: weak / no trend
        """
        ema_9 = indicators.get("ema_9")
        ema_20 = indicators.get("ema_20")
        ema_50 = indicators.get("ema_50")
        ema_200 = indicators.get("ema_200")
        adx_val = indicators.get("adx", {}).get("adx")
        plus_di = indicators.get("adx", {}).get("plus_di")
        minus_di = indicators.get("adx", {}).get("minus_di")

        # EMA trend direction
        ema_trend = "NEUTRAL"
        if all(v is not None for v in (ema_9, ema_20, ema_50)):
            if ema_9 > ema_20 > ema_50:  # type: ignore[operator]
                ema_trend = "BULL"
            elif ema_9 < ema_20 < ema_50:  # type: ignore[operator]
                ema_trend = "BEAR"

        # ADX strength
        trend_strength = 0.0
        if adx_val is not None:
            trend_strength = min(adx_val / 50.0, 1.0)  # Normalize to 0-1

        # DI-based direction confirmation
        di_direction = "NEUTRAL"
        if plus_di is not None and minus_di is not None:
            if plus_di > minus_di:
                di_direction = "BULL"
            elif minus_di > plus_di:
                di_direction = "BEAR"

        # Combined direction (EMA takes priority, DI confirms)
        if ema_trend != "NEUTRAL" and ema_trend == di_direction:
            direction = ema_trend
            direction_confidence = "HIGH"
        elif ema_trend != "NEUTRAL":
            direction = ema_trend
            direction_confidence = "MODERATE"
        elif di_direction != "NEUTRAL":
            direction = di_direction
            direction_confidence = "LOW"
        else:
            direction = "NEUTRAL"
            direction_confidence = "NONE"

        # Price vs EMA200 (long-term bias)
        long_term_bias = None
        if ema_200 is not None and closes:
            long_term_bias = "ABOVE" if closes[-1] > ema_200 else "BELOW"

        return {
            "direction": direction,
            "ema_trend": ema_trend,
            "di_direction": di_direction,
            "trend_strength": round(trend_strength, 4),
            "direction_confidence": direction_confidence,
            "long_term_bias": long_term_bias,
            "adx": adx_val,
        }

    @staticmethod
    def _compute_derived(
        closes: List[float], volumes: List[float]
    ) -> Dict[str, Any]:
        """
        Compute derived fields: price changes, volume ratio.

        Args:
            closes: Close price series.
            volumes: Volume series.

        Returns:
            Dict with price_change_1d, price_change_5d, volume_ratio.
        """
        n = len(closes)
        result: Dict[str, Any] = {}

        # Price change 1-day
        if n >= 2:
            result["price_change_1d"] = round(
                (closes[-1] - closes[-2]) / closes[-2] * 100, 4
            )
        else:
            result["price_change_1d"] = None

        # Price change 5-day
        if n >= 6:
            result["price_change_5d"] = round(
                (closes[-1] - closes[-6]) / closes[-6] * 100, 4
            )
        else:
            result["price_change_5d"] = None

        # Volume ratio: current volume / 20-day average volume
        vol_len = min(20, len(volumes))
        if vol_len >= 2 and sum(volumes[-vol_len:]) > 0:
            avg_vol = sum(volumes[-vol_len:]) / vol_len
            result["volume_ratio"] = round(volumes[-1] / avg_vol, 4) if avg_vol > 0 else 0.0
        else:
            result["volume_ratio"] = None

        # Current price position (high-low range over 20 bars)
        if n >= 20:
            recent_high = max(closes[-20:])
            recent_low = min(closes[-20:])
            price_range = recent_high - recent_low
            if price_range > 0:
                result["price_position"] = round(
                    (closes[-1] - recent_low) / price_range, 4
                )
            else:
                result["price_position"] = 0.5
        else:
            result["price_position"] = None

        return result


# ══════════════════════════════════════════════════════════════════════
# Singleton instance for @tool functions
# ══════════════════════════════════════════════════════════════════════

_default_tat: TechnicalAnalysisTool | None = None


def _get_default_tat() -> TechnicalAnalysisTool:
    """Get or create the default TechnicalAnalysisTool instance."""
    global _default_tat
    if _default_tat is None:
        _default_tat = TechnicalAnalysisTool(market_data_tool=_get_default_mdt())
    return _default_tat


# ══════════════════════════════════════════════════════════════════════
# LangChain @tool functions for agent consumption
# ══════════════════════════════════════════════════════════════════════


@tool
async def analyze_technical(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
) -> str:
    """
    Run full technical analysis on a trading symbol.

    Computes SMA, EMA, RSI, MACD, ADX, Bollinger Bands, Stochastic,
    ATR, OBV, VWAP, Smart Money Concepts (BOS/CHoCH), support/resistance
    levels, trend direction, and derived fields.

    Args:
        symbol: Ticker symbol (e.g., 'AAPL', 'BTC/USDT', 'EURUSD=X')
        timeframe: Candle interval ('1m', '5m', '15m', '1h', '4h', '1d')
        limit: Number of candles to analyze (minimum 50, default 200)

    Returns:
        JSON string with comprehensive technical analysis including
        indicators, SMC signals, trend direction, and support/resistance.
    """
    try:
        tat = _get_default_tat()
        result = await tat.analyze(symbol, timeframe, limit)
        return json.dumps(result, indent=2, default=str)
    except (DataError, InsufficientDataError) as exc:
        return json.dumps({"error": str(exc), "symbol": symbol})
    except Exception as exc:
        logger.error("analyze_technical tool error: %s", exc)
        return json.dumps({"error": f"Technical analysis failed: {exc}", "symbol": symbol})
