from __future__ import annotations

import logging
from typing import Any

import numpy as np

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


KNOWN_PAIRS: list[tuple[str, str]] = [
    ("GC1!", "SI1!"), ("ES1!", "NQ1!"), ("6E1!", "6B1!"),
    ("6A1!", "6C1!"), ("ZB1!", "ZN1!"), ("BTCUSD", "ETHUSD"),
    ("XAUUSD", "XAGUSD"), ("EURUSD", "GBPUSD"), ("US30", "NAS100"),
]


@StrategyRegistry.register
class StatisticalArbitrageStrategy(Strategy):
    """Moving-Band Statistical Arbitrage — Boyd et al. (2024).

    Uses cointegrated pairs with adaptive z-score bands.
    Entry on z-score extremes, exit on reversion to mean.
    Target Sharpe: 1.61, beta 0.11 (original paper).

    Reference: Boyd, N., et al. (2024) 'Moving-Band Statistical Arbitrage'
    """

    name = "statistical_arbitrage"
    description = "Pairs trading: z-score entry with cointegrated pairs"
    required_indicators = ["close"]

    def __init__(self, parameters: StrategyParameters | None = None, entry_z: float | None = None, exit_z: float | None = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.entry_z = entry_z if entry_z is not None else float(self.parameters.get("entry_z", 2.0))
        self.exit_z = exit_z if exit_z is not None else float(self.parameters.get("exit_z", 0.5))
        self._positions: dict[str, str] = {}

    def _extract_pair(self, data: Any) -> tuple[list[float], list[float]]:
        if isinstance(data, dict):
            pa = data.get("pair_a", data.get("prices_a", []))
            pb = data.get("pair_b", data.get("prices_b", []))
            if pa and pb:
                return [float(v) for v in pa], [float(v) for v in pb]
            pair = data.get("pair_prices", data.get("prices", {}))
            if isinstance(pair, dict):
                keys = list(pair.keys())
                if len(keys) >= 2:
                    return [float(v) for v in pair[keys[0]]], [float(v) for v in pair[keys[1]]]
        return [], []

    def _hedge_ratio(self, a: np.ndarray, b: np.ndarray) -> float:
        if len(b) < 30:
            return 1.0
        try:
            coeffs = np.linalg.lstsq(np.column_stack([np.ones(len(b)), b]), a, rcond=None)[0]
            return float(coeffs[1])
        except np.linalg.LinAlgError:
            return 1.0

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            prices_a, prices_b = self._extract_pair(data)
            if len(prices_a) < 20 or len(prices_b) < 20:
                return self._hold("Insufficient pair data")

            pa, pb = np.array(prices_a), np.array(prices_b)
            hr = self._hedge_ratio(pa, pb)
            spread = pa - hr * pb
            mean, std = float(np.mean(spread)), float(np.std(spread))
            z = float((spread[-1] - mean) / std) if std > 1e-10 else 0.0

            symbols = kwargs.get("symbol", "")
            pair_key = str(symbols) if symbols else f"{hash(str(prices_a[:5]))}"
            current_pos = self._positions.get(pair_key, "")

            direction = SignalDirection.HOLD
            confidence = 0.0
            reasoning = f"z={z:.2f} hr={hr:.4f}"

            if z > self.entry_z:
                direction = SignalDirection.SELL
                confidence = min(0.85, 0.3 + 0.15 * (z - self.entry_z))
                self._positions[pair_key] = "shorted"
                reasoning += " SELL (z>entry)"
            elif z < -self.entry_z:
                direction = SignalDirection.BUY
                confidence = min(0.85, 0.3 + 0.15 * (abs(z) - self.entry_z))
                self._positions[pair_key] = "bought"
                reasoning += " BUY (z<-entry)"
            elif current_pos and abs(z) < self.exit_z:
                direction = SignalDirection.EXIT
                confidence = 0.7
                self._positions.pop(pair_key, None)
                reasoning += " EXIT (z<exit)"

            if direction == SignalDirection.HOLD:
                return self._hold(reasoning, {"z_score": z, "hedge_ratio": hr})

            price = float(prices_a[-1])
            strength = SignalStrength.STRONG if confidence > 0.6 else SignalStrength.MODERATE
            sl = price * (0.98 if direction == SignalDirection.BUY else 1.02)
            tp = price * (1.02 if direction == SignalDirection.BUY else 0.98)

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                risk_reward=self.calculate_risk_reward(price, sl, tp, direction),
                reasoning=reasoning,
                indicators={"z_score": z, "hedge_ratio": hr, "spread_mean": mean, "spread_std": std},
            )

        except Exception as exc:
            logger.error("StatArb error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: dict | None = None) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, direction=SignalDirection.HOLD, reasoning=reason, indicators=indicators or {})
