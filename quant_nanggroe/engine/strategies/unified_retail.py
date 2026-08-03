"""Unified Retail Strategy — Combined ICT+SMC+Wyckoff+Fibonacci+SNR."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
class UnifiedRetailStrategy(Strategy):
    """Unified Retail Strategy.

    Combines multiple retail trading methodologies:
    - ICT (Inner Circle Trader)
    - SMC (Smart Money Concepts)
    - Wyckoff Method
    - Fibonacci Retracement/Extension
    - Support & Resistance (SNR)

    Each methodology contributes a weighted signal, and the
    final signal is a consensus of all methods.
    """

    name = "unified_retail"
    description = "Unified strategy: ICT+SMC+Wyckoff+Fibonacci+SNR"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("weights"):
            params.set("weights", {
                "ict": 0.25,
                "smc": 0.25,
                "wyckoff": 0.20,
                "fibonacci": 0.15,
                "snr": 0.15,
            })
        if not params.get("min_confidence"):
            params.set("min_confidence", 0.5)
        super().__init__(parameters=params)

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        """Generate unified signal from all methodologies."""
        from quant_nanggroe.engine.strategies.fibonacci import FibonacciStrategy
        from quant_nanggroe.engine.strategies.ict import ICTStrategy
        from quant_nanggroe.engine.strategies.smc_strategy import SMCStrategy
        from quant_nanggroe.engine.strategies.wyckoff import WyckoffStrategy

        # R11b FIX (2026-08-04, user GO): weights param may be a list or dict in
        # the wild — coerce defensively so `.get()` never raises. A list of names
        # maps to default 0.2; a dict is used as-is; anything else -> empty dict.
        _raw_weights = self._parameters.get("weights", {})
        if isinstance(_raw_weights, dict):
            weights = _raw_weights
        elif isinstance(_raw_weights, (list, tuple)):
            weights = {str(n): 0.2 for n in _raw_weights}
        else:
            weights = {}
        min_confidence = self._parameters.get("min_confidence", 0.5)

        # Generate signals from each sub-strategy
        sub_strategies = {
            "ict": ICTStrategy(),
            "smc": SMCStrategy(),
            "wyckoff": WyckoffStrategy(),
            "fibonacci": FibonacciStrategy(),
        }

        scores = {"bullish": 0.0, "bearish": 0.0}
        all_indicators: Dict[str, Any] = {}
        reasons = []

        for name, strategy in sub_strategies.items():
            try:
                signal = strategy.generate_signal(data, **kwargs)
                weight = weights.get(name, 0.2)
                all_indicators[name] = {
                    "direction": signal.direction.value,
                    "confidence": signal.confidence,
                    "weight": weight,
                }

                if signal.direction == SignalDirection.BUY:
                    scores["bullish"] += signal.confidence * weight
                    reasons.append(f"{name}: BULLISH ({signal.confidence:.0%})")
                elif signal.direction == SignalDirection.SELL:
                    scores["bearish"] += signal.confidence * weight
                    reasons.append(f"{name}: BEARISH ({signal.confidence:.0%})")
                else:
                    reasons.append(f"{name}: HOLD")
            except Exception as exc:
                logger.warning("Sub-strategy %s failed: %s", name, exc)
                reasons.append(f"{name}: ERROR")

        # Add SNR analysis
        snr_signal = self._snr_analysis(data)
        snr_weight = weights.get("snr", 0.15)
        all_indicators["snr"] = snr_signal
        if snr_signal.get("direction") == "bullish":
            scores["bullish"] += 0.6 * snr_weight
        elif snr_signal.get("direction") == "bearish":
            scores["bearish"] += 0.6 * snr_weight

        # Determine final direction
        total_score = scores["bullish"] + scores["bearish"]
        if total_score < min_confidence:
            return StrategySignal(
                strategy_name=self.name,
                direction=SignalDirection.HOLD,
                reasoning=f"Low confidence (bull={scores['bullish']:.2f}, bear={scores['bearish']:.2f})",
                indicators=all_indicators,
            )

        # Get current price
        try:
            if hasattr(data, "iloc"):
                current_price = float(data["close"].iloc[-1])
                low_val = float(data["low"].values[-20:].min()) if len(data) >= 20 else float(data["low"].iloc[-1])
                high_val = float(data["high"].values[-20:].max()) if len(data) >= 20 else float(data["high"].iloc[-1])
            else:
                current_price = float(data.get("close", [0])[-1])
                low_val = min(data.get("low", [0]))
                high_val = max(data.get("high", [0]))
        except Exception:
            logger.exception("price_extraction_failed: current_price set to 0")
            current_price = 0
            low_val = 0
            high_val = 0

        if scores["bullish"] > scores["bearish"]:
            direction = SignalDirection.BUY
            confidence = scores["bullish"] / max(total_score, 0.01)
            sl = low_val * 0.99
            tp = current_price + (current_price - sl) * 2
            strength = SignalStrength.STRONG if confidence > 0.7 else SignalStrength.MODERATE
        elif scores["bearish"] > scores["bullish"]:
            direction = SignalDirection.SELL
            confidence = scores["bearish"] / max(total_score, 0.01)
            sl = high_val * 1.01
            tp = current_price - (sl - current_price) * 2
            strength = SignalStrength.STRONG if confidence > 0.7 else SignalStrength.MODERATE
        else:
            return StrategySignal(
                strategy_name=self.name,
                direction=SignalDirection.HOLD,
                reasoning="Mixed signals - no consensus",
                indicators=all_indicators,
            )

        return StrategySignal(
            strategy_name=self.name,
            symbol=kwargs.get("symbol", ""),
            direction=direction,
            strength=strength,
            confidence=round(confidence, 3),
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            risk_reward=self.calculate_risk_reward(current_price, sl, tp, direction),
            reasoning=f"Unified: {'; '.join(reasons)}",
            indicators=all_indicators,
        )

    def _snr_analysis(self, data: Any) -> Dict[str, Any]:
        """Support and Resistance analysis."""
        try:
            if hasattr(data, "iloc"):
                high = data["high"].values
                low = data["low"].values
                close = data["close"].values
            elif isinstance(data, dict):
                high = data.get("high", [])
                low = data.get("low", [])
                close = data.get("close", [])
            elif isinstance(data, (list, tuple)):
                # data is a list of candle dicts/rows
                high = [c.get("high") for c in data if isinstance(c, dict)]
                low = [c.get("low") for c in data if isinstance(c, dict)]
                close = [c.get("close") for c in data if isinstance(c, dict)]
            else:
                return {"direction": "neutral", "note": "unsupported data type"}

            if len(close) < 10:
                return {"direction": "neutral", "note": "insufficient data"}

            support = min(low[-20:]) if len(low) >= 20 else min(low)
            resistance = max(high[-20:]) if len(high) >= 20 else max(high)
            current = close[-1]

            # Check proximity to S/R
            dist_to_support = (current - support) / max(current, 0.01)
            dist_to_resistance = (resistance - current) / max(current, 0.01)

            if dist_to_support < 0.02:  # Within 2% of support
                return {"direction": "bullish", "support": support, "resistance": resistance}
            elif dist_to_resistance < 0.02:  # Within 2% of resistance
                return {"direction": "bearish", "support": support, "resistance": resistance}

            return {"direction": "neutral", "support": support, "resistance": resistance}
        except Exception:
            logger.exception("snr_analysis_failed: returning neutral with error flag")
            return {"direction": "neutral", "error": True}


__all__ = ["UnifiedRetailStrategy"]
