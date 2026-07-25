"""GARCH volatility — volatility regime from GARCH(1,1)."""

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
class GARCHVolStrategy(Strategy):
    """GARCH vol — volatility regime from simplified GARCH(1,1)."""

    name = "garch_vol"
    description = "GARCH(1,1) volatility regime detection"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 50))
        self.mult: float = float(self._parameters.get("mult", 2.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.period + 10:
                return self._hold("Insufficient data")
            rets = c.pct_change().dropna().values[-self.period:]
            if len(rets) < 10:
                return self._hold("Insufficient returns")
            omega = np.var(rets) * 0.05
            alpha, beta = 0.1, 0.85
            sigma2 = np.var(rets)
            for r in rets:
                sigma2 = omega + alpha * r ** 2 + beta * sigma2
            garch_vol = np.sqrt(sigma2)
            hist_vol = np.std(rets)
            price = float(c.iloc[-1])
            if garch_vol > hist_vol * self.mult:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.HOLD,
                    confidence=0.6,
                    entry_price=round(price, 6),
                    reasoning=f"GARCH vol high: {garch_vol:.4f} > {hist_vol*self.mult:.4f}",
                    indicators={"garch_vol": round(garch_vol, 6), "hist_vol": round(hist_vol, 6)},
                )
            return self._hold(f"GARCH vol normal: {garch_vol:.4f}")
        except Exception as exc:
            logger.error("GARCHVol error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["GARCHVolStrategy"]
