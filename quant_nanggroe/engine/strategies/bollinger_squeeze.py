"""Bollinger Band squeeze — low vol precedes breakout."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
class BollingerSqueezeStrategy(Strategy):
    """Bollinger Band squeeze — low vol precedes breakout."""

    name = "bollinger_squeeze"
    description = "Bollinger band squeeze: low volatility precedes breakout"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 20))
        self.squeeze_threshold: float = float(self._parameters.get("squeeze_threshold", 0.05))

    @staticmethod
    def _compute_bb(series: pd.Series, period: int, num_std: float = 2.0):
        middle = series.rolling(window=period, min_periods=period).mean()
        std = series.rolling(window=period, min_periods=period).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        return upper, middle, lower

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.period * 2 + 5:
                return self._hold("Insufficient data")
            upper, mid, lower = self._compute_bb(c, self.period)
            bbw = (upper - lower) / (mid + 1e-10)
            bbw_hist = bbw.dropna().values[-self.period:]
            if len(bbw_hist) < 5:
                return self._hold("Insufficient BBW data")
            cur_bbw = float(bbw.iloc[-1])
            bbw_rank = float((bbw_hist < cur_bbw).mean())
            price = float(c.iloc[-1])
            if bbw_rank < self.squeeze_threshold:
                ret = float(c.iloc[-1]) / float(c.iloc[-5]) - 1.0
                sig = 1.0 if ret > 0 else -1.0
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY if sig > 0 else SignalDirection.SELL,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning=f"Bollinger squeeze: BBW at {bbw_rank:.0%}",
                    indicators={"bbw": round(float(cur_bbw), 6), "bbw_rank": round(float(bbw_rank), 3)},
                )
            return self._hold(f"BBW rank {bbw_rank:.3f} above squeeze threshold")
        except Exception as exc:
            logger.error("BollingerSqueeze error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["BollingerSqueezeStrategy"]
