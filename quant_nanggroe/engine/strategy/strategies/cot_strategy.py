"""COT-based trading strategy using Commitment of Traders data."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class COTStrategy(BaseStrategy):
    """Trades based on Commitment of Traders positioning analysis.

    Parameters:
        extreme_buy_threshold (float): COT index below which is extreme bearish -> buy (default 20)
        extreme_sell_threshold (float): COT index above which is extreme bullish -> sell (default 80)
        divergence_period (int): Lookback for divergence detection (default 10)
    """

    def __init__(self, name: str = "COT", params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name, params)
        self.extreme_buy = params.get("extreme_buy_threshold", 20)
        self.extreme_sell = params.get("extreme_sell_threshold", 80)
        self.div_period = params.get("divergence_period", 10)
        self._cot_cache: Optional[Dict] = None

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return 52

    def _load_cot(self, data: pd.DataFrame) -> Optional[Dict]:
        from quant_nanggroe.engine.data.cot_provider import COTProvider, COTAnalyzer
        provider = COTProvider()
        provider.fetch()
        analyzer = COTAnalyzer(provider)
        return analyzer.generate_signal("ES", price_series=data["close"])

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        cot = self._load_cot(data)
        if not cot or cot["signal"] == "neutral":
            return None

        latest_price = float(data["close"].iloc[-1])
        atr = float(data["high"].iloc[-20:].max() - data["low"].iloc[-20:].min()) / 20.0
        confidence = cot["confidence"]

        if cot["signal"] == "buy":
            return Signal(
                symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=latest_price,
                stop_loss=latest_price - atr * 2,
                take_profit=latest_price + atr * 4,
                source_strategy=self.name,
                reasoning=cot["reasoning"],
            )
        elif cot["signal"] == "sell":
            return Signal(
                symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=latest_price,
                stop_loss=latest_price + atr * 2,
                take_profit=latest_price - atr * 4,
                source_strategy=self.name,
                reasoning=cot["reasoning"],
            )
        return None
