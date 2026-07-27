"""DXY momentum — trades based on dollar index correlation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class DXYMomentumStrategy(Strategy):
    """DXY momentum — trades based on dollar index correlation."""

    name = "dxy_momentum"
    description = "DXY momentum: US dollar index correlation signal"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 20))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.lookback + 5:
                return self._hold("Insufficient data")
            ret = float(c.iloc[-1]) / float(c.iloc[-self.lookback]) - 1.0
            price = float(c.iloc[-1])
            if ret > 0.02:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"DXY bullish: {ret*100:.1f}% over {self.lookback} periods",
                    indicators={"ret": round(ret, 4)},
                )
            if ret < -0.02:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"DXY bearish: {ret*100:.1f}% over {self.lookback} periods",
                    indicators={"ret": round(ret, 4)},
                )
            return self._hold(f"DXY neutral: {ret*100:.1f}%")
        except Exception as exc:
            logger.error("DXYMomentum error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["DXYMomentumStrategy"]
