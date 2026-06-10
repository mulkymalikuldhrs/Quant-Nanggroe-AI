"""
Math Engine — Full Deterministic Indicator Suite
=================================================
Merged from HermesQuantOS (Python) + Quant-Nanggroe-AI (TypeScript).

100% deterministic — no AI, no approximation.
All indicators use proper Wilder's smoothing (not SMA approximation).

Indicators:
    SMA, EMA, WMA, RSI (Wilder's), MACD, Bollinger Bands,
    ATR (Wilder's), VWAP, Volume Profile, Stochastic, CCI,
    ADX (+DI, -DI, Wilder's smoothing), Pearson Correlation,
    Kelly Criterion
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


class MathEngine:
    """
    Pure mathematical indicator calculations — no AI, no approximation.

    Uses pandas/numpy for proper vectorized calculations where beneficial,
    with Wilder's smoothing (not SMA approximation) for RSI, ATR, and ADX.
    """

    # ══════════════════════════════════════════════════════════════════
    # Moving Averages
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def sma(data: list[float], period: int) -> list[float | None]:
        """
        Simple Moving Average.

        Args:
            data: Price series
            period: Lookback period

        Returns:
            List with SMA values (None for insufficient data points)
        """
        result: list[float | None] = [None] * len(data)
        if period < 1 or len(data) < period:
            return result
        for i in range(period - 1, len(data)):
            result[i] = sum(data[i - period + 1 : i + 1]) / period
        return result

    @staticmethod
    def ema(data: list[float], period: int) -> list[float | None]:
        """
        Exponential Moving Average using standard multiplier k = 2/(period+1).

        Seed: SMA of first `period` values.
        Note: For Wilder's smoothing (used in RSI/ATR/ADX), use `_wilder_smooth`.

        Args:
            data: Price series
            period: Lookback period

        Returns:
            List with EMA values (None for insufficient data points)
        """
        result: list[float | None] = [None] * len(data)
        if period < 1 or len(data) < period:
            return result

        multiplier = 2.0 / (period + 1)
        # Seed with SMA
        result[period - 1] = sum(data[:period]) / period
        for i in range(period, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        return result

    @staticmethod
    def _wilder_smooth(data: list[float], period: int) -> list[float | None]:
        """
        Wilder's Smoothing (used in RSI, ATR, ADX).

        Equivalent to EMA with alpha = 1/period (not 2/(period+1)).
        Formula: wilder[i] = wilder[i-1] * (period - 1) / period + data[i] / period
                                 = wilder[i-1] + (data[i] - wilder[i-1]) / period

        Args:
            data: Input series
            period: Wilder's period

        Returns:
            List with Wilder-smoothed values
        """
        result: list[float | None] = [None] * len(data)
        if period < 1 or len(data) < period:
            return result

        # Seed: SMA of first `period` values
        result[period - 1] = sum(data[:period]) / period
        for i in range(period, len(data)):
            result[i] = result[i - 1] + (data[i] - result[i - 1]) / period
        return result

    @staticmethod
    def wma(data: list[float], period: int) -> list[float | None]:
        """
        Weighted Moving Average.

        Args:
            data: Price series
            period: Lookback period

        Returns:
            List with WMA values (None for insufficient data points)
        """
        result: list[float | None] = [None] * len(data)
        if period < 1 or len(data) < period:
            return result

        weight_sum = period * (period + 1) / 2
        for i in range(period - 1, len(data)):
            w_sum = sum(data[i - period + 1 + j] * (j + 1) for j in range(period))
            result[i] = w_sum / weight_sum
        return result

    # ══════════════════════════════════════════════════════════════════
    # RSI (Wilder's Smoothing — Proper Implementation)
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def rsi(closes: list[float], period: int = 14) -> list[float | None]:
        """
        RSI using Wilder's smoothing method (NOT SMA approximation).

        The correct implementation uses:
        avg_gain = (prev_avg_gain * (period - 1) + current_gain) / period
        avg_loss = (prev_avg_loss * (period - 1) + current_loss) / period

        This is equivalent to Wilder's EMA with alpha = 1/period.

        Args:
            closes: Close price series
            period: RSI period (default 14)

        Returns:
            List with RSI values (None for insufficient data points)
        """
        result: list[float | None] = [None] * len(closes)
        if len(closes) < period + 1:
            return result

        # Calculate price changes
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [-d if d < 0 else 0.0 for d in deltas]

        # First average: simple mean of first `period` values
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Wilder's smoothing for subsequent values
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                result[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

        return result

    # ══════════════════════════════════════════════════════════════════
    # MACD
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def macd(
        closes: list[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> dict[str, list[float | None]]:
        """
        MACD, Signal Line, and Histogram.

        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD Line, signal)
        Histogram = MACD - Signal

        Args:
            closes: Close price series
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            Dict with 'macd', 'signal', 'histogram' lists
        """
        ema_fast = MathEngine.ema(closes, fast)
        ema_slow = MathEngine.ema(closes, slow)

        # MACD line
        macd_line: list[float | None] = [None] * len(closes)
        for i in range(len(closes)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line[i] = ema_fast[i] - ema_slow[i]  # type: ignore[operator]

        # Signal line: EMA of MACD values (use 0 for None values for proper EMA seeding)
        macd_values = [v if v is not None else 0.0 for v in macd_line]
        signal_line = MathEngine.ema(macd_values, signal)

        # Histogram
        histogram: list[float | None] = [None] * len(closes)
        for i in range(len(closes)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram[i] = macd_line[i] - signal_line[i]  # type: ignore[operator]

        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    # ══════════════════════════════════════════════════════════════════
    # Bollinger Bands
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def bollinger_bands(
        closes: list[float],
        period: int = 20,
        num_std: float = 2.0,
    ) -> dict[str, list[float | None]]:
        """
        Bollinger Bands with SMA middle band and ±Nσ bands.

        Also computes Bandwidth and %B.

        Args:
            closes: Close price series
            period: SMA period (default 20)
            num_std: Number of standard deviations (default 2.0)

        Returns:
            Dict with 'middle', 'upper', 'lower', 'bandwidth', 'percent_b'
        """
        middle = MathEngine.sma(closes, period)
        upper: list[float | None] = [None] * len(closes)
        lower: list[float | None] = [None] * len(closes)
        bandwidth: list[float | None] = [None] * len(closes)
        percent_b: list[float | None] = [None] * len(closes)

        for i in range(period - 1, len(closes)):
            assert middle[i] is not None
            slice_data = closes[i - period + 1 : i + 1]
            std = math.sqrt(sum((x - middle[i]) ** 2 for x in slice_data) / period)
            upper[i] = middle[i] + num_std * std
            lower[i] = middle[i] - num_std * std
            bandwidth[i] = (upper[i] - lower[i]) / middle[i] if middle[i] else 0.0
            percent_b[i] = (
                (closes[i] - lower[i]) / (upper[i] - lower[i])
                if (upper[i] - lower[i])
                else 0.5
            )

        return {
            "middle": middle,
            "upper": upper,
            "lower": lower,
            "bandwidth": bandwidth,
            "percent_b": percent_b,
        }

    # ══════════════════════════════════════════════════════════════════
    # ATR (Average True Range — Wilder's Smoothing)
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def atr(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int = 14,
    ) -> list[float | None]:
        """
        Average True Range using Wilder's smoothing.

        TR = max(H-L, |H-prevC|, |L-prevC|)
        First ATR = SMA of first `period` TRs
        Subsequent: ATR = (prev_ATR * (period-1) + current_TR) / period

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: ATR period (default 14)

        Returns:
            List with ATR values (None for insufficient data points)
        """
        result: list[float | None] = [None] * len(closes)
        if len(closes) < 2:
            return result

        # Calculate True Range
        true_ranges = [0.0]  # First bar has no previous close
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        if len(true_ranges) < period + 1:
            return result

        # First ATR = SMA of first `period` TRs
        result[period] = sum(true_ranges[1 : period + 1]) / period

        # Wilder's smoothing for subsequent values
        for i in range(period + 1, len(true_ranges)):
            result[i] = (result[i - 1] * (period - 1) + true_ranges[i]) / period

        return result

    # ══════════════════════════════════════════════════════════════════
    # Stochastic Oscillator
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def stochastic(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        k_period: int = 14,
        k_smooth: int = 3,
        d_period: int = 3,
    ) -> dict[str, list[float | None]]:
        """
        Stochastic Oscillator %K and %D.

        Raw %K = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
        %K = SMA(Raw %K, k_smooth)
        %D = SMA(%K, d_period)

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            k_period: %K lookback period (default 14)
            k_smooth: %K smoothing period (default 3)
            d_period: %D smoothing period (default 3)

        Returns:
            Dict with 'k' and 'd' lists
        """
        raw_k: list[float | None] = [None] * len(closes)

        for i in range(k_period - 1, len(closes)):
            highest = max(highs[i - k_period + 1 : i + 1])
            lowest = min(lows[i - k_period + 1 : i + 1])
            if highest - lowest == 0:
                raw_k[i] = 50.0
            else:
                raw_k[i] = ((closes[i] - lowest) / (highest - lowest)) * 100

        # Smooth %K
        k_values: list[float | None] = [None] * len(closes)
        for i in range(k_period - 1 + k_smooth - 1, len(closes)):
            slice_data = [v for v in raw_k[i - k_smooth + 1 : i + 1] if v is not None]
            if len(slice_data) == k_smooth:
                k_values[i] = sum(slice_data) / k_smooth

        # %D = SMA of %K
        d_values = MathEngine.sma(
            [v if v is not None else 0.0 for v in k_values], d_period
        )

        return {"k": k_values, "d": d_values}

    # ══════════════════════════════════════════════════════════════════
    # CCI (Commodity Channel Index)
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def cci(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int = 20,
    ) -> list[float | None]:
        """
        Commodity Channel Index.

        CCI = (TP - SMA(TP)) / (0.015 * Mean Deviation)

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: CCI period (default 20)

        Returns:
            List with CCI values
        """
        result: list[float | None] = [None] * len(closes)
        tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        tp_sma = MathEngine.sma(tp, period)

        for i in range(period - 1, len(closes)):
            assert tp_sma[i] is not None
            mean_dev = sum(abs(tp[j] - tp_sma[i]) for j in range(i - period + 1, i + 1)) / period
            result[i] = (tp[i] - tp_sma[i]) / (0.015 * mean_dev) if mean_dev else 0.0

        return result

    # ══════════════════════════════════════════════════════════════════
    # ADX (Average Directional Index — Full Wilder's Implementation)
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def adx(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int = 14,
    ) -> dict[str, list[float | None]]:
        """
        ADX with +DI and -DI using proper Wilder's smoothing.

        Steps:
        1. Calculate +DM and -DM
        2. Smooth +DM, -DM, TR with Wilder's method (same as ATR)
        3. +DI = (Smoothed +DM / Smoothed TR) * 100
        4. -DI = (Smoothed -DM / Smoothed TR) * 100
        5. DX = |+DI - -DI| / (+DI + -DI) * 100
        6. ADX = Wilder's smoothed DX

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: ADX period (default 14)

        Returns:
            Dict with 'adx', 'plus_di', 'minus_di', 'dx' lists
        """
        n = len(closes)
        plus_dm = [0.0] * n
        minus_dm = [0.0] * n
        tr = [0.0] * n

        # Step 1: Calculate +DM, -DM, TR
        for i in range(1, n):
            high_diff = highs[i] - highs[i - 1]
            low_diff = lows[i - 1] - lows[i]

            plus_dm[i] = high_diff if (high_diff > low_diff and high_diff > 0) else 0.0
            minus_dm[i] = low_diff if (low_diff > high_diff and low_diff > 0) else 0.0
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )

        # Step 2: Wilder's smoothing of +DM, -DM, TR
        atr_vals: list[float | None] = [None] * n
        smooth_plus_dm: list[float | None] = [None] * n
        smooth_minus_dm: list[float | None] = [None] * n

        if n <= period:
            return {
                "adx": [None] * n,
                "plus_di": [None] * n,
                "minus_di": [None] * n,
                "dx": [None] * n,
            }

        # Seed: SMA of first `period` values
        atr_vals[period] = sum(tr[1 : period + 1]) / period
        smooth_plus_dm[period] = sum(plus_dm[1 : period + 1]) / period
        smooth_minus_dm[period] = sum(minus_dm[1 : period + 1]) / period

        # Wilder's smoothing for subsequent values
        for i in range(period + 1, n):
            atr_vals[i] = (atr_vals[i - 1] * (period - 1) + tr[i]) / period
            smooth_plus_dm[i] = (smooth_plus_dm[i - 1] * (period - 1) + plus_dm[i]) / period
            smooth_minus_dm[i] = (smooth_minus_dm[i - 1] * (period - 1) + minus_dm[i]) / period

        # Step 3-5: Calculate +DI, -DI, DX
        plus_di: list[float | None] = [None] * n
        minus_di: list[float | None] = [None] * n
        dx: list[float | None] = [None] * n

        for i in range(period, n):
            if atr_vals[i] and atr_vals[i] > 0:
                plus_di[i] = (smooth_plus_dm[i] / atr_vals[i]) * 100  # type: ignore[operator]
                minus_di[i] = (smooth_minus_dm[i] / atr_vals[i]) * 100  # type: ignore[operator]
                di_sum = plus_di[i] + minus_di[i]
                dx[i] = abs(plus_di[i] - minus_di[i]) / di_sum * 100 if di_sum else 0.0

        # Step 6: ADX = Wilder's smoothed DX
        adx_values: list[float | None] = [None] * n
        if n > 2 * period:
            # First ADX = SMA of first `period` DX values
            dx_slice = [dx[j] for j in range(period, 2 * period) if dx[j] is not None]
            if dx_slice:
                adx_values[2 * period - 1] = sum(dx_slice) / len(dx_slice)

            # Wilder's smoothing for subsequent ADX values
            for i in range(2 * period, n):
                if dx[i] is not None and adx_values[i - 1] is not None:
                    adx_values[i] = (adx_values[i - 1] * (period - 1) + dx[i]) / period

        return {"adx": adx_values, "plus_di": plus_di, "minus_di": minus_di, "dx": dx}

    # ══════════════════════════════════════════════════════════════════
    # VWAP (Volume Weighted Average Price)
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def vwap(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        volumes: list[float],
    ) -> list[float | None]:
        """
        Cumulative VWAP (Volume Weighted Average Price).

        VWAP = Cumulative(TP * Volume) / Cumulative(Volume)
        TP = (High + Low + Close) / 3

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            volumes: Volume series

        Returns:
            List with VWAP values
        """
        result: list[float | None] = [None] * len(closes)
        cum_tp_vol = 0.0
        cum_vol = 0.0

        for i in range(len(closes)):
            tp = (highs[i] + lows[i] + closes[i]) / 3
            cum_tp_vol += tp * volumes[i]
            cum_vol += volumes[i]
            result[i] = cum_tp_vol / cum_vol if cum_vol > 0 else None

        return result

    # ══════════════════════════════════════════════════════════════════
    # Volume Profile
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def volume_profile(
        highs: list[float],
        lows: list[float],
        volumes: list[float],
        num_bins: int = 20,
    ) -> dict[str, Any]:
        """
        Volume profile with High Volume Node (HVN) and Low Volume Node (LVN) detection.

        Args:
            highs: High price series
            lows: Low price series
            volumes: Volume series
            num_bins: Number of price bins (default 20)

        Returns:
            Dict with 'bins', 'hvn', 'lvn'
        """
        if not highs:
            return {"bins": [], "hvn": None, "lvn": None}

        price_min = min(lows)
        price_max = max(highs)
        price_range = price_max - price_min

        if price_range == 0:
            return {"bins": [], "hvn": None, "lvn": None}

        bin_size = price_range / num_bins
        bins = [
            {
                "low": price_min + i * bin_size,
                "high": price_min + (i + 1) * bin_size,
                "volume": 0.0,
            }
            for i in range(num_bins)
        ]

        for i in range(len(volumes)):
            mid = (highs[i] + lows[i]) / 2
            bin_idx = min(int((mid - price_min) / bin_size), num_bins - 1)
            bins[bin_idx]["volume"] += volumes[i]

        total_vol = sum(b["volume"] for b in bins)
        for b in bins:
            b["pct"] = round(b["volume"] / total_vol * 100, 1) if total_vol else 0.0

        # Find HVN and LVN
        max_vol_bin = max(bins, key=lambda b: b["volume"])
        min_vol_bin = min(bins, key=lambda b: b["volume"])

        return {
            "bins": bins,
            "hvn": {
                "price": (max_vol_bin["low"] + max_vol_bin["high"]) / 2,
                "volume": max_vol_bin["volume"],
                "pct": max_vol_bin["pct"],
            },
            "lvn": {
                "price": (min_vol_bin["low"] + min_vol_bin["high"]) / 2,
                "volume": min_vol_bin["volume"],
                "pct": min_vol_bin["pct"],
            },
        }

    # ══════════════════════════════════════════════════════════════════
    # Pearson Correlation
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def correlation(x: list[float], y: list[float]) -> float | None:
        """
        Pearson correlation coefficient between two series.

        Args:
            x: First series
            y: Second series

        Returns:
            Correlation coefficient (-1 to 1), or None if insufficient data
        """
        n = min(len(x), len(y))
        if n < 2:
            return None

        mean_x = sum(x[:n]) / n
        mean_y = sum(y[:n]) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = math.sqrt(sum((x[i] - mean_x) ** 2 for i in range(n)) / n)
        std_y = math.sqrt(sum((y[i] - mean_y) ** 2 for i in range(n)) / n)

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)

    # ══════════════════════════════════════════════════════════════════
    # Kelly Criterion
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.25,
    ) -> dict[str, Any]:
        """
        Kelly Criterion position sizing.

        Full Kelly = win_rate - (1 - win_rate) / (avg_win / avg_loss)
        Fractional Kelly = Full Kelly * fraction (for safety, default 0.25 = quarter)

        Args:
            win_rate: Win rate (0.0 - 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount
            fraction: Fractional Kelly multiplier (default 0.25)

        Returns:
            Dict with kelly_pct, fractional_kelly, recommendation
        """
        if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
            return {
                "kelly_pct": 0,
                "fractional_kelly": 0,
                "recommendation": "NO_TRADE",
            }

        r = avg_win / avg_loss  # Win/loss ratio
        full_kelly = win_rate - ((1 - win_rate) / r)
        fractional = full_kelly * fraction

        return {
            "win_rate": round(win_rate, 4),
            "win_loss_ratio": round(r, 4),
            "full_kelly": round(full_kelly, 4),
            "fraction": fraction,
            "fractional_kelly": round(fractional, 4),
            "recommendation": f"Risk {fractional:.2%} of capital per trade",
        }

    # ══════════════════════════════════════════════════════════════════
    # Master Analysis
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def analyze_sequence(
        closes: list[float],
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        volumes: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        Run full indicator analysis on price data.

        This is the master function that computes all indicators at once.

        Args:
            closes: Close price series (minimum 30 bars)
            highs: High price series (defaults to closes)
            lows: Low price series (defaults to closes)
            volumes: Volume series (defaults to [1.0] * len(closes))

        Returns:
            Dict with all indicator values and metadata
        """
        if not closes or len(closes) < 30:
            return {"error": "Insufficient data (need 30+ bars)"}

        highs = highs or closes
        lows = lows or closes
        volumes = volumes or [1.0] * len(closes)

        result: dict[str, Any] = {
            "latest_close": closes[-1],
            "bars": len(closes),
            "timestamp": datetime.now().isoformat(),
            "indicators": {},
        }

        # RSI
        rsi_vals = MathEngine.rsi(closes, 14)
        result["indicators"]["rsi_14"] = rsi_vals[-1]

        # EMA
        for period in [9, 20, 50, 200]:
            ema_vals = MathEngine.ema(closes, period)
            result["indicators"][f"ema_{period}"] = ema_vals[-1]

        # SMA
        for period in [20, 50, 200]:
            sma_vals = MathEngine.sma(closes, period)
            result["indicators"][f"sma_{period}"] = sma_vals[-1]

        # MACD
        macd_result = MathEngine.macd(closes)
        result["indicators"]["macd"] = {
            "line": macd_result["macd"][-1],
            "signal": macd_result["signal"][-1],
            "histogram": macd_result["histogram"][-1],
        }

        # Bollinger Bands
        bb = MathEngine.bollinger_bands(closes)
        result["indicators"]["bollinger"] = {
            "upper": bb["upper"][-1],
            "middle": bb["middle"][-1],
            "lower": bb["lower"][-1],
            "bandwidth": bb["bandwidth"][-1],
            "percent_b": bb["percent_b"][-1],
        }

        # ATR
        atr_vals = MathEngine.atr(highs, lows, closes, 14)
        result["indicators"]["atr_14"] = atr_vals[-1]
        result["indicators"]["atr_pct"] = (
            (atr_vals[-1] / closes[-1] * 100) if atr_vals[-1] and closes[-1] else None
        )

        # Stochastic
        stoch = MathEngine.stochastic(highs, lows, closes)
        result["indicators"]["stochastic"] = {
            "k": stoch["k"][-1],
            "d": stoch["d"][-1],
        }

        # CCI
        cci_vals = MathEngine.cci(highs, lows, closes)
        result["indicators"]["cci_20"] = cci_vals[-1]

        # ADX
        adx_result = MathEngine.adx(highs, lows, closes)
        result["indicators"]["adx"] = {
            "adx": adx_result["adx"][-1],
            "plus_di": adx_result["plus_di"][-1],
            "minus_di": adx_result["minus_di"][-1],
        }

        # VWAP
        vwap_vals = MathEngine.vwap(highs, lows, closes, volumes)
        result["indicators"]["vwap"] = vwap_vals[-1]

        # Volume Profile
        vp = MathEngine.volume_profile(highs[-50:], lows[-50:], volumes[-50:])
        result["indicators"]["volume_profile"] = vp

        return result
