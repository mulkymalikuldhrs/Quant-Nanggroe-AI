"""ICT (Inner Circle Trader) trading strategy.

Implements Michael Huddleston's ICT concepts:

- Displacement — directional candle with body >= displacement_atr_mult × ATR,
  identifying institutional-driven moves
- Fair Value Gaps (FVG) — price inefficiency between two candles where
  retail liquidity was taken
- Optimal Trade Entry (OTE) — retracement into the 61.8%-70.2% Fibonacci
  zone of the displacement range
- Order Blocks — consolidation before a displacement move
- Kill Zones — London (2-5am EST), New York (7-10am EST), Asian (7pm-2am EST)

When require_killzone is True, only trade during active kill zone sessions.

References:
    - Huddleston, M. "Inner Circle Trader" (ICT) — 2016-2022 concepts.
    - ICT mentorship materials on displacement, FVG, OTE, and
      silver bullet methodologies.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class ICTStrategy(BaseStrategy):
    """ICT trading strategy.

    Parameters:
        displacement_atr_mult (float): Min ATR multiplier for displacement (default 1.5)
        ote_min (float): Min OTE retracement (default 0.618)
        ote_max (float): Max OTE retracement (default 0.702)
        require_killzone (bool): Require kill zone time filter (default False)
    """

    def __init__(self, params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name="ICT", params=params)
        self.disp_atr_mult = self.params.get("displacement_atr_mult", 1.5)
        self.ote_min = self.params.get("ote_min", 0.618)
        self.ote_max = self.params.get("ote_max", 0.702)
        self.require_killzone = self.params.get("require_killzone", False)

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return 30

    @staticmethod
    def _in_killzone(dt: pd.Timestamp) -> bool:
        h = dt.hour
        # London: 2-5am EST = 7-10am UTC
        if 7 <= h <= 9:
            return True
        # New York: 7am-12pm EST = 12-17 UTC
        if 12 <= h <= 16:
            return True
        # Asian: 7pm-2am EST = 0-7 UTC
        if 0 <= h <= 6:
            return True
        return False

    def _detect_displacement(self, high, low, close, atr, i):
        if i < 2:
            return None
        candle_range = high[i] - low[i]
        body = abs(close[i] - close[i - 1])
        if candle_range > atr[i] * self.disp_atr_mult and body > candle_range * 0.5:
            if close[i] > close[i - 1]:
                return "bullish"
            elif close[i] < close[i - 1]:
                return "bearish"
        return None

    def _detect_fvg(self, high, low, i):
        if i < 2:
            return None
        if low[i - 2] > high[i]:
            return "bullish"
        if high[i - 2] < low[i]:
            return "bearish"
        return None

    def _find_order_block(self, high, low, close, i):
        if i < 3:
            return None
        if close[i] > close[i - 1] and close[i - 1] < close[i - 2]:
            return "bullish", high[i - 1], low[i - 1]
        if close[i] < close[i - 1] and close[i - 1] > close[i - 2]:
            return "bearish", high[i - 1], low[i - 1]
        return None

    def _compute_ote_levels(self, move_high, move_low):
        dist = move_high - move_low
        return {
            "ote_buy_zone_high": move_low + dist * self.ote_max,
            "ote_buy_zone_low": move_low + dist * self.ote_min,
            "ote_sell_zone_high": move_high - dist * self.ote_min,
            "ote_sell_zone_low": move_high - dist * self.ote_max,
        }

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        high = data["high"].values
        low = data["low"].values
        close = data["close"].values
        atr = self.compute_atr(data["high"], data["low"], data["close"], 14).values

        if self.require_killzone and isinstance(data.index, pd.DatetimeIndex):
            if not self._in_killzone(data.index[-1]):
                return None

        last_i = len(data) - 1
        displacement = None
        disp_start = None
        for i in range(last_i, max(last_i - 10, 2), -1):
            d = self._detect_displacement(high, low, close, atr, i)
            if d:
                displacement = d
                disp_start = i
                break

        if not displacement:
            return None

        fvg = self._detect_fvg(high, low, disp_start)

        ob = self._find_order_block(high, low, close, disp_start)

        move_high = max(high[disp_start - 1:disp_start + 2])
        move_low = min(low[disp_start - 1:disp_start + 2])
        ote = self._compute_ote_levels(move_high, move_low)

        latest_price = float(close[-1])

        if displacement == "bullish":
            in_ote = ote["ote_buy_zone_low"] <= latest_price <= ote["ote_buy_zone_high"]
            has_confluence = sum([
                1 if fvg == "bullish" else 0,
                1 if ob and ob[0] == "bullish" else 0,
                1 if in_ote else 0,
            ])
            if has_confluence >= 2:
                atr_val = float(atr[-1])
                return Signal(
                    symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                    signal_type=SignalType.BUY,
                    confidence=min(has_confluence / 3.0, 1.0),
                    price=latest_price,
                    stop_loss=latest_price - atr_val * 1.5,
                    take_profit=latest_price + atr_val * 3.0,
                source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"ICT BUY: displacement @{disp_start} FVG={fvg} "
                        f"OB={'yes' if ob else 'no'} OTE={in_ote} conf={has_confluence}/3"
                    ),
                )

        elif displacement == "bearish":
            in_ote = ote["ote_sell_zone_low"] <= latest_price <= ote["ote_sell_zone_high"]
            has_confluence = sum([
                1 if fvg == "bearish" else 0,
                1 if ob and ob[0] == "bearish" else 0,
                1 if in_ote else 0,
            ])
            if has_confluence >= 2:
                atr_val = float(atr[-1])
                return Signal(
                    symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                    signal_type=SignalType.SELL,
                    confidence=min(has_confluence / 3.0, 1.0),
                    price=latest_price,
                    stop_loss=latest_price + atr_val * 1.5,
                    take_profit=latest_price - atr_val * 3.0,
                source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"ICT SELL: displacement @{disp_start} FVG={fvg} "
                        f"OB={'yes' if ob else 'no'} OTE={in_ote} conf={has_confluence}/3"
                    ),
                )

        return None
