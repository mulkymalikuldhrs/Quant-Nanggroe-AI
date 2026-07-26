from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class TailRiskLevel(Enum):
    NONE = 0
    WATCH = 1
    HEDGE = 2
    EMERGENCY = 3


@dataclass
class TailRiskMetrics:
    cvar_95: float
    cvar_99: float
    expected_shortfall: float
    max_drawdown_forecast: float
    tail_ratio: float
    skewness: float
    kurtosis: float
    risk_level: TailRiskLevel
    hedging_cost_bps: float


@dataclass
class HedgeAllocation:
    asset: str
    weight: float
    hedge_type: str
    cost_bps: float


class TailRiskHedger:
    """Tail risk hedging — CVaR optimization + crash protection.

    Combines:
      - CVaR (Conditional Value at Risk) optimization
      - Tail ratio monitoring (95th/50th percentile)
      - Put option hedging cost estimation
      - Trend-based crash protection
      - Dynamic hedge rebalancing

    Reference: Artzner et al. (1999) 'Coherent Measures of Risk'
              Taleb, N. 'Black Swan' hedging framework
              Practitioner: Universa, 36 South, Capstone
    """

    def __init__(self, cvar_confidence: float = 0.95, lookback: int = 252):
        self.cvar_confidence = cvar_confidence
        self.lookback = lookback
        self._returns: list[float] = []
        self._hedge_history: list[dict[str, Any]] = []

    def add_return(self, log_return: float) -> None:
        self._returns.append(log_return)
        if len(self._returns) > self.lookback * 2:
            self._returns = self._returns[-self.lookback * 2:]

    def compute_cvar(self, returns: np.ndarray, confidence: float) -> float:
        if len(returns) == 0:
            return 0.0
        var_threshold = np.percentile(returns, (1 - confidence) * 100)
        tail = returns[returns <= var_threshold]
        return float(np.mean(tail)) if len(tail) > 0 else float(var_threshold)

    def assess(self) -> TailRiskMetrics:
        if len(self._returns) < 20:
            return TailRiskMetrics(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 3.0, TailRiskLevel.NONE, 0.0)

        returns = np.array(self._returns[-self.lookback:])
        n = len(returns)

        cvar_95 = abs(self.compute_cvar(returns, 0.95))
        cvar_99 = abs(self.compute_cvar(returns, 0.99))
        es = (cvar_95 + cvar_99) / 2

        # Expected max drawdown from CVaR (simplified)
        mdd_forecast = es * np.sqrt(n / 252) * 2.0

        # Tail ratio: 95th / 50th percentile
        p95 = abs(np.percentile(returns, 5))
        p50 = abs(np.percentile(returns, 50))
        tail_ratio = p95 / p50 if p50 > 1e-10 else 3.0

        # Skewness and kurtosis
        skewness = float(pd_skewness(returns))
        kurtosis = float(pd_kurtosis(returns))

        # Risk level
        if cvar_99 > 0.05 or kurtosis > 8.0 or tail_ratio > 5.0:
            risk_level = TailRiskLevel.EMERGENCY
        elif cvar_95 > 0.03 or kurtosis > 5.0 or tail_ratio > 3.0:
            risk_level = TailRiskLevel.HEDGE
        elif cvar_95 > 0.015 or tail_ratio > 2.0:
            risk_level = TailRiskLevel.WATCH
        else:
            risk_level = TailRiskLevel.NONE

        # Hedging cost (VIX-based approximation)
        hedging_cost = cvar_95 * 0.6 * 10000

        return TailRiskMetrics(
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            expected_shortfall=es,
            max_drawdown_forecast=mdd_forecast,
            tail_ratio=tail_ratio,
            skewness=skewness,
            kurtosis=kurtosis,
            risk_level=risk_level,
            hedging_cost_bps=round(hedging_cost, 2),
        )

    def suggest_hedge(self, portfolio_value: float, risk_level: TailRiskLevel | None = None) -> list[HedgeAllocation]:
        metrics = self.assess()
        level = risk_level or metrics.risk_level

        if level == TailRiskLevel.NONE:
            return []

        hedges: list[HedgeAllocation] = []
        if level == TailRiskLevel.WATCH:
            hedges.append(HedgeAllocation("VIX_call", 0.02, "tail_risk", round(metrics.hedging_cost_bps * 0.5, 2)))
            hedges.append(HedgeAllocation("GOLD", 0.05, "safe_haven", 5.0))
        elif level == TailRiskLevel.HEDGE:
            hedges.append(HedgeAllocation("VIX_call", 0.05, "tail_risk", round(metrics.hedging_cost_bps, 2)))
            hedges.append(HedgeAllocation("PUT_SPX", 0.03, "put_spread", round(metrics.hedging_cost_bps * 1.5, 2)))
            hedges.append(HedgeAllocation("GOLD", 0.10, "safe_haven", 5.0))
            hedges.append(HedgeAllocation("TREASURY", 0.10, "flight_to_safety", 2.0))
        elif level == TailRiskLevel.EMERGENCY:
            hedges.append(HedgeAllocation("VIX_call", 0.10, "tail_risk", round(metrics.hedging_cost_bps * 2, 2)))
            hedges.append(HedgeAllocation("PUT_SPX", 0.05, "put_spread", round(metrics.hedging_cost_bps * 2.5, 2)))
            hedges.append(HedgeAllocation("GOLD", 0.15, "safe_haven", 5.0))
            hedges.append(HedgeAllocation("TREASURY", 0.20, "flight_to_safety", 2.0))
            hedges.append(HedgeAllocation("USD", 0.10, "cash", 0.0))

        return hedges

    def to_dict(self) -> dict[str, Any]:
        metrics = self.assess()
        hedges = self.suggest_hedge(portfolio_value=100000.0)
        return {
            "cvar_95": metrics.cvar_95,
            "cvar_99": metrics.cvar_99,
            "expected_shortfall": metrics.expected_shortfall,
            "max_drawdown_forecast": metrics.max_drawdown_forecast,
            "tail_ratio": metrics.tail_ratio,
            "skewness": metrics.skewness,
            "kurtosis": metrics.kurtosis,
            "risk_level": metrics.risk_level.name,
            "hedging_cost_bps": metrics.hedging_cost_bps,
            "suggested_hedges": [(h.asset, h.weight, h.hedge_type) for h in hedges],
        }


def pd_skewness(arr: np.ndarray) -> float:
    n = len(arr)
    if n < 3:
        return 0.0
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std < 1e-12:
        return 0.0
    return float((n / ((n-1) * (n-2))) * np.sum(((arr - mean) / std) ** 3))


def pd_kurtosis(arr: np.ndarray) -> float:
    n = len(arr)
    if n < 4:
        return 3.0
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std < 1e-12:
        return 3.0
    kurt = float((n * (n+1) / ((n-1) * (n-2) * (n-3))) * np.sum(((arr - mean) / std) ** 4))
    return kurt - (3 * (n-1) ** 2) / ((n-2) * (n-3))
