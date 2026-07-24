"""Pairs Trade Strategy — Wrapper for legacy PairsTrade (cointegration-based)."""

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
class PairsTradeStrategy(Strategy):
    """Pairs Trading via Cointegration (Gatev, Goetzmann, Rouwenhorst 2006).

    Wraps the legacy PairsTrade implementation.  Expects **two** price series:
    - primary symbol via ``data['close']``
    - pair symbol via ``kwargs['pair_data']['close']`` (or ``kwargs.get('pair_closes')``)

    If pair data is missing the strategy returns HOLD.
    """

    name = "pairs_trade"
    description = "Pairs trading: z-score of cointegrated pair spread"
    required_indicators = ["close"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("lookback"):
            params.set("lookback", 60)
        if not params.get("entry_z"):
            params.set("entry_z", 2.0)
        if not params.get("exit_z"):
            params.set("exit_z", 0.5)
        super().__init__(parameters=params)

    def _extract_close(self, data: Any, key: str = "close") -> List[float]:
        if hasattr(data, "iloc"):
            return [float(v) for v in data[key].values]
        elif isinstance(data, dict):
            vals = data.get(key, [])
            return [float(v) for v in vals] if isinstance(vals, (list, tuple)) else []
        return []

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            close_a = self._extract_close(data)
            if len(close_a) < self._parameters.get("lookback", 60):
                return self._hold("Insufficient primary data")

            # Try pair data from kwargs
            pair_data = kwargs.get("pair_data")
            pair_closes = kwargs.get("pair_closes")
            if pair_data is not None:
                close_b = self._extract_close(pair_data)
            elif pair_closes is not None:
                close_b = [float(v) for v in pair_closes] if isinstance(pair_closes, (list, tuple)) else []
            else:
                return self._hold("No pair data provided — pairs_trade needs two symbols", {})

            if len(close_b) < self._parameters.get("lookback", 60):
                return self._hold("Insufficient pair data")

            # Run legacy PairsTrade analysis
            from quant_nanggroe.strategies.pairs_trade import PairsTrade

            pt = PairsTrade(
                lookback=self._parameters.get("lookback", 60),
                entry_z=self._parameters.get("entry_z", 2.0),
                exit_z=self._parameters.get("exit_z", 0.5),
            )
            result = pt.analyze_pair(close_a, close_b)

            signal = result.get("signal", "hold")
            confidence = float(result.get("confidence", 0.0))
            z_score = float(result.get("z_score", 0.0))
            current_price = close_a[-1]

            if signal == "buy":
                direction = SignalDirection.BUY
                sl = current_price * 0.98
                tp = current_price * 1.04
                strength = SignalStrength.MODERATE if confidence < 0.6 else SignalStrength.STRONG
                reasoning = f"Pairs z-score {z_score:.2f} < -entry_z: BUY signal"
            elif signal == "sell":
                direction = SignalDirection.SELL
                sl = current_price * 1.02
                tp = current_price * 0.96
                strength = SignalStrength.MODERATE if confidence < 0.6 else SignalStrength.STRONG
                reasoning = f"Pairs z-score {z_score:.2f} > entry_z: SELL signal"
            elif signal == "close":
                direction = SignalDirection.EXIT
                strength = SignalStrength.MODERATE
                reasoning = f"Pairs z-score {z_score:.2f} < exit_z: closing position"
            else:
                return self._hold(f"Pairs neutral (z={z_score:.2f})", {"z_score": z_score})

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
                indicators={"z_score": z_score, "signal": signal},
            )

        except Exception as exc:
            logger.error("PairsTradeStrategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["PairsTradeStrategy"]
