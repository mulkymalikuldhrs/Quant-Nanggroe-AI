"""EMA + ADX Strategy — QNA-compatible port."""

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
class EMAADXStrategy(Strategy):
    """EMA crossover dengan ADX trend filter."""

    name = "ema_adx"
    description = "EMA + ADX: hanya trading saat trend kuat"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("fast"):
            params.set("fast", 12)
        if not params.get("slow"):
            params.set("slow", 26)
        if not params.get("adx_period"):
            params.set("adx_period", 14)
        if not params.get("adx_threshold"):
            params.set("adx_threshold", 25)
        super().__init__(parameters=params)

    def _adx(self, h, l, c, period):
        tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        plus_dm = (h - h.shift(1)).clip(lower=0)
        minus_dm = (l.shift(1) - l).clip(lower=0)
        plus_di = 100 * (plus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        minus_di = 100 * (minus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).clip(lower=0.001)
        return dx.rolling(period).mean()

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc"):
                return self._hold("No DataFrame")
            df = data.copy()
            if len(df) < 30:
                return self._hold("Insufficient data")
            h, l, c = df["high"], df["low"], df["close"]
            fast = int(self._parameters.get("fast", 12))
            slow = int(self._parameters.get("slow", 26))
            adx_p = int(self._parameters.get("adx_period", 14))
            adx_t = float(self._parameters.get("adx_threshold", 25))

            ema_f = c.ewm(span=fast).mean()
            ema_s = c.ewm(span=slow).mean()
            adx = self._adx(h, l, c, adx_p)

            last = -1
            close = float(c.values[last])
            trend = adx.values[last] > adx_t

            if trend and ema_f.values[last] > ema_s.values[last]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    strength=SignalStrength.STRONG if adx.values[last] > adx_t * 1.5 else SignalStrength.MODERATE,
                    confidence=min(0.85, 0.5 + adx.values[last] / 200),
                    entry_price=close,
                    reasoning=f"EMA+ADX: bullish cross, ADX={adx.values[last]:.1f}",
                    indicators={"adx": float(adx.values[last]), "ema_f": float(ema_f.values[last])},
                )
            if trend and ema_f.values[last] < ema_s.values[last]:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    strength=SignalStrength.STRONG if adx.values[last] > adx_t * 1.5 else SignalStrength.MODERATE,
                    confidence=min(0.85, 0.5 + adx.values[last] / 200),
                    entry_price=close,
                    reasoning=f"EMA+ADX: bearish cross, ADX={adx.values[last]:.1f}",
                    indicators={"adx": float(adx.values[last]), "ema_f": float(ema_f.values[last])},
                )
            return self._hold("No EMA+ADX signal")
        except Exception as e:  # pragma: no cover
            logger.debug("EMAADX error: %s", e)
            return self._hold(f"Error: {e}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["EMAADXStrategy"]
