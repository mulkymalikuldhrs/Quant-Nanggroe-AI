"""Momentum Strategy.

Implements production-quality momentum trading using:
1. Time-series momentum (MOM) across multiple lookbacks
2. Cross-sectional momentum (relative strength ranking)
3. Dual momentum (absolute + relative)
4. Moving average crossover (SMA, EMA, WMA, HMA)
5. MACD-based momentum
6. Trend following with ATR trailing stop

Academic References:
    - Jegadeesh, N. & Titman, S. (1993). "Returns to Buying Winners and Selling Losers."
      Journal of Finance, 48(1), 65-91.
    - Moskowitz, T.J., Ooi, Y.H., & Pedersen, L.H. (2012). "Time Series Momentum."
      Journal of Financial Economics, 104(2), 228-250.
    - Antonacci, G. (2014). Dual Momentum Investing. McGraw-Hill.
    - Hull, A.W. (2005). "How to Reduce Lag in a Moving Average."
      Active Trader Magazine.
    - Wilder, J.W. (1978). New Concepts in Technical Trading Systems. Trend Research.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class MomentumStrategy(BaseStrategy):
    """Multi-method momentum strategy.

    Supports multiple momentum calculation modes:
    - 'ts_momentum': Time-series momentum (price change over lookback)
    - 'dual_momentum': Absolute + relative momentum
    - 'ma_crossover': Moving average crossover system
    - 'macd': MACD-based momentum

    Parameters:
        mode: Momentum calculation mode (default 'ts_momentum').
        fast_period: Fast MA / momentum lookback (default 12).
        slow_period: Slow MA period (default 26).
        signal_period: Signal line period for MACD (default 9).
        atr_period: ATR period for trailing stop (default 14).
        atr_multiplier: ATR multiplier for trailing stop distance (default 2.5).
        stop_loss_pct: Hard stop loss fraction (default 0.05).
        take_profit_pct: Take profit fraction (default 0.15).
        ma_type: Moving average type: 'sma', 'ema', 'wma', 'hma' (default 'ema').
        lookbacks: List of momentum lookback periods (default [21, 63, 126]).
        symbol: Trading symbol (default "ASSET").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="Momentum", params=params)
        self.mode: str = self.params.get("mode", "ts_momentum")
        self.fast_period: int = self.params.get("fast_period", 12)
        self.slow_period: int = self.params.get("slow_period", 26)
        self.signal_period: int = self.params.get("signal_period", 9)
        self.atr_period: int = self.params.get("atr_period", 14)
        self.atr_multiplier: float = self.params.get("atr_multiplier", 2.5)
        self.stop_loss_pct: float = self.params.get("stop_loss_pct", 0.05)
        self.take_profit_pct: float = self.params.get("take_profit_pct", 0.15)
        self.ma_type: str = self.params.get("ma_type", "ema")
        self.lookbacks: List[int] = self.params.get("lookbacks", [21, 63, 126])
        self.symbol: str = self.params.get("symbol", "ASSET")

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        if self.mode == "ma_crossover":
            return self.slow_period + 20
        elif self.mode == "macd":
            return self.slow_period + self.signal_period + 10
        else:
            return max(self.lookbacks) + 10

    def compute_wma(self, series: pd.Series, period: int) -> pd.Series:
        """Compute Weighted Moving Average.

        WMA weights increase linearly: weight for bar i is (i+1) / (n*(n+1)/2).

        Args:
            series: Price series.
            period: WMA period.

        Returns:
            WMA series.
        """
        weights = np.arange(1, period + 1, dtype=float)
        weights /= weights.sum()
        return series.rolling(window=period, min_periods=period).apply(
            lambda x: np.dot(x, weights), raw=True
        )

    def compute_hma(self, series: pd.Series, period: int) -> pd.Series:
        """Compute Hull Moving Average (HMA).

        HMA = WMA(2 * WMA(period/2) - WMA(period), sqrt(period))

        Reference: Hull, A.W. (2005). "How to Reduce Lag in a Moving Average."

        Args:
            series: Price series.
            period: HMA period.

        Returns:
            HMA series.
        """
        half_period = max(int(period / 2), 1)
        sqrt_period = max(int(np.sqrt(period)), 1)

        wma_half = self.compute_wma(series, half_period)
        wma_full = self.compute_wma(series, period)
        diff = 2 * wma_half - wma_full
        hma = self.compute_wma(diff, sqrt_period)
        return hma

    def compute_ma(self, series: pd.Series, period: int) -> pd.Series:
        """Compute moving average of the configured type.

        Args:
            series: Price series.
            period: MA period.

        Returns:
            Moving average series.
        """
        if self.ma_type == "sma":
            return self.compute_sma(series, period)
        elif self.ma_type == "ema":
            return self.compute_ema(series, period)
        elif self.ma_type == "wma":
            return self.compute_wma(series, period)
        elif self.ma_type == "hma":
            return self.compute_hma(series, period)
        else:
            return self.compute_ema(series, period)

    def compute_ts_momentum(self, data: pd.DataFrame) -> tuple[str, float]:
        """Compute time-series momentum score.

        Aggregates momentum across multiple lookbacks using a
        weighted voting scheme where shorter lookbacks get more weight
        (recency bias).

        Reference:
            Moskowitz, Ooi, & Pedersen (2012). "Time Series Momentum."

        Args:
            data: OHLCV DataFrame.

        Returns:
            Tuple of (direction, score). direction is 'long'/'short'/'flat',
            score is the weighted momentum strength.
        """
        close = data["close"]
        total_score = 0.0
        total_weight = 0.0

        for i, lb in enumerate(self.lookbacks):
            if len(close) < lb + 1:
                continue
            # Momentum = current price / price lb bars ago - 1
            mom = (close.iloc[-1] / close.iloc[-lb - 1]) - 1.0
            # Weight: shorter lookbacks get more weight (recency)
            weight = 1.0 / (i + 1)
            total_score += np.sign(mom) * weight
            total_weight += weight

        if total_weight == 0:
            return "flat", 0.0

        avg_score = total_score / total_weight

        if avg_score > 0.1:
            return "long", avg_score
        elif avg_score < -0.1:
            return "short", abs(avg_score)
        else:
            return "flat", abs(avg_score)

    def compute_dual_momentum(self, data: pd.DataFrame) -> tuple[str, float]:
        """Compute dual momentum (absolute + relative).

        Absolute momentum: Is the asset above its slow MA? (positive trend)
        Relative momentum: Is the momentum score positive? (outperforming)

        Only go long if BOTH are positive (dual momentum rule).
        Only go short if BOTH are negative.

        Reference:
            Antonacci, G. (2014). Dual Momentum Investing.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Tuple of (direction, score).
        """
        close = data["close"]
        slow_ma = self.compute_ma(close, self.slow_period)
        current_price = close.iloc[-1]
        current_ma = slow_ma.iloc[-1]

        if np.isnan(current_ma):
            return "flat", 0.0

        # Absolute momentum: price vs slow MA
        absolute_momentum = (current_price / current_ma) - 1.0

        # Relative momentum: time-series momentum
        ts_direction, ts_score = self.compute_ts_momentum(data)

        # Dual momentum logic
        if absolute_momentum > 0 and ts_direction == "long":
            combined = (absolute_momentum + ts_score) / 2
            return "long", min(combined, 1.0)
        elif absolute_momentum < 0 and ts_direction == "short":
            combined = (abs(absolute_momentum) + ts_score) / 2
            return "short", min(combined, 1.0)
        else:
            return "flat", 0.0

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate momentum-based trading signal.

        Uses the configured mode to determine signal generation logic.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Signal if momentum condition is met, None otherwise.
        """
        if not self.validate_data(data):
            return None

        close = data["close"]
        high = data["high"]
        low = data["low"]
        current_price = close.iloc[-1]

        # ATR for trailing stop
        atr = self.compute_atr(high, low, close, self.atr_period)
        current_atr = atr.iloc[-1] if not np.isnan(atr.iloc[-1]) else current_price * 0.02

        if self.mode == "ts_momentum":
            direction, score = self.compute_ts_momentum(data)
        elif self.mode == "dual_momentum":
            direction, score = self.compute_dual_momentum(data)
        elif self.mode == "ma_crossover":
            direction, score = self._ma_crossover_signal(data)
        elif self.mode == "macd":
            direction, score = self._macd_signal(data)
        else:
            direction, score = self.compute_ts_momentum(data)

        if direction == "flat" or score < 0.05:
            return None

        confidence = min(score, 1.0)

        if direction == "long":
            # Trailing stop: current_price - atr_multiplier * ATR
            trailing_stop = current_price - self.atr_multiplier * current_atr
            stop_loss = min(
                current_price * (1 - self.stop_loss_pct),
                trailing_stop,
            )
            take_profit = current_price * (1 + self.take_profit_pct)

            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Momentum BUY ({self.mode}): score={score:.3f}, "
                    f"ATR={current_atr:.4f}, trailing_stop={trailing_stop:.4f}"
                ),
                evidence={
                    "mode": self.mode,
                    "score": round(score, 4),
                    "atr": round(float(current_atr), 4),
                    "trailing_stop": round(float(trailing_stop), 4),
                },
                factors=["momentum", self.mode],
            )
        else:  # short
            trailing_stop = current_price + self.atr_multiplier * current_atr
            stop_loss = max(
                current_price * (1 + self.stop_loss_pct),
                trailing_stop,
            )
            take_profit = current_price * (1 - self.take_profit_pct)

            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.SELL,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(stop_loss, 6),
                take_profit=round(take_profit, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Momentum SELL ({self.mode}): score={score:.3f}, "
                    f"ATR={current_atr:.4f}, trailing_stop={trailing_stop:.4f}"
                ),
                evidence={
                    "mode": self.mode,
                    "score": round(score, 4),
                    "atr": round(float(current_atr), 4),
                    "trailing_stop": round(float(trailing_stop), 4),
                },
                factors=["momentum", self.mode],
            )

    def _ma_crossover_signal(self, data: pd.DataFrame) -> tuple[str, float]:
        """Generate signal from MA crossover.

        Bullish: fast MA crosses above slow MA.
        Bearish: fast MA crosses below slow MA.

        Returns:
            Tuple of (direction, score).
        """
        close = data["close"]
        fast_ma = self.compute_ma(close, self.fast_period)
        slow_ma = self.compute_ma(close, self.slow_period)

        if len(fast_ma) < 2 or np.isnan(fast_ma.iloc[-1]) or np.isnan(slow_ma.iloc[-1]):
            return "flat", 0.0

        current_diff = fast_ma.iloc[-1] - slow_ma.iloc[-1]
        prev_diff = fast_ma.iloc[-2] - slow_ma.iloc[-2]

        # Crossover detection
        if prev_diff <= 0 and current_diff > 0:
            # Bullish crossover
            score = min(abs(current_diff) / (slow_ma.iloc[-1] + 1e-10) * 100, 1.0)
            return "long", max(score, 0.3)

        elif prev_diff >= 0 and current_diff < 0:
            # Bearish crossover
            score = min(abs(current_diff) / (slow_ma.iloc[-1] + 1e-10) * 100, 1.0)
            return "short", max(score, 0.3)

        # Trend continuation
        if current_diff > 0:
            score = min(abs(current_diff) / (slow_ma.iloc[-1] + 1e-10) * 50, 0.5)
            return "long", score
        elif current_diff < 0:
            score = min(abs(current_diff) / (slow_ma.iloc[-1] + 1e-10) * 50, 0.5)
            return "short", score

        return "flat", 0.0

    def _macd_signal(self, data: pd.DataFrame) -> tuple[str, float]:
        """Generate signal from MACD.

        Bullish: MACD line crosses above signal line.
        Bearish: MACD line crosses below signal line.

        Returns:
            Tuple of (direction, score).
        """
        close = data["close"]
        macd_line, signal_line, histogram = self.compute_macd(
            close, self.fast_period, self.slow_period, self.signal_period
        )

        if len(macd_line) < 2 or np.isnan(macd_line.iloc[-1]):
            return "flat", 0.0

        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]

        # Histogram crossover (MACD - signal)
        if prev_hist <= 0 and current_hist > 0:
            score = min(abs(current_hist) / (abs(macd_line.iloc[-1]) + 1e-10), 1.0)
            return "long", max(score, 0.3)

        elif prev_hist >= 0 and current_hist < 0:
            score = min(abs(current_hist) / (abs(macd_line.iloc[-1]) + 1e-10), 1.0)
            return "short", max(score, 0.3)

        # Trend continuation based on histogram
        if current_hist > 0:
            return "long", min(abs(current_hist) / (abs(macd_line.iloc[-1]) + 1e-10) * 0.5, 0.5)
        elif current_hist < 0:
            return "short", min(abs(current_hist) / (abs(macd_line.iloc[-1]) + 1e-10) * 0.5, 0.5)

        return "flat", 0.0
