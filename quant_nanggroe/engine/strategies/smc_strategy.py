"""SMC Strategy — Smart Money Concepts trading strategy."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
class SMCStrategy(Strategy):
    """Smart Money Concepts Strategy.

    Detects institutional trading patterns:
    - Order Blocks (OB): Last bearish candle before bullish move (bullish OB)
      or last bullish candle before bearish move (bearish OB)
    - Fair Value Gaps (FVG): 3-candle gap indicating imbalance
    - Break of Structure (BOS): Trend continuation
    - Change of Character (CHOCH): Trend reversal
    - Liquidity Sweeps: Price taking out stops before reversing
    """

    name = "smc"
    description = "Smart Money Concepts: order blocks, FVGs, BOS, CHOCH"
    required_indicators = ["close", "high", "low", "volume"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("fvg_min_gap_pct"):
            params.set("fvg_min_gap_pct", 0.001)  # 0.1% minimum FVG
        if not params.get("ob_lookback"):
            params.set("ob_lookback", 10)
        if not params.get("liquidity_sweep_pct"):
            params.set("liquidity_sweep_pct", 0.005)  # 0.5% sweep threshold
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        """Generate SMC-based trading signal."""
        try:
            if hasattr(data, "iloc"):
                close = data["close"].values
                high = data["high"].values
                low = data["low"].values
                open_prices = data["open"].values if "open" in data else close
            elif isinstance(data, dict):
                close = data.get("close", [])
                high = data.get("high", [])
                low = data.get("low", [])
                open_prices = data.get("open", close)
            else:
                return self._hold("No valid data")

            if len(close) < 5:
                return self._hold("Insufficient data")

            indicators: Dict[str, Any] = {}
            signals_found = []

            # Detect Fair Value Gaps
            fvg = self._detect_fvg(close, high, low)
            if fvg:
                indicators["fvg"] = fvg
                signals_found.append(fvg)

            # Detect Order Blocks
            ob = self._detect_order_block(close, high, low, open_prices)
            if ob:
                indicators["order_block"] = ob
                signals_found.append(ob)

            # Detect BOS/CHOCH
            structure = self._detect_structure(close, high, low)
            if structure:
                indicators["structure"] = structure
                signals_found.append(structure)

            # Detect Liquidity Sweep
            sweep = self._detect_liquidity_sweep(close, high, low)
            if sweep:
                indicators["liquidity_sweep"] = sweep
                signals_found.append(sweep)

            # Aggregate signals
            if not signals_found:
                return self._hold("No SMC patterns detected", indicators)

            # Determine direction from signals
            bullish_count = sum(1 for s in signals_found if s.get("direction") == "bullish")
            bearish_count = sum(1 for s in signals_found if s.get("direction") == "bearish")

            current_price = close[-1]
            recent_low = min(low[-20:]) if len(low) >= 20 else min(low)
            recent_high = max(high[-20:]) if len(high) >= 20 else max(high)

            if bullish_count > bearish_count:
                direction = SignalDirection.BUY
                sl = recent_low * 0.995
                tp = current_price + (current_price - sl) * 2
                strength = SignalStrength.STRONG if bullish_count >= 2 else SignalStrength.MODERATE
                confidence = min(0.5 + bullish_count * 0.15, 0.9)
                reasoning = f"SMC Bullish: {bullish_count} bullish patterns ({', '.join(s.get('type','') for s in signals_found if s.get('direction')=='bullish')})"
            elif bearish_count > bullish_count:
                direction = SignalDirection.SELL
                sl = recent_high * 1.005
                tp = current_price - (sl - current_price) * 2
                strength = SignalStrength.STRONG if bearish_count >= 2 else SignalStrength.MODERATE
                confidence = min(0.5 + bearish_count * 0.15, 0.9)
                reasoning = f"SMC Bearish: {bearish_count} bearish patterns"
            else:
                return self._hold("Mixed SMC signals", indicators)

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=sl,
                take_profit=tp,
                risk_reward=self.calculate_risk_reward(current_price, sl, tp, direction),
                reasoning=reasoning,
                indicators=indicators,
            )

        except Exception as exc:
            logger.error("SMC strategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _detect_fvg(self, close, high, low) -> Optional[Dict]:
        """Detect Fair Value Gap (3-candle imbalance)."""
        if len(high) < 3:
            return None

        min_gap_pct = self._parameters.get("fvg_min_gap_pct", 0.001)

        # Bullish FVG: gap between candle[i-2].low and candle[i].high
        if low[-1] > high[-3]:
            gap_pct = (low[-1] - high[-3]) / close[-1]
            if gap_pct >= min_gap_pct:
                return {"type": "fvg_bullish", "direction": "bullish", "gap_pct": round(gap_pct, 4)}

        # Bearish FVG: gap between candle[i-2].high and candle[i].low
        if high[-1] < low[-3]:
            gap_pct = (low[-3] - high[-1]) / close[-1]
            if gap_pct >= min_gap_pct:
                return {"type": "fvg_bearish", "direction": "bearish", "gap_pct": round(gap_pct, 4)}

        return None

    def _detect_order_block(self, close, high, low, open_prices) -> Optional[Dict]:
        """Detect Order Block."""
        if len(close) < 4:
            return None

        # Bullish OB: last bearish candle before bullish move
        if close[-1] > close[-2] and close[-2] < open_prices[-2]:
            return {"type": "bullish_ob", "direction": "bullish", "level": high[-2]}

        # Bearish OB: last bullish candle before bearish move
        if close[-1] < close[-2] and close[-2] > open_prices[-2]:
            return {"type": "bearish_ob", "direction": "bearish", "level": low[-2]}

        return None

    def _detect_structure(self, close, high, low) -> Optional[Dict]:
        """Detect BOS or CHOCH."""
        if len(high) < 6:
            return None

        # Simple structure: compare recent highs/lows
        recent_high = max(high[-5:])
        prev_high = max(high[-10:-5]) if len(high) >= 10 else max(high[:5])
        recent_low = min(low[-5:])
        prev_low = min(low[-10:-5]) if len(low) >= 10 else min(low[:5])

        if recent_high > prev_high and recent_low > prev_low:
            return {"type": "BOS_bullish", "direction": "bullish"}
        elif recent_high < prev_high and recent_low < prev_low:
            return {"type": "BOS_bearish", "direction": "bearish"}
        elif recent_high > prev_high and recent_low < prev_low:
            return {"type": "CHOCH_bullish", "direction": "bullish"}
        elif recent_high < prev_high and recent_low > prev_low:
            return {"type": "CHOCH_bearish", "direction": "bearish"}

        return None

    def _detect_liquidity_sweep(self, close, high, low) -> Optional[Dict]:
        """Detect liquidity sweep."""
        if len(high) < 10:
            return None

        sweep_pct = self._parameters.get("liquidity_sweep_pct", 0.005)
        recent_low = min(low[-10:-1])
        recent_high = max(high[-10:-1])

        # Bullish sweep: price dipped below recent low then reversed
        if low[-1] < recent_low and close[-1] > recent_low:
            return {"type": "bullish_sweep", "direction": "bullish", "swept_level": recent_low}

        # Bearish sweep: price spiked above recent high then reversed
        if high[-1] > recent_high and close[-1] < recent_high:
            return {"type": "bearish_sweep", "direction": "bearish", "swept_level": recent_high}

        return None

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["SMCStrategy"]
