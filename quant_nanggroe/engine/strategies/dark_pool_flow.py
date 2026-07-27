"""Dark pool flow proxy via block trade detection."""

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
class DarkPoolFlowStrategy(Strategy):
    """Dark pool flow proxy via block trade detection (large prints)."""

    name = "dark_pool_flow"
    description = "Dark pool flow: block trade volume spike detection"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 20))
        self.vol_mult: float = float(self._parameters.get("vol_mult", 3.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c, v = data["close"], data["volume"]
            if len(c) < self.lookback + 5:
                return self._hold("Insufficient data")
            avg_vol = float(v.iloc[-self.lookback:-1].mean())
            cur_vol = float(v.iloc[-2])
            prev_vol = float(v.iloc[-3]) if len(v) > 3 else 0
            price = float(c.iloc[-1])
            ret = float(c.iloc[-1]) / float(c.iloc[-2]) - 1.0
            if cur_vol > avg_vol * self.vol_mult and prev_vol < avg_vol * 1.5:
                if ret > 0:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.BUY,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning="Dark pool: block buy detected",
                        indicators={"vol_ratio": round(float(cur_vol / avg_vol), 2), "return": round(float(ret), 4)},
                    )
                if ret < 0:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning="Dark pool: block sell detected",
                        indicators={"vol_ratio": round(float(cur_vol / avg_vol), 2), "return": round(float(ret), 4)},
                    )
            return self._hold("No dark pool signal")
        except Exception as exc:
            logger.error("DarkPoolFlow error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["DarkPoolFlowStrategy"]
