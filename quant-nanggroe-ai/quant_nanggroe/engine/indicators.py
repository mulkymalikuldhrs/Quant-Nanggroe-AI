"""Technical indicators engine — RSI, SMA, EMA, MACD, Bollinger, VWAP, ATR, ADX, Stochastic, CCI.

Extracts and improves the BEST implementations from:
- Quant-Nanggroe-AI's MathEngine (Wilder's RSI, MACD, Bollinger, VWAP, ATR, Stochastic, CCI)
- ai-hedge-fund's TechnicalIndicators library (pandas/numpy-based indicators)
- Properly implements Wilder's Smoothing for ADX (not SMA proxy)

All functions are pure — no side effects, no state, deterministic output.
Uses numpy/pandas for vectorized computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MACDResult:
    """MACD indicator result."""

    macd_line: float
    signal_line: float
    histogram: float


@dataclass(frozen=True)
class BollingerResult:
    """Bollinger Bands result."""

    upper: float
    middle: float
    lower: float
    bandwidth: float = 0.0
    percent_b: float = 0.0


@dataclass(frozen=True)
class StochasticResult:
    """Stochastic Oscillator result."""

    k: float
    d: float


@dataclass(frozen=True)
class ADXResult:
    """ADX indicator result with directional indicators."""

    adx: float
    plus_di: float
    minus_di: float


@dataclass(frozen=True)
class SMAResult:
    """Simple Moving Averages at standard periods."""

    ma10: float
    ma20: float
    ma50: float
    ma100: float
    ma200: float


@dataclass(frozen=True)
class FullIndicators:
    """Complete technical indicator sheet for a symbol."""

    rsi: float
    stoch: StochasticResult
    cci: float
    adx: ADXResult
    macd: MACDResult
    bollinger: BollingerResult
    vwap: float
    atr: float
    sma: SMAResult


# ──────────────────────────────────────────────────────────────
# Technical Indicators — pure functions
# ──────────────────────────────────────────────────────────────


class TechnicalIndicators:
    """Comprehensive technical indicators library.

    All methods are pure functions that accept numpy arrays or pandas Series
    and return scalar or dataclass results. No side effects, no state.
    """

    # ── SMA ──

    @staticmethod
    def sma(data: np.ndarray | pd.Series, period: int) -> float:
        """Calculate Simple Moving Average.

        Args:
            data: Price series.
            period: Number of periods.

        Returns:
            SMA value (last value). Returns NaN if insufficient data.
        """
        arr = np.asarray(data, dtype=float)
        if len(arr) < period:
            return float("nan")
        return float(np.mean(arr[-period:]))

    @staticmethod
    def sma_series(data: np.ndarray | pd.Series, period: int) -> np.ndarray:
        """Calculate SMA as a full series.

        Args:
            data: Price series.
            period: Number of periods.

        Returns:
            Array of SMA values (NaN for initial periods).
        """
        arr = np.asarray(data, dtype=float)
        if len(arr) < period:
            return np.full_like(arr, np.nan)

        result = np.full_like(arr, np.nan)
        cumsum = np.cumsum(arr)
        result[period - 1:] = (cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])) / period
        return result

    # ── EMA ──

    @staticmethod
    def ema(data: np.ndarray | pd.Series, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average as a full series.

        Uses the standard EMA formula: EMA_t = price_t * k + EMA_{t-1} * (1 - k)
        where k = 2 / (period + 1).

        Args:
            data: Price series.
            period: EMA period.

        Returns:
            Array of EMA values.
        """
        arr = np.asarray(data, dtype=float)
        k = 2.0 / (period + 1)
        result = np.empty_like(arr)
        result[0] = arr[0]
        for i in range(1, len(arr)):
            result[i] = arr[i] * k + result[i - 1] * (1 - k)
        return result

    # ── RSI (Wilder's Smoothing) ──

    @staticmethod
    def rsi(closes: np.ndarray | pd.Series, period: int = 14) -> float:
        """Calculate RSI using Wilder's Smoothing method.

        This is the correct RSI implementation matching TradingView
        and other major platforms.

        Algorithm:
        1. Calculate price changes
        2. Separate into gains (positive) and losses (negative)
        3. First average: simple mean over period
        4. Subsequent averages: Wilder's smoothing
           avg_gain = (prev_avg_gain * (period-1) + current_gain) / period
           avg_loss = (prev_avg_loss * (period-1) + current_loss) / period
        5. RS = avg_gain / avg_loss
        6. RSI = 100 - 100/(1 + RS)

        Args:
            closes: Close price series.
            period: RSI period (default 14).

        Returns:
            RSI value (0–100). Returns 50.0 if insufficient data.
        """
        arr = np.asarray(closes, dtype=float)
        if len(arr) < period + 1:
            return 50.0

        deltas = np.diff(arr)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # First average: simple mean
        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))

        # Wilder's smoothing for subsequent values
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return float(100.0 - (100.0 / (1.0 + rs)))

    @staticmethod
    def rsi_series(closes: np.ndarray | pd.Series, period: int = 14) -> np.ndarray:
        """Calculate RSI as a full series using Wilder's Smoothing.

        Args:
            closes: Close price series.
            period: RSI period.

        Returns:
            Array of RSI values (NaN for initial periods).
        """
        arr = np.asarray(closes, dtype=float)
        n = len(arr)
        result = np.full(n, np.nan)

        if n < period + 1:
            return result

        deltas = np.diff(arr)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # Seed with SMA
        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))

        if avg_loss == 0:
            result[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[period] = 100.0 - (100.0 / (1.0 + rs))

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                result[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

        return result

    # ── MACD ──

    @staticmethod
    def macd(
        closes: np.ndarray | pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> MACDResult:
        """Calculate MACD (Moving Average Convergence Divergence).

        Args:
            closes: Close price series.
            fast_period: Fast EMA period (default 12).
            slow_period: Slow EMA period (default 26).
            signal_period: Signal line period (default 9).

        Returns:
            MACDResult with macd_line, signal_line, and histogram.
        """
        arr = np.asarray(closes, dtype=float)
        if len(arr) < slow_period:
            return MACDResult(macd_line=0.0, signal_line=0.0, histogram=0.0)

        ema_fast = TechnicalIndicators.ema(arr, fast_period)
        ema_slow = TechnicalIndicators.ema(arr, slow_period)

        macd_line_arr = ema_fast - ema_slow
        signal_line_arr = TechnicalIndicators.ema(macd_line_arr, signal_period)

        idx = len(arr) - 1
        macd_val = float(macd_line_arr[idx])
        signal_val = float(signal_line_arr[idx])

        return MACDResult(
            macd_line=macd_val,
            signal_line=signal_val,
            histogram=macd_val - signal_val,
        )

    # ── Bollinger Bands ──

    @staticmethod
    def bollinger_bands(
        closes: np.ndarray | pd.Series,
        period: int = 20,
        multiplier: float = 2.0,
    ) -> BollingerResult:
        """Calculate Bollinger Bands.

        Args:
            closes: Close price series.
            period: SMA period (default 20).
            multiplier: Standard deviation multiplier (default 2.0).

        Returns:
            BollingerResult with upper, middle, lower, bandwidth, and %B.
        """
        arr = np.asarray(closes, dtype=float)
        if len(arr) < period:
            return BollingerResult(upper=0.0, middle=0.0, lower=0.0)

        middle = float(np.mean(arr[-period:]))
        std_dev = float(np.std(arr[-period:], ddof=0))
        upper = middle + multiplier * std_dev
        lower = middle - multiplier * std_dev

        last_close = float(arr[-1])
        bandwidth = (upper - lower) / middle if middle != 0 else 0.0
        percent_b = (last_close - lower) / (upper - lower) if (upper - lower) != 0 else 0.5

        return BollingerResult(
            upper=upper,
            middle=middle,
            lower=lower,
            bandwidth=bandwidth,
            percent_b=percent_b,
        )

    # ── VWAP ──

    @staticmethod
    def vwap(
        highs: np.ndarray | pd.Series,
        lows: np.ndarray | pd.Series,
        closes: np.ndarray | pd.Series,
        volumes: np.ndarray | pd.Series,
    ) -> float:
        """Calculate Volume Weighted Average Price.

        VWAP = cumsum(typical_price * volume) / cumsum(volume)

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            volumes: Volume series.

        Returns:
            VWAP value.
        """
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)
        v = np.asarray(volumes, dtype=float)

        typical_price = (h + l + c) / 3.0
        cum_pv = np.sum(typical_price * v)
        cum_vol = np.sum(v)

        if cum_vol == 0:
            return 0.0
        return float(cum_pv / cum_vol)

    # ── ATR (Average True Range) ──

    @staticmethod
    def atr(
        highs: np.ndarray | pd.Series,
        lows: np.ndarray | pd.Series,
        closes: np.ndarray | pd.Series,
        period: int = 14,
    ) -> float:
        """Calculate Average True Range using Wilder's Smoothing.

        TR = max(high - low, |high - prev_close|, |low - prev_close|)
        First ATR = SMA(TR, period)
        Subsequent ATR = (prev_ATR * (period-1) + current_TR) / period

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            period: ATR period (default 14).

        Returns:
            ATR value. Returns 0.0 if insufficient data.
        """
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)

        if len(c) < period + 1:
            return 0.0

        # Calculate True Range
        tr1 = h[1:] - l[1:]
        tr2 = np.abs(h[1:] - c[:-1])
        tr3 = np.abs(l[1:] - c[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        if len(tr) < period:
            return 0.0

        # First ATR: SMA of first 'period' TRs
        atr_val = float(np.mean(tr[:period]))

        # Wilder's smoothing for subsequent values
        for i in range(period, len(tr)):
            atr_val = (atr_val * (period - 1) + tr[i]) / period

        return float(atr_val)

    # ── ADX (Average Directional Index) — Proper Wilder's Smoothing ──

    @staticmethod
    def adx(
        highs: np.ndarray | pd.Series,
        lows: np.ndarray | pd.Series,
        closes: np.ndarray | pd.Series,
        period: int = 14,
    ) -> ADXResult:
        """Calculate ADX with proper Wilder's Smoothing.

        This is the CORRECT implementation of ADX using Wilder's smoothing
        (not the SMA proxy found in many libraries).

        Algorithm:
        1. Calculate +DM and -DM (directional movement)
        2. Smooth +DM, -DM, and TR using Wilder's method
        3. Calculate +DI and -DI from smoothed values
        4. Calculate DX from +DI and -DI
        5. Smooth DX using Wilder's method to get ADX

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            period: ADX period (default 14).

        Returns:
            ADXResult with adx, plus_di, minus_di.
        """
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)
        n = len(c)

        if n < 2 * period + 1:
            return ADXResult(adx=25.0, plus_di=25.0, minus_di=25.0)

        # 1. Calculate +DM, -DM, and TR
        plus_dm = np.zeros(n - 1)
        minus_dm = np.zeros(n - 1)
        tr = np.zeros(n - 1)

        for i in range(1, n):
            high_diff = h[i] - h[i - 1]
            low_diff = l[i - 1] - l[i]

            plus_dm[i - 1] = high_diff if (high_diff > low_diff and high_diff > 0) else 0.0
            minus_dm[i - 1] = low_diff if (low_diff > high_diff and low_diff > 0) else 0.0

            tr1 = h[i] - l[i]
            tr2 = abs(h[i] - c[i - 1])
            tr3 = abs(l[i] - c[i - 1])
            tr[i - 1] = max(tr1, tr2, tr3)

        # 2. Wilder's smoothing for +DM, -DM, TR
        # First values: sum of first 'period' values
        smooth_plus_dm = np.sum(plus_dm[:period])
        smooth_minus_dm = np.sum(minus_dm[:period])
        smooth_tr = np.sum(tr[:period])

        # 3. Calculate first +DI, -DI
        plus_di_vals = []
        minus_di_vals = []

        if smooth_tr > 0:
            plus_di_vals.append(100.0 * smooth_plus_dm / smooth_tr)
            minus_di_vals.append(100.0 * smooth_minus_dm / smooth_tr)
        else:
            plus_di_vals.append(0.0)
            minus_di_vals.append(0.0)

        # Continue smoothing
        for i in range(period, len(tr)):
            smooth_plus_dm = smooth_plus_dm - (smooth_plus_dm / period) + plus_dm[i]
            smooth_minus_dm = smooth_minus_dm - (smooth_minus_dm / period) + minus_dm[i]
            smooth_tr = smooth_tr - (smooth_tr / period) + tr[i]

            if smooth_tr > 0:
                plus_di_vals.append(100.0 * smooth_plus_dm / smooth_tr)
                minus_di_vals.append(100.0 * smooth_minus_dm / smooth_tr)
            else:
                plus_di_vals.append(0.0)
                minus_di_vals.append(0.0)

        # 4. Calculate DX
        dx_vals = []
        for pdi, mdi in zip(plus_di_vals, minus_di_vals):
            di_sum = pdi + mdi
            if di_sum > 0:
                dx_vals.append(100.0 * abs(pdi - mdi) / di_sum)
            else:
                dx_vals.append(0.0)

        # 5. Calculate ADX using Wilder's smoothing of DX
        if len(dx_vals) < period:
            return ADXResult(
                adx=float(np.mean(dx_vals)) if dx_vals else 25.0,
                plus_di=plus_di_vals[-1] if plus_di_vals else 25.0,
                minus_di=minus_di_vals[-1] if minus_di_vals else 25.0,
            )

        # First ADX: SMA of first 'period' DX values
        adx_val = float(np.mean(dx_vals[:period]))

        # Wilder's smoothing for subsequent ADX
        for i in range(period, len(dx_vals)):
            adx_val = (adx_val * (period - 1) + dx_vals[i]) / period

        return ADXResult(
            adx=float(adx_val),
            plus_di=float(plus_di_vals[-1]),
            minus_di=float(minus_di_vals[-1]),
        )

    # ── Stochastic Oscillator ──

    @staticmethod
    def stochastic(
        highs: np.ndarray | pd.Series,
        lows: np.ndarray | pd.Series,
        closes: np.ndarray | pd.Series,
        k_period: int = 14,
        d_period: int = 3,
    ) -> StochasticResult:
        """Calculate Stochastic Oscillator.

        %K = 100 * (close - lowest_low) / (highest_high - lowest_low)
        %D = SMA(%K, d_period)

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            k_period: %K lookback period (default 14).
            d_period: %D smoothing period (default 3).

        Returns:
            StochasticResult with k and d values.
        """
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)

        if len(c) < k_period:
            return StochasticResult(k=50.0, d=50.0)

        # Calculate raw %K values
        k_values = []
        for i in range(k_period - 1, len(c)):
            period_highs = h[i - k_period + 1: i + 1]
            period_lows = l[i - k_period + 1: i + 1]
            highest_high = np.max(period_highs)
            lowest_low = np.min(period_lows)

            if highest_high == lowest_low:
                k_values.append(50.0)
            else:
                k_values.append(100.0 * (c[i] - lowest_low) / (highest_high - lowest_low))

        # %D = SMA of %K
        if len(k_values) >= d_period:
            d_value = float(np.mean(k_values[-d_period:]))
        else:
            d_value = float(np.mean(k_values))

        return StochasticResult(k=float(k_values[-1]), d=d_value)

    # ── CCI (Commodity Channel Index) ──

    @staticmethod
    def cci(
        highs: np.ndarray | pd.Series,
        lows: np.ndarray | pd.Series,
        closes: np.ndarray | pd.Series,
        period: int = 20,
    ) -> float:
        """Calculate Commodity Channel Index.

        CCI = (TP - SMA(TP)) / (0.015 * Mean Deviation)

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            period: CCI period (default 20).

        Returns:
            CCI value.
        """
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)

        if len(c) < period:
            return 0.0

        typical_price = (h + l + c) / 3.0
        recent_tp = typical_price[-period:]
        sma_tp = float(np.mean(recent_tp))
        mean_dev = float(np.mean(np.abs(recent_tp - sma_tp)))

        if mean_dev == 0:
            return 0.0

        current_tp = float(typical_price[-1])
        return float((current_tp - sma_tp) / (0.015 * mean_dev))

    # ── MASTER: Analyze full indicator sheet ──

    @staticmethod
    def analyze(
        highs: np.ndarray | pd.Series,
        lows: np.ndarray | pd.Series,
        closes: np.ndarray | pd.Series,
        volumes: Optional[np.ndarray | pd.Series] = None,
    ) -> FullIndicators:
        """Generate a complete technical indicator sheet.

        This is the master function that computes all indicators at once,
        producing a FullIndicators result suitable for the MarketStateEngine
        and trading agents.

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            volumes: Volume series (optional, for VWAP).

        Returns:
            FullIndicators with all computed indicators.
        """
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)
        v = np.asarray(volumes, dtype=float) if volumes is not None else np.ones_like(c)

        return FullIndicators(
            rsi=TechnicalIndicators.rsi(c),
            stoch=TechnicalIndicators.stochastic(h, l, c),
            cci=TechnicalIndicators.cci(h, l, c),
            adx=TechnicalIndicators.adx(h, l, c),
            macd=TechnicalIndicators.macd(c),
            bollinger=TechnicalIndicators.bollinger_bands(c),
            vwap=TechnicalIndicators.vwap(h, l, c, v),
            atr=TechnicalIndicators.atr(h, l, c),
            sma=SMAResult(
                ma10=TechnicalIndicators.sma(c, 10),
                ma20=TechnicalIndicators.sma(c, 20),
                ma50=TechnicalIndicators.sma(c, 50),
                ma100=TechnicalIndicators.sma(c, 100),
                ma200=TechnicalIndicators.sma(c, 200),
            ),
        )
