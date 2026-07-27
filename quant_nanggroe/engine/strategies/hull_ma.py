"""Hull Moving Average — smoother and faster MA."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class HullMAStrategy(Strategy):
    """Hull Moving Average — smoother and faster MA."""

    name = "hull_ma"
    description = "Hull MA: smooth, responsive moving average"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 14))

    @staticmethod
    def _wma(series: pd.Series, period: int) -> pd.Series:
        weights = np.arange(1, period + 1)
        return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.period * 3 + 5:
                return self._hold("Insufficient data")
            sqrt_period = int(np.sqrt(self.period))
            wma_half = self._wma(c, self.period // 2)
            wma_full = self._wma(c, self.period)
            hull = 2 * wma_half - wma_full
            hull_smooth = self._wma(hull, sqrt_period)
            hull_val = float(hull_smooth.iloc[-1])
            if np.isnan(hull_val):
                return self._hold("Hull MA not ready")
            # ── TREND STRENGTH FILTER (Phase-Improve) ──
            diff = c.diff()
            up = diff.clip(lower=0).rolling(14).sum()
            dn = (-diff.clip(upper=0)).rolling(14).sum()
            plus_dm = up.rolling(14).mean()
            minus_dm = dn.rolling(14).mean()
            dx = np.abs(plus_dm - minus_dm) / (plus_dm + minus_dm + 1e-10)
            adx = float(dx.rolling(14).mean().iloc[-1]) if len(dx) > 14 else 0.0
            if adx < 20.0:
                return self._hold(f"Weak trend (ADX={adx:.1f} < 20) — stay flat", {"adx": round(adx, 2)})
            is_buy = price > hull_val
            strength = np.clip((adx - 20) / 30.0, 0.1, 0.95)
            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=SignalDirection.BUY if is_buy else SignalDirection.SELL,
                confidence=round(strength, 2),
                entry_price=round(price, 6),
                reasoning=f"{'Price above' if is_buy else 'Price below'} Hull MA, ADX={adx:.1f}",
                indicators={"hull": round(hull_val, 4), "adx": round(adx, 2)},
            )
        except Exception as exc:
            logger.error("HullMA error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["HullMAStrategy"]
