"""AMDX / XAMD Strategy — QNA-compatible port."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
class AMDXStrategy(Strategy):
    """AMDX/XAMD — Market Profile open/close relationship."""

    name = "amdx"
    description = "AMDX/XAMD: market profile open-drive-close"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 8)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 5:
                return self._hold("Insufficient data")
            o, h, l, c = df["open"], df["high"], df["low"], df["close"]
            last = -1

            open_type = 0
            if o.values[last] > c.values[last - 1]:
                open_type = 1
            elif o.values[last] < c.values[last - 1]:
                open_type = -1

            close = float(c.values[last])
            prev_close = float(c.values[last - 1])

            # Buy: gap down + close above open + close above prev close
            if open_type == -1 and c.values[last] > o.values[last] and c.values[last] > prev_close:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.55,
                    entry_price=close,
                    reasoning="AMDX: gap-down filled, close reclaims open + prior close",
                    indicators={"open_type": open_type},
                )
            # Sell: gap up + close below open + close below prev close
            if open_type == 1 and c.values[last] < o.values[last] and c.values[last] < prev_close:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=0.55,
                    entry_price=close,
                    reasoning="AMDX: gap-up filled, close rejects open + prior close",
                    indicators={"open_type": open_type},
                )
            return self._hold("No AMDX setup")
        except Exception as e:  # pragma: no cover
            logger.debug("AMDX error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["AMDXStrategy"]
