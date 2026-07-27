"""Entropy-based randomness detection."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class EntropyStrategy(Strategy):
    """Entropy — randomness / predictability detection."""

    name = "entropy"
    description = "Entropy: randomness / predictability in returns"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.period: int = int(self._parameters.get("period", 20))
        self.bins: int = int(self._parameters.get("bins", 10))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.period + 5:
                return self._hold("Insufficient data")
            rets = c.pct_change().dropna().values[-self.period:]
            if len(rets) < self.bins:
                return self._hold("Insufficient returns")
            hist, _ = np.histogram(rets, bins=self.bins)
            probs = hist / (hist.sum() + 1e-10)
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            max_entropy = np.log(self.bins)
            norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
            price = float(c.iloc[-1])
            if norm_entropy < 0.5:
                ret = float(c.iloc[-1]) / float(c.iloc[-5]) - 1.0
                sig = 1.0 if ret > 0 else -1.0
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY if sig > 0 else SignalDirection.SELL,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning=f"Entropy {norm_entropy:.2f} < 0.5: structured movement",
                    indicators={"entropy": round(norm_entropy, 4)},
                )
            return self._hold(f"Entropy {norm_entropy:.2f}: random market")
        except Exception as exc:
            logger.error("Entropy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["EntropyStrategy"]
