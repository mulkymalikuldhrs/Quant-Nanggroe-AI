"""MSNR Strategy — Malaysian Support & Resistance (storyline-driven SMC + PA).

QNA-compatible port of the Hedge Fund registry strategy.
Returns a ``StrategySignal`` (not a DataFrame column) so it wires into
``engine_production_bridge.generate_signals`` and the ``StrategyRegistry``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
class MSNRStrategy(Strategy):
    """Malaysian Support & Resistance — hybrid SMC + price action."""

    name = "msnr"
    description = "MSNR: Hybrid SMC + Price Action, storyline-driven"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 20)
        if not params.get("breakout_mult"):
            params.set("breakout_mult", 1.5)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 30:
                return self._hold("Insufficient data")
            h, l, c = df["high"], df["low"], df["close"]
            lookback = int(self._parameters.get("lookback", 20))

            hh = h.rolling(lookback).max()
            ll = l.rolling(lookback).min()
            rng = hh - ll

            # ATR for SL/TP calculation
            tr = pd.concat([
                h - l,
                (h - c.shift(1)).abs(),
                (l - c.shift(1)).abs()
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()

            last = -1
            break_up = c.iloc[last] > hh.iloc[last - 1] and rng.iloc[last] > 0
            break_dn = c.iloc[last] < ll.iloc[last - 1] and rng.iloc[last] > 0

            if break_up:
                entry = float(c.iloc[last])
                atr_val = float(atr.iloc[last]) if not pd.isna(atr.iloc[last]) else entry * 0.01
                sl = entry - 1.5 * atr_val
                tp = entry + 3.0 * atr_val
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=0.55,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    reasoning="MSNR: close broke above recent HH (bullish S/R breakout)",
                    indicators={"hh": float(hh.iloc[last]), "ll": float(ll.iloc[last]), "atr": atr_val},
                )
            if break_dn:
                entry = float(c.iloc[last])
                atr_val = float(atr.iloc[last]) if not pd.isna(atr.iloc[last]) else entry * 0.01
                sl = entry + 1.5 * atr_val
                tp = entry - 3.0 * atr_val
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=0.55,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    reasoning="MSNR: close broke below recent LL (bearish S/R breakout)",
                    indicators={"hh": float(hh.iloc[last]), "ll": float(ll.iloc[last]), "atr": atr_val},
                )
            return self._hold("No S/R breakout")
        except Exception as e:  # pragma: no cover
            logger.debug("MSNR error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["MSNRStrategy"]
