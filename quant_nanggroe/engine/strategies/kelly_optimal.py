"""Kelly Optimal — position sizing via Kelly criterion."""

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
class KellyOptimalStrategy(Strategy):
    """Kelly Optimal — position sizing via Kelly criterion."""

    name = "kelly_optimal"
    description = "Kelly optimal: position sizing via Kelly criterion"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 50))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.lookback + 5:
                return self._hold("Insufficient data")
            rets = c.pct_change().dropna().values[-self.lookback:]
            if len(rets) < 10:
                return self._hold("Insufficient returns")
            wins = rets[rets > 0]
            losses = rets[rets < 0]
            if len(wins) > 0 and len(losses) > 0:
                w = len(wins) / len(rets)
                avg_win = float(wins.mean())
                avg_loss = abs(float(losses.mean())) if len(losses) > 0 else 1.0
                kelly = w - (1 - w) / (avg_win / (avg_loss + 1e-10) + 1e-10)
            else:
                kelly = 0.0
            price = float(c.iloc[-1])
            ret = float(c.iloc[-1]) / float(c.iloc[-3]) - 1.0
            if kelly > 0.05 and ret > 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=min(kelly, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"Kelly positive: {kelly:.3f}",
                    indicators={"kelly": round(kelly, 4)},
                )
            if kelly > 0.05 and ret < 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=min(kelly, 1.0),
                    entry_price=round(price, 6),
                    reasoning=f"Kelly positive short: {kelly:.3f}",
                    indicators={"kelly": round(kelly, 4)},
                )
            return self._hold(f"Kelly {kelly:.3f} too low")
        except Exception as exc:
            logger.error("KellyOptimal error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["KellyOptimalStrategy"]
