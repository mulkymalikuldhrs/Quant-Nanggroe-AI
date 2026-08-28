"""Mean Reversion Strategy (Stochastic) — QNA-compatible port."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class MeanReversionStrategy(Strategy):
    """Legacy-compatible wrapper for MeanReversion strategy.

    Accepts legacy `params` dict, provides `required_columns`, `warmup_period`,
    and `estimate_half_life`. Returns ``None`` for insufficient data to match older
    test expectations.
    """
    def __init__(self, parameters: Optional[StrategyParameters] = None, *, params: Optional[Dict] = None, name: str = "MeanReversion") -> None:
        # Support legacy signature: params dict and name.
        if params is not None:
            # Legacy usage – wrap provided dict.
            parameters = StrategyParameters(params)
            self.name = name
            self.params = params
        else:
            # Modern usage – keep original default name.
            parameters = parameters or StrategyParameters()
            self.name = "mean_rev"
            self.params = {}
        # Ensure default params exist.
        if not parameters.get("k_period"):
            parameters.set("k_period", 14)
        if not parameters.get("d_period"):
            parameters.set("d_period", 5)
        if not parameters.get("oversold"):
            parameters.set("oversold", 25)
        if not parameters.get("overbought"):
            parameters.set("overbought", 75)
        super().__init__(parameters=parameters)

    def required_columns(self) -> list:
        # Legacy required columns.
        return ["high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        # Legacy warmup: lookback (default 30) + 10
        lookback = int(self._parameters.get("lookback", 30))
        return lookback + 10

    def estimate_half_life(self, series: pd.Series) -> float:
        """Estimate half‑life of mean reversion using OU approximation.

        Mirrors the logic used in the original back‑test scripts.
        """
        close = series.values
        n = len(close)
        window = 60
        half_life_vals = []
        for i in range(window, n):
            prices = close[i - window : i]
            spread = prices - np.mean(prices)
            lag = spread[:-1]
            diff = np.diff(spread)
            if len(lag) > 2 and np.std(lag) > 0:
                beta = np.polyfit(lag, diff, 1)[0]
                hl = -np.log(2) / beta if beta < 0 else 999
                if 0 < hl < 30:
                    half_life_vals.append(hl)
        return np.mean(half_life_vals) if half_life_vals else np.nan

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        # Legacy behavior: return None when data insufficient.
        try:
            if not hasattr(data, "iloc"):
                return None
            df = data.copy()
            lookback = int(self._parameters.get("lookback", 30))
            min_len = lookback + 10
            if len(df) < min_len:
                return None
            # Use original logic.
            h, l, c = df["high"], df["low"], df["close"]
            kp = int(self._parameters.get("k_period", 14))
            dp = int(self._parameters.get("d_period", 3))
            os_ = float(self._parameters.get("oversold", 20))
            ob_ = float(self._parameters.get("overbought", 80))

            # ATR for SL/TP calculation
            tr = pd.concat([
                h - l,
                (h - c.shift(1)).abs(),
                (l - c.shift(1)).abs()
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()

            low_k = l.rolling(kp).min()
            high_k = h.rolling(kp).max()
            stoch_k = 100 * (c - low_k) / (high_k - low_k)
            stoch_d = stoch_k.rolling(dp).mean()

            last = -1
            k = stoch_k.values[last]
            d = stoch_d.values[last]
            close_price = float(c.values[last])
            atr_val = float(atr.iloc[last]) if not pd.isna(atr.iloc[last]) else close_price * 0.01

            if k < os_ and k > d:
                sl = close_price - 1.0 * atr_val
                tp = close_price + 3.0 * atr_val
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=close_price,
                    stop_loss=sl,
                    take_profit=tp,
                    reasoning=f"MeanRev: stochastic oversold ({k:.1f}) K crossed above D",
                    indicators={"stoch_k": float(k), "stoch_d": float(d), "atr": atr_val},
                )
            if k > ob_ and k < d:
                sl = close_price + 1.0 * atr_val
                tp = close_price - 3.0 * atr_val
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=close_price,
                    stop_loss=sl,
                    take_profit=tp,
                    reasoning=f"MeanRev: stochastic overbought ({k:.1f}) K crossed below D",
                    indicators={"stoch_k": float(k), "stoch_d": float(d), "atr": atr_val},
                )
            return None
        except Exception as e:  # pragma: no cover
            logger.debug("MeanRev error: %s", e)
            return None

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )

    """Mean Reversion via Stochastic Oscillator."""

    name = "mean_rev"
    description = "Mean Reversion: Stochastic %K/%D crossover"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("k_period"):
            params.set("k_period", 14)
        if not params.get("d_period"):
            params.set("d_period", 5)
        if not params.get("oversold"):
            params.set("oversold", 25)
        if not params.get("overbought"):
            params.set("overbought", 75)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 30:
                return self._hold("Insufficient data")
            h, l, c = df["high"], df["low"], df["close"]
            kp = int(self._parameters.get("k_period", 14))
            dp = int(self._parameters.get("d_period", 3))
            os_ = float(self._parameters.get("oversold", 20))
            ob_ = float(self._parameters.get("overbought", 80))

            # ATR for SL/TP calculation
            tr = pd.concat([
                h - l,
                (h - c.shift(1)).abs(),
                (l - c.shift(1)).abs()
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()

            low_k = l.rolling(kp).min()
            high_k = h.rolling(kp).max()
            stoch_k = 100 * (c - low_k) / (high_k - low_k)
            stoch_d = stoch_k.rolling(dp).mean()

            last = -1
            k = stoch_k.values[last]
            d = stoch_d.values[last]
            close = float(c.values[last])
            atr_val = float(atr.iloc[last]) if not pd.isna(atr.iloc[last]) else close * 0.01

            if k < os_ and k > d:
                sl = close - 1.0 * atr_val
                tp = close + 3.0 * atr_val
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    reasoning=f"MeanRev: stochastic oversold ({k:.1f}) K crossed above D",
                    indicators={"stoch_k": float(k), "stoch_d": float(d), "atr": atr_val},
                )
            if k > ob_ and k < d:
                sl = close + 1.0 * atr_val
                tp = close - 3.0 * atr_val
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    entry_price=close,
                    stop_loss=sl,
                    take_profit=tp,
                    reasoning=f"MeanRev: stochastic overbought ({k:.1f}) K crossed below D",
                    indicators={"stoch_k": float(k), "stoch_d": float(d), "atr": atr_val},
                )
            return self._hold("No stochastic signal")
        except Exception as e:  # pragma: no cover
            logger.debug("MeanRev error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["MeanReversionStrategy"]
