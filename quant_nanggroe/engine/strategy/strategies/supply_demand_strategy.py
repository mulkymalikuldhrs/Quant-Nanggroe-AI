"""Supply and Demand zone trading strategy.

Detects institutional supply/demand zones from rapid price movements
and generates signals on zone touches and breaks.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class SupplyDemandStrategy(BaseStrategy):
    """Supply and Demand zone strategy.

    Parameters:
        zone_lookback (int): Lookback for base detection (default 5)
        zone_pct (float): Zone thickness as % of price (default 0.003)
        min_strength (int): Min touches for valid zone (default 2)
        max_zone_age (int): Max bars before zone expires (default 100)
        require_volume (bool): Volume confirmation at zone creation (default True)
    """

    def __init__(self, name: str = "SnD", params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name, params)
        self.lookback = params.get("zone_lookback", 5)
        self.zone_pct = params.get("zone_pct", 0.003)
        self.min_strength = params.get("min_strength", 2)
        self.max_age = params.get("max_zone_age", 100)
        self.require_volume = params.get("require_volume", True)

    def required_columns(self) -> List[str]:
        cols = ["open", "high", "low", "close"]
        if self.require_volume:
            cols.append("volume")
        return cols

    def warmup_period(self) -> int:
        return 20

    def _find_demand_zones(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, vol: np.ndarray) -> List[Dict]:
        """Find demand zones — sharp rallies after basing periods."""
        zones = []
        for i in range(self.lookback, len(high) - 1):
            base_high = max(high[i-self.lookback:i])
            base_low = min(low[i-self.lookback:i])
            base_range = base_high - base_low
            base_body = abs(close[i] - close[i-self.lookback])
            if base_body < base_range * 0.3:
                continue
            rally = close[i+1] - close[i]
            rally_pct = rally / close[i]
            if rally_pct > 0.01 and base_range > 0:
                avg_vol = float(np.mean(vol[max(0,i-10):i+1])) if vol is not None else 1.0
                entry_vol = float(vol[i]) if vol is not None else 1.0
                zones.append({
                    "type": "demand",
                    "zone_high": base_high,
                    "zone_low": base_low,
                    "entry": i,
                    "strength": 1,
                    "volume_ratio": entry_vol / avg_vol if avg_vol > 0 else 1.0,
                })
        return zones

    def _find_supply_zones(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, vol: np.ndarray) -> List[Dict]:
        """Find supply zones — sharp drops after run-up periods."""
        zones = []
        for i in range(self.lookback, len(high) - 1):
            base_high = max(high[i-self.lookback:i])
            base_low = min(low[i-self.lookback:i])
            base_range = base_high - base_low
            base_body = abs(close[i] - close[i-self.lookback])
            if base_body < base_range * 0.3:
                continue
            drop = close[i] - close[i+1]
            drop_pct = drop / close[i]
            if drop_pct > 0.01 and base_range > 0:
                avg_vol = float(np.mean(vol[max(0,i-10):i+1])) if vol is not None else 1.0
                entry_vol = float(vol[i]) if vol is not None else 1.0
                zones.append({
                    "type": "supply",
                    "zone_high": base_high,
                    "zone_low": base_low,
                    "entry": i,
                    "strength": 1,
                    "volume_ratio": entry_vol / avg_vol if avg_vol > 0 else 1.0,
                })
        return zones

    def _update_strength(self, zones: List[Dict], high: np.ndarray, low: np.ndarray, current_idx: int) -> List[Dict]:
        """Update zone strength based on touches."""
        for z in zones:
            age = current_idx - z["entry"]
            if age > self.max_age:
                continue
            for i in range(z["entry"] + 1, current_idx + 1):
                if z["type"] == "demand" and low[i] <= z["zone_high"] >= low[i]:
                    z["strength"] += 1
                elif z["type"] == "supply" and high[i] >= z["zone_low"] <= high[i]:
                    z["strength"] += 1
        return [z for z in zones if z["strength"] >= self.min_strength and (current_idx - z["entry"]) <= self.max_age]

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        high = data["high"].values
        low = data["low"].values
        close = data["close"].values
        vol = data["volume"].values if self.require_volume else None

        demand_zones = self._find_demand_zones(high, low, close, vol)
        supply_zones = self._find_supply_zones(high, low, close, vol)

        last_idx = len(data) - 1
        demand_zones = self._update_strength(demand_zones, high, low, last_idx)
        supply_zones = self._update_strength(supply_zones, high, low, last_idx)

        latest_close = float(close[-1])
        atr_val = float(self.compute_atr(data["high"], data["low"], data["close"]).iloc[-1])

        # Check demand zones
        for z in demand_zones:
            if abs(latest_close - z["zone_high"]) / latest_close <= self.zone_pct:
                conf = min(0.3 + z["strength"] * 0.1 + (z.get("volume_ratio", 1.0) - 1.0) * 0.1, 0.95)
                return Signal(
                    symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                    signal_type=SignalType.BUY,
                    confidence=round(conf, 2),
                    price=latest_close,
                    stop_loss=latest_close - atr_val * 1.5,
                    take_profit=latest_close + atr_val * 3.0,
                source_agent=self.name,
                source_strategy=self.name,
                    reasoning=f"Demand zone touch: {z['zone_high']:.2f}–{z['zone_low']:.2f}, strength={z['strength']}, vol={z.get('volume_ratio',1):.1f}x",
                )

        # Check supply zones
        for z in supply_zones:
            if abs(latest_close - z["zone_low"]) / latest_close <= self.zone_pct:
                conf = min(0.3 + z["strength"] * 0.1 + (z.get("volume_ratio", 1.0) - 1.0) * 0.1, 0.95)
                return Signal(
                    symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                    signal_type=SignalType.SELL,
                    confidence=round(conf, 2),
                    price=latest_close,
                    stop_loss=latest_close + atr_val * 1.5,
                    take_profit=latest_close - atr_val * 3.0,
                source_agent=self.name,
                source_strategy=self.name,
                    reasoning=f"Supply zone touch: {z['zone_high']:.2f}–{z['zone_low']:.2f}, strength={z['strength']}, vol={z.get('volume_ratio',1):.1f}x",
                )

        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(params={self.params})"
