"""DMI — Directional Movement Index trend strength."""

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
class DMIStrategy(Strategy):
    """Directional Movement Index — +DI/-DI crossover."""

    name = "dmi"
    description = "Directional Movement Index: +DI/-DI crossover"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 14))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            h, l, c = data["high"], data["low"], data["close"]
            if len(c) < self.period * 2 + 5:
                return self._hold("Insufficient data")
            up = h.diff()
            down = -l.diff()
            p_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=h.index)
            n_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=h.index)
            tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            atr = tr.rolling(self.period).mean()
            p_di = 100 * p_dm.rolling(self.period).mean() / (atr + 1e-10)
            n_di = 100 * n_dm.rolling(self.period).mean() / (atr + 1e-10)
            if np.isnan(p_di.iloc[-1]) or np.isnan(n_di.iloc[-1]):
                return self._hold("DMI not ready")
            pdi, ndi = float(p_di.iloc[-1]), float(n_di.iloc[-1])
            price = float(c.iloc[-1])
            if pdi > ndi:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"+DI {pdi:.1f} > -DI {ndi:.1f}",
                    indicators={"+DI": round(pdi, 2), "-DI": round(ndi, 2)},
                )
            if ndi > pdi:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"-DI {ndi:.1f} > +DI {pdi:.1f}",
                    indicators={"+DI": round(pdi, 2), "-DI": round(ndi, 2)},
                )
            return self._hold("DMI neutral")
        except Exception as exc:
            logger.error("DMI error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["DMIStrategy"]
