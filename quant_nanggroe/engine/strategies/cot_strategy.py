"""COT-based trading strategy using Commitment of Traders data."""

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
class COTStrategy(Strategy):
    """Trades based on Commitment of Traders positioning analysis.

    Uses COT index percentile to identify extreme sentiment.
    """

    name = "cot"
    description = "Commitment of Traders positioning analysis"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.extreme_buy: float = float(self._parameters.get("extreme_buy_threshold", 20))
        self.extreme_sell: float = float(self._parameters.get("extreme_sell_threshold", 80))
        self.div_period: int = int(self._parameters.get("divergence_period", 10))

    def _load_cot(self, data: pd.DataFrame) -> Optional[Dict]:
        try:
            from quant_nanggroe.engine.data.cot_provider import COTAnalyzer, COTProvider
            provider = COTProvider()
            provider.fetch()
            analyzer = COTAnalyzer(provider)
            return analyzer.generate_signal("ES", price_series=data["close"])
        except Exception:
            return None

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty or len(data) < 52:
                return self._hold("No or insufficient data")
            cot = self._load_cot(data)
            if not cot or cot["signal"] == "neutral":
                return self._hold("COT neutral or unavailable")
            latest_price = float(data["close"].iloc[-1])
            atr_val = float(data["high"].iloc[-20:].max() - data["low"].iloc[-20:].min()) / 20.0
            confidence = float(cot["confidence"])
            if cot["signal"] == "buy":
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY,
                    confidence=confidence,
                    entry_price=latest_price,
                    stop_loss=latest_price - atr_val * 2,
                    take_profit=latest_price + atr_val * 4,
                    reasoning=str(cot["reasoning"]),
                    indicators={"cot_signal": "buy"},
                )
            elif cot["signal"] == "sell":
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.SELL,
                    confidence=confidence,
                    entry_price=latest_price,
                    stop_loss=latest_price + atr_val * 2,
                    take_profit=latest_price - atr_val * 4,
                    reasoning=str(cot["reasoning"]),
                    indicators={"cot_signal": "sell"},
                )
            return self._hold("COT no signal")
        except Exception as exc:
            logger.error("COT error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["COTStrategy"]
