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


@StrategyRegistry.register
class MicrostructureAlphaStrategy(Strategy):
    """Microstructure alpha from order flow analysis.

    Implements:
      - Order flow imbalance (OFI) signal
      - VPIN (Volume-synchronized Probability of Informed Trading)
      - Cumulative delta divergence
      - Absorption ratio (HFT liquidity detection)

    Reference: Easley, D., et al. (2012) 'The Volume Clock'
    """

    name = "microstructure_alpha"
    description = "Order flow imbalance + VPIN + cumulative delta + absorption ratio"
    required_indicators = ["close", "volume"]

    def __init__(self, parameters: StrategyParameters | None = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.tick_window = int(self.parameters.get("tick_window", 100))
        self.vpin_buckets = int(self.parameters.get("vpin_buckets", 50))
        self._tick_buf: list[dict[str, Any]] = []

    def _extract_ticks(self, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            ticks = data.get("ticks", data.get("tick_data", []))
            if isinstance(ticks, list):
                return ticks
        return []

    def _ofi(self, ticks: list[dict[str, Any]]) -> float:
        buy = sum(t.get("volume", 0) for t in ticks if t.get("side") == "buy")
        sell = sum(t.get("volume", 0) for t in ticks if t.get("side") == "sell")
        total = buy + sell
        return (buy - sell) / total if total > 0 else 0.0

    def _vpin(self, ticks: list[dict[str, Any]]) -> float:
        if len(ticks) < self.vpin_buckets:
            return 0.5
        bucket_vol = sum(t.get("volume", 0) for t in ticks) / self.vpin_buckets
        if bucket_vol <= 0:
            return 0.5
        signed, vol_sum, buckets = 0.0, 0.0, 0
        for t in ticks:
            v = t.get("volume", 0)
            vol_sum += v
            signed += v if t.get("side") == "buy" else -v
            if vol_sum >= bucket_vol:
                buckets += 1
                vol_sum = 0.0
        return float(abs(signed) / (buckets * bucket_vol + 1e-10))

    def _delta(self, ticks: list[dict[str, Any]]) -> float:
        return float(sum(t.get("volume", 0) if t.get("side") == "buy" else -t.get("volume", 0) for t in ticks))

    def _absorption(self, ticks: list[dict[str, Any]]) -> float:
        if len(ticks) < 20:
            return 0.5
        vols = np.array([t.get("volume", 0) for t in ticks])
        prices = np.array([t.get("price", 0) for t in ticks])
        changes = np.abs(np.diff(prices))
        if np.sum(changes) < 1e-10:
            return 0.5
        avg_impact = np.mean(changes) / (np.mean(vols[1:]) + 1e-10)
        recent_impact = np.mean(changes[-10:]) / (np.mean(vols[-10:]) + 1e-10)
        return float(np.clip(recent_impact / (avg_impact + 1e-10), 0.0, 2.0))

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            ticks = self._extract_ticks(data)
            if not ticks:
                closes = data.get("close", []) if isinstance(data, dict) else []
                if len(closes) > 1:
                    vol = data.get("volume", [1] * len(closes)) if isinstance(data, dict) else []
                    synthetic = [{"price": float(closes[i]), "volume": float(vol[i]) if i < len(vol) else 1.0, "side": ("buy" if closes[i] >= closes[i-1] else "sell") if i > 0 else "buy"} for i in range(len(closes))]
                    ticks = synthetic[-100:]

            if not ticks:
                return self._hold("No tick data available")

            self._tick_buf.extend(ticks)
            if len(self._tick_buf) > 10000:
                self._tick_buf = self._tick_buf[-5000:]

            window = self._tick_buf[-self.tick_window:]
            oi = self._ofi(window)
            vpin_ = self._vpin(self._tick_buf)
            cd = self._delta(window)
            ab = self._absorption(window)

            direction = SignalDirection.HOLD
            confidence = 0.0

            if oi > 0.4 and ab < 0.5:
                direction = SignalDirection.BUY
                confidence = min(0.85, 0.4 + oi * 0.5)
            elif oi < -0.4 and ab < 0.5:
                direction = SignalDirection.SELL
                confidence = min(0.85, 0.4 + abs(oi) * 0.5)

            if direction == SignalDirection.HOLD and vpin_ > 0.75:
                direction = SignalDirection.BUY if cd > 0 else SignalDirection.SELL
                confidence = 0.6

            if direction == SignalDirection.HOLD and abs(cd) > 50:
                direction = SignalDirection.BUY if cd > 0 else SignalDirection.SELL
                confidence = 0.5

            if direction == SignalDirection.HOLD:
                return self._hold(f"oi={oi:.2f} vpin={vpin_:.2f} delta={cd:.0f}", {"oi": oi, "vpin": vpin_, "delta": cd, "absorption": ab})

            price = float(window[-1].get("price", 0))
            strength = SignalStrength.STRONG if confidence > 0.6 else SignalStrength.MODERATE
            sl = price * (0.99 if direction == SignalDirection.BUY else 1.01)
            tp = price * (1.01 if direction == SignalDirection.BUY else 0.99)

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                risk_reward_ratio=self.calculate_risk_reward(price, sl, tp, direction),
                reasoning=f"oi={oi:.2f} vpin={vpin_:.2f} delta={cd:.0f} absorb={ab:.2f}",
                indicators={"oi": oi, "vpin": vpin_, "cumulative_delta": cd, "absorption_ratio": ab},
            )

        except Exception as exc:
            logger.error("MicrostructureAlpha error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: dict | None = None) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, direction=SignalDirection.HOLD, reasoning=reason, indicators=indicators or {})
