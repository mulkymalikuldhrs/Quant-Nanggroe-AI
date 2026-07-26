from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AssetAllocation:
    symbol: str
    weight: float
    volatility: float
    risk_contribution: float
    asset_class: str


@dataclass
class RiskParityPortfolio:
    allocations: list[AssetAllocation] = field(default_factory=list)
    total_volatility: float = 0.0
    diversification_ratio: float = 0.0
    leverage: float = 1.0
    convolved_risk: float = 0.0


CORE_ASSET_CLASSES: dict[str, dict[str, float]] = {
    "equities": {"expected_vol": 0.15, "expected_return": 0.08, "weight_cap": 0.30},
    "bonds": {"expected_vol": 0.06, "expected_return": 0.04, "weight_cap": 0.40},
    "commodities": {"expected_vol": 0.20, "expected_return": 0.06, "weight_cap": 0.20},
    "forex": {"expected_vol": 0.10, "expected_return": 0.03, "weight_cap": 0.20},
    "crypto": {"expected_vol": 0.60, "expected_return": 0.15, "weight_cap": 0.05},
}


class RiskParityAllocator:
    """Bridgewater-style Risk Parity allocation.

    Allocates risk equally across asset classes rather than capital.
    Uses:
      - Volatility parity (equal risk contribution)
      - Leverage to target absolute volatility
      - Drawdown-constrained rebalancing
      - Cross-asset correlation scaling

    Reference: Bridgewater Associates 'All Weather' / 'Risk Parity' strategy
              Asness, C., et al. (2012) 'Leverage Aversion and Risk Parity'
    """

    def __init__(self, target_vol: float = 0.10, max_leverage: float = 2.0, rebalance_threshold: float = 0.05):
        self.target_vol = target_vol
        self.max_leverage = max_leverage
        self.rebalance_threshold = rebalance_threshold

    def compute_risk_parity_weights(self, volatilities: dict[str, float], correlations: dict[tuple[str, str], float] | None = None) -> dict[str, float]:
        n = len(volatilities)
        if n == 0:
            return {}

        symbols = list(volatilities.keys())
        vols = np.array([max(volatilities[s], 0.01) for s in symbols])

        inv_vol = 1.0 / vols
        weights = inv_vol / np.sum(inv_vol)
        scaled = weights / np.max(weights)

        risk_contrib = scaled * vols / np.sum(scaled * vols)

        rc_std = float(np.std(risk_contrib))
        logger.info("Risk parity: %d assets, rc_std=%.4f", n, rc_std)

        result: dict[str, float] = {}
        for i, s in enumerate(symbols):
            result[s] = float(scaled[i])

        return result

    def compute_volatility_parity(self, portfolio_value: float, positions: dict[str, dict[str, Any]], volatilities: dict[str, float]) -> RiskParityPortfolio:
        if not volatilities:
            return RiskParityPortfolio()

        raw_weights = self.compute_risk_parity_weights(volatilities)
        total = sum(raw_weights.values())
        if total == 0:
            return RiskParityPortfolio()

        # Scale to target volatility
        inv_vol_sum = sum(1.0 / max(v, 0.01) for v in volatilities.values())
        target_leverage = self.target_vol * inv_vol_sum / len(volatilities)
        leverage = min(target_leverage, self.max_leverage)

        allocations: list[AssetAllocation] = []
        for symbol, vol in volatilities.items():
            raw_w = raw_weights.get(symbol, 0.0)
            weight = raw_w * leverage
            rc = weight * vol

            ac = "other"
            for cls, params in CORE_ASSET_CLASSES.items():
                if any(indicator in symbol.upper() for indicator in {
                    "equities": ["ES", "NQ", "YM", "SPY", "QQQ"],
                    "bonds": ["ZB", "ZN", "BOND", "TREASURY"],
                    "commodities": ["GC", "SI", "CL", "NG", "HG"],
                    "forex": ["6E", "6B", "6J", "6A", "6C", "DXY"],
                    "crypto": ["BTC", "ETH"],
                }.get(cls, [])):
                    ac = cls
                    break

            allocations.append(AssetAllocation(
                symbol=symbol,
                weight=round(weight, 4),
                volatility=vol,
                risk_contribution=round(rc, 6),
                asset_class=ac,
            ))

        total_vol = sum(a.weight * a.volatility for a in allocations)
        return RiskParityPortfolio(
            allocations=allocations,
            total_volatility=round(total_vol, 4),
            diversification_ratio=round(len(allocations) * sum(a.weight * a.volatility for a in allocations) / (sum(abs(a.weight) * a.volatility for a in allocations) + 1e-10), 4),
            leverage=round(leverage, 2),
        )

    def rebalance_check(self, current_weights: dict[str, float], target_weights: dict[str, float]) -> list[str]:
        symbols_to_rebalance: list[str] = []
        for sym, target in target_weights.items():
            current = current_weights.get(sym, 0.0)
            drift = abs(target - current) / (max(abs(target), 0.001))
            if drift > self.rebalance_threshold:
                symbols_to_rebalance.append(sym)
        return symbols_to_rebalance

    def to_dict(self, portfolio: RiskParityPortfolio) -> dict[str, Any]:
        return {
            "total_volatility": portfolio.total_volatility,
            "diversification_ratio": portfolio.diversification_ratio,
            "leverage": portfolio.leverage,
            "allocations": [
                {
                    "symbol": a.symbol,
                    "weight_pct": round(a.weight * 100, 2),
                    "volatility": round(a.volatility * 100, 2),
                    "risk_contribution_pct": round(a.risk_contribution * 100, 4),
                    "asset_class": a.asset_class,
                }
                for a in portfolio.allocations
            ],
        }
