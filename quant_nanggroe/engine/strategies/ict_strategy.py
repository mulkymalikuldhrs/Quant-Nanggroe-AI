"""ICT — Inner Circle Trader concepts: FVG, OB, displacement."""

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
class ICTStrategy(Strategy):
    """ICT — Inner Circle Trader: FVG, order block, displacement.

    Supports modes: fvg, order_block, displacement, all.
    """

    name = "ict_strategy"
    description = "ICT: FVG, order block, displacement, all"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.mode: str = str(self._parameters.get("mode", "fvg"))
        self.lookback: int = int(self._parameters.get("lookback", 50))
        self.min_gap_pct: float = float(self._parameters.get("min_gap_pct", 0.002))
        self.ob_window: int = int(self._parameters.get("ob_window", 5))
        self.disp_threshold: float = float(self._parameters.get("disp_threshold", 0.03))

    def _fvg_signal(self, data: pd.DataFrame, price: float, symbol: str) -> Optional[StrategySignal]:
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        for i in range(min(10, len(data) - 2)):
            if l.iloc[i + 1] > h.iloc[i] and l.iloc[i + 1] > h.iloc[i + 2]:
                gap = (l.iloc[i + 1] - h.iloc[i]) / h.iloc[i]
                if gap > self.min_gap_pct:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=symbol,
                        direction=SignalDirection.SELL,
                        confidence=0.6,
                        entry_price=round(price, 6),
                        reasoning=f"FVG: bullish gap above {i} bars back",
                        indicators={"pattern": "fvg_bullish", "gap": round(gap, 4)},
                    )
            if h.iloc[i + 1] < l.iloc[i] and h.iloc[i + 1] < l.iloc[i + 2]:
                gap = (l.iloc[i] - h.iloc[i + 1]) / h.iloc[i + 1]
                if gap > self.min_gap_pct:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=symbol,
                        direction=SignalDirection.BUY,
                        confidence=0.6,
                        entry_price=round(price, 6),
                        reasoning=f"FVG: bearish gap below {i} bars back",
                        indicators={"pattern": "fvg_bearish", "gap": round(gap, 4)},
                    )
        return None

    def _order_block_signal(self, data: pd.DataFrame, price: float, symbol: str) -> Optional[StrategySignal]:
        h = data["high"]
        l = data["low"]
        c = data["close"]
        strength = 0.0
        for i in range(min(self.lookback, len(data) - self.ob_window - 1)):
            block_move = abs(float(h.iloc[i + self.ob_window]) - float(l.iloc[i]))
            subsequent_move = abs(float(c.iloc[i + self.ob_window + 3]) - float(c.iloc[i + self.ob_window]))
            if subsequent_move > block_move * 0.5:
                strength = subsequent_move / (block_move + 1e-10)
                if c.iloc[i] > c.iloc[i - 1] and h.iloc[i] > h.iloc[i - 1]:
                    if price < h.iloc[i]:
                        return StrategySignal(
                            strategy_name=self.name,
                            symbol=symbol,
                            direction=SignalDirection.SELL,
                            confidence=0.55,
                            entry_price=round(price, 6),
                            reasoning="ICT order block SELL",
                            indicators={"pattern": "order_block", "strength": round(strength, 2)},
                        )
                elif c.iloc[i] < c.iloc[i - 1] and l.iloc[i] < l.iloc[i - 1]:
                    if price > l.iloc[i]:
                        return StrategySignal(
                            strategy_name=self.name,
                            symbol=symbol,
                            direction=SignalDirection.BUY,
                            confidence=0.55,
                            entry_price=round(price, 6),
                            reasoning="ICT order block BUY",
                            indicators={"pattern": "order_block", "strength": round(strength, 2)},
                        )
        return None

    def _displacement_signal(self, data: pd.DataFrame, price: float, symbol: str) -> Optional[StrategySignal]:
        o, h, l, c = data["open"], data["high"], data["low"], data["close"]
        if len(c) < 5:
            return None
        ret = float(c.iloc[-1]) / float(c.iloc[-5]) - 1.0
        vol = float(data["volume"].iloc[-5:].std())
        avg_vol = float(data["volume"].iloc[-20:].mean()) if len(data["volume"]) >= 20 else 1.0
        if abs(ret) > self.disp_threshold and vol > avg_vol * 1.5:
            if ret > 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=symbol,
                    direction=SignalDirection.BUY,
                    confidence=0.55,
                    entry_price=round(price, 6),
                    reasoning=f"ICT displacement: {ret*100:.2f}% move with volume",
                    indicators={"pattern": "displacement_bullish", "ret": round(ret, 4), "vol_ratio": round(vol / (avg_vol + 1e-10), 2)},
                )
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=0.55,
                entry_price=round(price, 6),
                reasoning=f"ICT displacement: {ret*100:.2f}% move with volume",
                indicators={"pattern": "displacement_bearish", "ret": round(ret, 4), "vol_ratio": round(vol / (avg_vol + 1e-10), 2)},
            )
        return None

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            if len(data) < self.lookback:
                return self._hold("Insufficient data")
            price = float(data["close"].iloc[-1])
            symbol = kwargs.get("symbol", "")

            if self.mode == "fvg":
                sig = self._fvg_signal(data, price, symbol)
            elif self.mode == "order_block":
                sig = self._order_block_signal(data, price, symbol)
            elif self.mode == "displacement":
                sig = self._displacement_signal(data, price, symbol)
            elif self.mode == "all":
                sig = self._fvg_signal(data, price, symbol)
                if sig is None:
                    sig = self._order_block_signal(data, price, symbol)
                if sig is None:
                    sig = self._displacement_signal(data, price, symbol)
            else:
                sig = None

            if sig is not None:
                return sig
            return self._hold(f"No ICT signal in mode={self.mode}")
        except Exception as exc:
            logger.error("ICT error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["ICTStrategy"]
