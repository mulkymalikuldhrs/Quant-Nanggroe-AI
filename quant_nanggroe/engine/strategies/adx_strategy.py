"""ADX trend strength — trade direction when ADX > threshold."""

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
class ADXStrategy(Strategy):
    """ADX trend strength — trade direction when ADX > threshold."""

    name = "adx"
    description = "ADX trend strength with +DI/-DI direction"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 14))
        self.threshold: float = float(self._parameters.get("threshold", 25.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.period * 2:
                return self._hold("Insufficient data")
            up = h.diff()
            down = -l.diff()
            p_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=h.index)
            n_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=h.index)
            tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            atr = tr.rolling(self.period).mean()
            p_di = 100 * p_dm.rolling(self.period).mean() / (atr + 1e-10)
            n_di = 100 * n_dm.rolling(self.period).mean() / (atr + 1e-10)
            dx = 100 * (p_di - n_di).abs() / (p_di + n_di + 1e-10)
            adx = dx.rolling(self.period).mean()
            if np.isnan(adx.iloc[-1]):
                return self._hold("ADX not ready")
            adx_val = float(adx.iloc[-1])
            price = float(c.iloc[-1])
            if adx_val > self.threshold:
                sig = 1.0 if float(p_di.iloc[-1]) > float(n_di.iloc[-1]) else -1.0
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY if sig > 0 else SignalDirection.SELL,
                    confidence=min((adx_val - self.threshold) / 50, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"ADX {adx_val:.1f} > {self.threshold}, trending",
                    indicators={"adx": round(adx_val, 2), "p_di": round(float(p_di.iloc[-1]), 2), "n_di": round(float(n_di.iloc[-1]), 2)},
                )
            return self._hold(f"ADX {adx_val:.1f} below threshold")
        except Exception as exc:
            logger.error("ADX error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["ADXStrategy"]
