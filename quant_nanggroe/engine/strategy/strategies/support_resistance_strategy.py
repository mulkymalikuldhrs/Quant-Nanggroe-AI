"""Support and Resistance levels trading strategy.

Detects key S/R levels from swing points, clusters them into zones,
and generates signals on bounces and breakouts.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class SupportResistanceStrategy(BaseStrategy):
    """Support and Resistance strategy.

    Parameters:
        pivot_window (int): Lookback for swing highs/lows (default 5)
        zone_pct (float): Cluster merge distance as % of price (default 0.005)
        min_touches (int): Min touches for a valid level (default 2)
        breakout_pct (float): % beyond level to confirm breakout (default 0.003)
        use_volume (bool): Require volume confirmation (default True)
    """

    def __init__(self, params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name="S/R", params=params)
        self.pivot_window = self.params.get("pivot_window", 5)
        self.zone_pct = self.params.get("zone_pct", 0.005)
        self.min_touches = self.params.get("min_touches", 2)
        self.breakout_pct = self.params.get("breakout_pct", 0.003)
        self.use_volume = self.params.get("use_volume", True)

    def required_columns(self) -> List[str]:
        cols = ["high", "low", "close"]
        if self.use_volume:
            cols.append("volume")
        return cols

    def warmup_period(self) -> int:
        return 20

    def _find_swing_points(
        self, high: np.ndarray, low: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        w = self.pivot_window
        swing_highs = np.zeros(len(high))
        swing_lows = np.zeros(len(low))

        for i in range(w, len(high) - w):
            if high[i] == max(high[i - w:i + w + 1]):
                swing_highs[i] = high[i]
            if low[i] == min(low[i - w:i + w + 1]):
                swing_lows[i] = low[i]

        return swing_highs, swing_lows

    def _cluster_levels(
        self, levels: List[float], prices: np.ndarray
    ) -> List[Dict]:
        if not levels:
            return []
        sorted_levels = sorted(levels)
        clusters = []
        current = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            if (
                abs(level - np.mean(current)) / np.mean(current)
                <= self.zone_pct
            ):
                current.append(level)
            else:
                avg_price = np.mean(current)
                touches = sum(
                    1
                    for p in prices
                    if abs(p - avg_price) / avg_price
                    <= self.zone_pct * 0.5
                )
                clusters.append(
                    {"price": avg_price, "touches": touches, "n_levels": len(current)}
                )
                current = [level]

        if current:
            avg_price = np.mean(current)
            touches = sum(
                1
                for p in prices
                if abs(p - avg_price) / avg_price <= self.zone_pct * 0.5
            )
            clusters.append(
                {"price": avg_price, "touches": touches, "n_levels": len(current)}
            )

        return clusters

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        high = data["high"].values
        low = data["low"].values
        close = data["close"].values
        vol = data["volume"].values if self.use_volume else None

        swing_highs, swing_lows = self._find_swing_points(high, low)

        resistance_levels = [sh for sh in swing_highs if sh > 0]
        support_levels = [sl for sl in swing_lows if sl > 0]

        resistance_zones = self._cluster_levels(resistance_levels, close)
        support_zones = self._cluster_levels(support_levels, close)

        latest_price = float(close[-1])
        avg_vol = float(np.mean(vol[-20:])) if vol is not None else 1.0
        current_vol = float(vol[-1]) if vol is not None else 1.0
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

        atr_val = float(
            self.compute_atr(data["high"], data["low"], data["close"]).iloc[-1]
        )

        # Breakout above resistance
        for rz in resistance_zones:
            if rz["touches"] < self.min_touches:
                continue
            dist = (rz["price"] - latest_price) / latest_price
            if -self.breakout_pct <= dist <= self.breakout_pct:
                if vol is not None and vol_ratio < 1.2:
                    continue
                return Signal(
                    symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                    signal_type=SignalType.BUY,
                    confidence=min(0.5 + vol_ratio * 0.1, 0.9),
                    price=latest_price,
                    stop_loss=latest_price - atr_val * 1.5,
                    take_profit=latest_price + atr_val * 3.0,
                source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"S/R breakout: resistance {rz['price']:.2f} broken, "
                        f"touches={rz['touches']}, vol={vol_ratio:.1f}x"
                    ),
                )

        # Bounce off support
        for sz in support_zones:
            if sz["touches"] < self.min_touches:
                continue
            dist = (latest_price - sz["price"]) / latest_price
            if -self.breakout_pct <= dist <= self.breakout_pct:
                confidence = min(
                    0.5 + (latest_price - sz["price"]) / sz["price"] * 10, 0.9
                )
                return Signal(
                    symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    price=latest_price,
                    stop_loss=latest_price - atr_val * 1.5,
                    take_profit=latest_price + atr_val * 3.0,
                source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"S/R bounce: support {sz['price']:.2f} held, "
                        f"touches={sz['touches']}"
                    ),
                )

        # Breakdown below support
        for sz in support_zones:
            if sz["touches"] < self.min_touches:
                continue
            dist = (latest_price - sz["price"]) / sz["price"]
            if -self.breakout_pct <= dist <= self.breakout_pct and dist < 0:
                if vol is not None and vol_ratio < 1.2:
                    continue
                return Signal(
                    symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                    signal_type=SignalType.SELL,
                    confidence=min(0.5 + vol_ratio * 0.1, 0.9),
                    price=latest_price,
                    stop_loss=latest_price + atr_val * 1.5,
                    take_profit=latest_price - atr_val * 3.0,
                source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"S/R breakdown: support {sz['price']:.2f} broken, "
                        f"touches={sz['touches']}, vol={vol_ratio:.1f}x"
                    ),
                )

        return None
