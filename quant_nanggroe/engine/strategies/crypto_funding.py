"""Crypto Funding — momentum-based crypto strategy."""

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
class CryptoFundingStrategy(Strategy):
    """Crypto funding momentum strategy."""

    name = "crypto_funding"
    description = "Crypto momentum: fast/slow return comparison"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.fast: int = int(self._parameters.get("fast", 8))
        self.slow: int = int(self._parameters.get("slow", 24))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.slow + 5:
                return self._hold("Insufficient data")
            fast_ret = float(c.iloc[-1]) / float(c.iloc[-self.fast]) - 1.0
            slow_ret = float(c.iloc[-1]) / float(c.iloc[-self.slow]) - 1.0
            price = float(c.iloc[-1])
            if fast_ret > 0.02 and slow_ret > 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Crypto funding positive: fast momentum up",
                    indicators={"fast_ret": round(float(fast_ret), 4), "slow_ret": round(float(slow_ret), 4)},
                )
            if fast_ret < -0.02 and slow_ret < 0:
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=0.5,
                    entry_price=round(price, 6),
                    reasoning="Crypto funding negative: fast momentum down",
                    indicators={"fast_ret": round(float(fast_ret), 4), "slow_ret": round(float(slow_ret), 4)},
                )
            return self._hold(f"Crypto funding neutral: fast={fast_ret:.4f} slow={slow_ret:.4f}")
        except Exception as exc:
            logger.error("CryptoFunding error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["CryptoFundingStrategy"]
