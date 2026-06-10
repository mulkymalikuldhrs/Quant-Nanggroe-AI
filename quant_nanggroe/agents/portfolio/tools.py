"""Portfolio Agent Tools for Quant Nanggroe AI Trading Framework."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from langchain_core.tools import tool


logger = logging.getLogger(__name__)


@tool
def optimize_portfolio(
    symbols: List[str],
    expected_returns: Optional[Dict[str, float]] = None,
    method: str = "risk_parity",
    risk_free_rate: float = 0.05,
) -> str:
    """
    Optimize portfolio allocation using specified method.

    Args:
        symbols: List of symbols to include
        expected_returns: Expected returns by symbol
        method: Optimization method (risk_parity, mean_variance, min_variance, max_sharpe)
        risk_free_rate: Risk-free rate for Sharpe calculation

    Returns:
        JSON string with optimized allocation
    """
    # In production, this would use scipy.optimize or cvxpy
    n = len(symbols)
    equal_weight = 1.0 / n if n > 0 else 0.0

    allocation = {}
    if method == "risk_parity":
        # Simplified risk parity: equal risk contribution
        for symbol in symbols:
            allocation[symbol] = round(equal_weight * 100, 2)
    elif method == "mean_variance":
        # Simplified mean-variance with expected returns
        for symbol in symbols:
            ret = (expected_returns or {}).get(symbol, 0.05)
            weight = max(0.05, min(0.25, ret / 0.2))  # Simple heuristic
            allocation[symbol] = round(weight * 100, 2)
    else:
        for symbol in symbols:
            allocation[symbol] = round(equal_weight * 100, 2)

    result = {
        "method": method,
        "allocation": allocation,
        "expected_return": 0.08,
        "expected_volatility": 0.12,
        "sharpe_ratio": 0.25,
        "risk_free_rate": risk_free_rate,
        "number_of_positions": n,
        "diversification_score": 0.75,
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def compute_allocation(
    current_positions: Dict[str, float],
    target_allocation: Dict[str, float],
    total_value: float,
) -> str:
    """
    Compute trades needed to reach target allocation.

    Args:
        current_positions: Current position values by symbol
        target_allocation: Target allocation weights by symbol (0-100%)
        total_value: Total portfolio value

    Returns:
        JSON string with required trades
    """
    trades = {}
    for symbol, target_weight in target_allocation.items():
        target_value = total_value * (target_weight / 100)
        current_value = current_positions.get(symbol, 0)
        diff = target_value - current_value
        if abs(diff) > total_value * 0.01:  # Only trade if diff > 1%
            trades[symbol] = {
                "action": "BUY" if diff > 0 else "SELL",
                "amount": round(abs(diff), 2),
                "current_value": round(current_value, 2),
                "target_value": round(target_value, 2),
            }

    result = {
        "current_positions": current_positions,
        "target_allocation": target_allocation,
        "required_trades": trades,
        "total_rebalance_amount": sum(t["amount"] for t in trades.values()),
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def rebalance(
    current_allocation: Dict[str, float],
    target_allocation: Dict[str, float],
    threshold_pct: float = 5.0,
) -> str:
    """
    Determine if portfolio rebalancing is needed.

    Args:
        current_allocation: Current allocation weights by symbol
        target_allocation: Target allocation weights by symbol
        threshold_pct: Drift threshold to trigger rebalancing (default: 5%)

    Returns:
        JSON string with rebalancing assessment
    """
    drifts = {}
    needs_rebalance = False

    all_symbols = set(list(current_allocation.keys()) + list(target_allocation.keys()))
    for symbol in all_symbols:
        current = current_allocation.get(symbol, 0)
        target = target_allocation.get(symbol, 0)
        drift = abs(current - target)
        drifts[symbol] = {
            "current": current,
            "target": target,
            "drift": round(drift, 2),
            "exceeds_threshold": drift > threshold_pct,
        }
        if drift > threshold_pct:
            needs_rebalance = True

    result = {
        "needs_rebalance": needs_rebalance,
        "threshold_pct": threshold_pct,
        "drifts": drifts,
        "recommendation": "Rebalance recommended" if needs_rebalance else "No rebalancing needed",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


PORTFOLIO_TOOLS = [optimize_portfolio, compute_allocation, rebalance]
