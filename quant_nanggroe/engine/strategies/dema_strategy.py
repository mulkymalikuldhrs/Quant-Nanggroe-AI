"""Double EMA — double-smooth trend filtering."""

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
class DEMAStrategy(Strategy):
    """Double EMA — double-smooth trend filtering."""

    name = "dema"
    description = "Double EMA: double-smooth trend filtering"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 14))

    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, min_periods=period, adjust=False).mean()

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.period * 3 + 5:
                return self._hold("Insufficient data")
            ema1 = self._ema(c, self.period)
            ema2 = self._ema(ema1, self.period)
            dema = 2 * ema1 - ema2
            price = float(c.iloc[-1])
            dema_val = float(dema.iloc[-1])
            if np.isnan(dema_val):
                return self._hold("DEMA not ready")
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
            is_buy = price > dema_val
            strength = np.clip((adx - 20) / 30.0, 0.1, 0.95)
            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=SignalDirection.BUY if is_buy else SignalDirection.SELL,
                confidence=round(strength, 2),
                entry_price=round(price, 6),
                reasoning=f"{'Price above' if is_buy else 'Price below'} DEMA, ADX={adx:.1f}",
                indicators={"dema": round(dema_val, 4), "adx": round(adx, 2)},
            )
        except Exception as exc:
            logger.error("DEMA error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["DEMAStrategy"]
