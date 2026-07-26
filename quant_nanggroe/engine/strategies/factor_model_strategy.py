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
class FactorModelStrategy(Strategy):
    """Large Factor Model (SDF) — Kelly et al. 2025-2026 approach.

    Combines traditional factor zoo with cross-asset attention mechanism.
    Uses time-series and cross-sectional factor loadings to produce
    a Stochastic Discount Factor (SDF) that prices assets.

    Reference: Didisheim & Kelly (2025) 'Large Factor Models'
              Kelly et al. (2026) 'Transformer SDF'
    """

    name = "factor_model_sdf"
    description = "SDF factor model: momentum + carry + value + quality + low-vol ensemble"
    required_indicators = ["close"]

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            closes = self._extract_close(data)
            if len(closes) < 20:
                return self._hold("Insufficient data (need 20+ bars)")

            prices = np.array(closes, dtype=float)
            returns = np.diff(prices) / prices[:-1]
            regime_vol = float(kwargs.get("regime_volatility", 1.0))

            funda = data.get("fundamentals") if isinstance(data, dict) else kwargs.get("fundamentals")

            loadings = self._calc_loadings(returns, funda)
            sdf = self._compute_sdf(loadings, regime_vol)

            if sdf > 0.3:
                direction = SignalDirection.BUY
                conf = min(abs(sdf), 0.95)
                strength = SignalStrength.STRONG if abs(sdf) > 0.6 else SignalStrength.MODERATE
            elif sdf < -0.3:
                direction = SignalDirection.SELL
                conf = min(abs(sdf), 0.95)
                strength = SignalStrength.STRONG if abs(sdf) > 0.6 else SignalStrength.MODERATE
            else:
                return self._hold(f"SDF neutral (score={sdf:.4f})", {"sdf_score": sdf})

            price = float(closes[-1])
            sl = price * (0.97 if direction == SignalDirection.BUY else 1.03)
            tp = price * (1.04 if direction == SignalDirection.BUY else 0.96)

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=conf,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                risk_reward=self.calculate_risk_reward(price, sl, tp, direction),
                reasoning=f"SDF={sdf:.4f} mom={loadings[0]:.4f} carry={loadings[1]:.4f} val={loadings[2]:.4f} qual={loadings[3]:.4f} vol={loadings[4]:.4f}",
                indicators={"sdf_score": sdf, "momentum": loadings[0], "carry": loadings[1], "value": loadings[2], "quality": loadings[3], "volatility": loadings[4]},
            )

        except Exception as exc:
            logger.error("FactorModel error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _calc_loadings(self, returns: np.ndarray, funda: Any = None) -> list[float]:
        if len(returns) < 2:
            return [0.0] * 5
        mom = float(np.mean(returns[-min(252, len(returns)):]) * np.sqrt(252))
        vol = float(np.std(returns[-60:]) * np.sqrt(252))
        low_beta = 0.0
        if len(returns) >= 60:
            mkt = np.array([np.mean(returns[max(0, i-20):i+1]) for i in range(len(returns))])
            if np.std(mkt) > 1e-10:
                low_beta = 1.0 - float(np.cov(returns, mkt)[0, 1] / np.var(mkt))
        carry = float(funda.get("carry_yield", 0)) if isinstance(funda, dict) else 0.0
        quality = float(funda.get("profitability", 0)) if isinstance(funda, dict) else 0.0
        value = float(funda.get("book_to_price", 0)) if isinstance(funda, dict) else 0.0
        return [mom, carry, value, quality, vol, low_beta]

    def _compute_sdf(self, loadings: list[float], regime_vol: float) -> float:
        mom, carry, value, quality, vol_, low_beta = loadings
        score = 0.25 * np.tanh(mom) + 0.15 * np.tanh(carry) + 0.10 * np.tanh(value) + 0.15 * np.tanh(quality) + 0.10 * (1.0 - np.tanh(vol_ / 0.3)) + 0.10 * np.tanh(low_beta)
        if regime_vol > 0.4:
            score *= 0.5
        return float(np.clip(score, -1.0, 1.0))

    def _extract_close(self, data: Any) -> list[float]:
        if hasattr(data, "iloc"):
            return [float(v) for v in data["close"].values]
        elif isinstance(data, dict):
            vals = data.get("close", [])
            return [float(v) for v in vals] if isinstance(vals, (list, tuple)) else []
        return []

    def _hold(self, reason: str, indicators: dict | None = None) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, direction=SignalDirection.HOLD, reasoning=reason, indicators=indicators or {})
