"""Market Profile / Volume Profile Strategy.

Analyzes volume distribution across price levels to identify:
- Point of Control (POC)
- Value Area High/Low (70% of volume)
- Profile shape (normal, b-shape, p-shape, bipolar)
- Auction type (balanced, tail, unfinished)

Ported from ai-hedge-fund/src/strategies/unified_retail_strategy.py (MarketProfileAnalyzer)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalAction,
    Strategy,
    StrategyParameters,
    StrategySignal,
    StrategyType,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


class MarketProfileParameters(StrategyParameters):
    """Market Profile strategy parameters."""

    num_bins: int = 50
    value_area_pct: float = 0.70
    ib_period: int = 5  # Initial balance period (number of bars)
    min_confidence: float = 0.55


@StrategyRegistry.register
class MarketProfileStrategy(Strategy):
    """Market Profile / Volume Profile Strategy.

    Analyzes the volume distribution across price levels to identify
    high-volume nodes (POC), value areas, and auction types.
    """

    name = "market_profile"

    def __init__(self, parameters: Optional[MarketProfileParameters] = None) -> None:
        self._params = parameters or MarketProfileParameters()

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MARKET_PROFILE

    @property
    def description(self) -> str:
        return "Market profile / volume profile: POC, value area, auction type"

    def generate_signal(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> StrategySignal:
        """Generate market profile-based trading signal."""
        if not self.validate(df):
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reasoning="Insufficient data for market profile analysis",
            )

        high = df["high"]
        low = df["low"]
        close = df["close"]
        volume = df["volume"] if "volume" in df.columns else pd.Series(np.ones(len(df)), index=df.index)

        current_price = float(close.iloc[-1])

        # Calculate market profile
        poc, vah, val, profile_shape, auction_type = self._calculate_profile(high, low, close, volume)

        if poc is None:
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                action=SignalAction.HOLD,
                confidence=0.0,
                reasoning="Could not compute market profile",
            )

        # Score signal
        bullish_score = 0.0
        bearish_score = 0.0
        reasons = []

        # Price relative to value area
        if current_price > vah:
            bullish_score += 0.3
            reasons.append(f"Price above VAH ({vah:.2f}) — breakout")
        elif current_price < val:
            bearish_score += 0.3
            reasons.append(f"Price below VAL ({val:.2f}) — breakdown")
        elif current_price > poc:
            bullish_score += 0.15
            reasons.append("Price above POC — slight bullish")
        elif current_price < poc:
            bearish_score += 0.15
            reasons.append("Price below POC — slight bearish")

        # Profile shape
        if profile_shape == "p_shape":
            bullish_score += 0.2
            reasons.append("P-shape profile (accumulation)")
        elif profile_shape == "b_shape":
            bearish_score += 0.2
            reasons.append("B-shape profile (distribution)")

        # Auction type
        if auction_type == "tail":
            if current_price > vah:
                bullish_score += 0.2
                reasons.append("Tail auction above VAH")
            elif current_price < val:
                bearish_score += 0.2
                reasons.append("Tail auction below VAL")

        # Determine action
        total_score = bullish_score - bearish_score
        confidence = min(0.85, abs(total_score) + 0.3)

        if total_score > 0.3:
            action = SignalAction.BUY
            stop_loss = val * 0.99
            take_profit = vah * 1.02
        elif total_score < -0.3:
            action = SignalAction.SELL
            stop_loss = vah * 1.01
            take_profit = val * 0.98
        else:
            action = SignalAction.HOLD
            stop_loss = current_price
            take_profit = current_price

        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        rr_ratio = reward / risk if risk > 0 else 0

        if confidence < self._params.min_confidence:
            action = SignalAction.HOLD

        return StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            action=action,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            reasoning="; ".join(reasons) if reasons else "No market profile signal",
            metadata={
                "poc": poc,
                "vah": vah,
                "val": val,
                "profile_shape": profile_shape,
                "auction_type": auction_type,
                "bullish_score": bullish_score,
                "bearish_score": bearish_score,
            },
        )

    def get_parameters(self) -> MarketProfileParameters:
        return self._params

    def validate(self, df: pd.DataFrame) -> bool:
        required_cols = {"high", "low", "close"}
        if not required_cols.issubset(df.columns):
            return False
        return len(df) >= 30

    # ── Helper Methods ──────────────────────────────────────────────────

    def _calculate_profile(
        self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
    ) -> Tuple[Optional[float], float, float, str, str]:
        """Calculate market profile metrics.

        Returns:
            (poc, vah, val, profile_shape, auction_type)
        """
        price_range = float(high.max()) - float(low.min())
        if price_range <= 0:
            return None, 0.0, 0.0, "normal", "unfinished"

        num_bins = min(self._params.num_bins, max(5, int(price_range / 0.01)))
        bin_size = price_range / num_bins
        low_min = float(low.min())

        # Volume per bin
        vol_per_bin = np.zeros(num_bins)
        for i in range(len(close)):
            bin_idx = int((float(close.iloc[i]) - low_min) / bin_size)
            bin_idx = max(0, min(bin_idx, num_bins - 1))
            vol_per_bin[bin_idx] += float(volume.iloc[i])

        # POC (Point of Control)
        poc_idx = int(np.argmax(vol_per_bin))
        poc = low_min + poc_idx * bin_size

        # Value Area (70% of volume)
        total_vol = np.sum(vol_per_bin)
        if total_vol == 0:
            return poc, poc, poc, "normal", "unfinished"

        target_vol = total_vol * self._params.value_area_pct
        cumsum = np.cumsum(vol_per_bin)

        # Expand from POC
        va_high = poc_idx
        va_low = poc_idx
        current_vol = vol_per_bin[poc_idx]

        while current_vol < target_vol and (va_high < num_bins - 1 or va_low > 0):
            add_high = vol_per_bin[va_high + 1] if va_high < num_bins - 1 else 0
            add_low = vol_per_bin[va_low - 1] if va_low > 0 else 0

            if add_high >= add_low and va_high < num_bins - 1:
                va_high += 1
                current_vol += add_high
            elif va_low > 0:
                va_low -= 1
                current_vol += add_low
            else:
                break

        vah = low_min + va_high * bin_size
        val = low_min + va_low * bin_size

        # Profile shape
        left_tail = np.sum(vol_per_bin[:poc_idx])
        right_tail = np.sum(vol_per_bin[poc_idx + 1:])

        if left_tail > right_tail * 1.5:
            profile_shape = "b_shape"
        elif right_tail > left_tail * 1.5:
            profile_shape = "p_shape"
        else:
            profile_shape = "normal"

        # Auction type
        current = float(close.iloc[-1])
        if abs(current - poc) < bin_size:
            auction_type = "balanced"
        elif current > vah or current < val:
            auction_type = "tail"
        else:
            auction_type = "unfinished"

        return poc, vah, val, profile_shape, auction_type
