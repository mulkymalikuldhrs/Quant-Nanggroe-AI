"""Adaptive Moving Average — adjusts to market volatility."""

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
class AdaptiveMovingAverageStrategy(Strategy):
    """Adaptive MA — adjusts to market volatility."""

    name = "adaptive_moving_average"
    description = "Adaptive MA: adjusts period to market volatility"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 10))
        self.min_period: int = int(self._parameters.get("min_period", 2))
        self.max_period: int = int(self._parameters.get("max_period", 30))

    @staticmethod
    def _compute_sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period, min_periods=period).mean()

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data or not a DataFrame")
            c = data["close"]
            if len(c) < self.max_period + 5:
                return self._hold("Insufficient data")
            rets = c.pct_change().dropna().values[-self.max_period * 2:]
            if len(rets) < self.max_period:
                return self._hold("Insufficient returns data")
            vol = np.std(rets)
            vol_rank = np.clip(vol / (np.mean(np.abs(rets)) + 1e-10), 0, 1)
            adaptive_period = int(self.max_period - (self.max_period - self.min_period) * vol_rank)
            adaptive_period = max(adaptive_period, self.min_period)
            ama = self._compute_sma(c, adaptive_period)
            if np.isnan(ama.iloc[-1]):
                return self._hold("AMA not ready")
            price = float(c.iloc[-1])
            ama_val = float(ama.iloc[-1])
            if np.isnan(ama_val):
                return self._hold("AMA not ready")
            # ── TREND STRENGTH FILTER (Phase-Improve: only trade real trends) ──
            # Compute ADX-like trend strength to avoid churning in ranges
            diff = c.diff()
            up = diff.clip(lower=0).rolling(14).sum()
            dn = (-diff.clip(upper=0)).rolling(14).sum()
            plus_dm = up.rolling(14).mean()
            minus_dm = dn.rolling(14).mean()
            atr = (c.diff().abs()).rolling(14).mean()
            dx = np.abs(plus_dm - minus_dm) / (plus_dm + minus_dm + 1e-10)
            adx = dx.rolling(14).mean().iloc[-1] if len(dx) > 14 else 0.0
            # Gap fix: only trade when ADX > 20 (real trend), else HOLD
            if adx < 20.0:
                return self._hold(f"Weak trend (ADX={adx:.1f} < 20) — stay flat", {"adx": round(float(adx), 2)})
            is_buy = price > ama_val
            strength = np.clip((adx - 20) / 30.0, 0.1, 0.95)
            direction = SignalDirection.BUY if is_buy else SignalDirection.SELL
            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                confidence=round(float(strength), 2),
                entry_price=round(price, 6),
                reasoning=f"{'Price above' if is_buy else 'Price below'} adaptive MA ({adaptive_period}), ADX={adx:.1f}",
                indicators={"adaptive_period": adaptive_period, "ama": round(ama_val, 4), "adx": round(float(adx), 2)},
            )
        except Exception as exc:
            logger.error("AdaptiveMovingAverage error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["AdaptiveMovingAverageStrategy"]
