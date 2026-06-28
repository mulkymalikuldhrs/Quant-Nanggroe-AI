"""Correlation regime detection and cross-asset margin monitoring.

Monitors rolling correlations between assets to detect correlation regimes
and manages total margin utilization across all positions.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class CorrelationRegimeDetector:
    """Detects correlation regimes across assets.

    Monitors rolling correlations between symbols and classifies
    the current correlation regime: low_corr, normal_corr, high_corr, crisis_corr.

    In high/crisis correlation regimes, diversification benefits break down
    and position limits should be tightened.
    """

    def __init__(self, window: int = 30) -> None:
        self.window = window
        self._returns_history: Dict[str, List[float]] = defaultdict(list)

    def update(self, symbol_returns: Dict[str, float]) -> None:
        """Feed per-symbol returns for the current period.

        Args:
            symbol_returns: Dict mapping symbol to its return for this period.
        """
        for symbol, ret in symbol_returns.items():
            self._returns_history[symbol].append(float(ret))
            if len(self._returns_history[symbol]) > self.window:
                self._returns_history[symbol] = self._returns_history[symbol][-self.window:]

    def get_correlation_matrix(self) -> pd.DataFrame:
        """Rolling correlation matrix (window=30 periods).

        Returns:
            Correlation matrix as a DataFrame, or empty DataFrame if insufficient data.
        """
        symbols = [s for s, vals in self._returns_history.items() if len(vals) >= 2]
        if len(symbols) < 2:
            return pd.DataFrame()

        data = {s: self._returns_history[s] for s in symbols}
        df = pd.DataFrame(data)
        return df.corr()

    def detect_regime(self) -> tuple[str, float]:
        """Detect current correlation regime.

        Returns:
            Tuple of (regime_name, confidence).
            - crisis_corr: avg pairwise correlation > 0.8
            - high_corr: avg pairwise correlation > 0.6
            - normal_corr: avg pairwise correlation 0.3-0.6
            - low_corr: avg pairwise correlation < 0.3
        """
        corr_matrix = self.get_correlation_matrix()
        if corr_matrix.empty or corr_matrix.shape[0] < 2:
            return "normal_corr", 0.0

        n = corr_matrix.shape[0]
        mask = ~np.eye(n, dtype=bool)
        avg_corr = float(corr_matrix.values[mask].mean())

        if avg_corr > 0.8:
            return "crisis_corr", min(1.0, avg_corr)
        elif avg_corr > 0.6:
            return "high_corr", min(0.9, avg_corr)
        elif avg_corr >= 0.3:
            return "normal_corr", 0.7
        else:
            return "low_corr", 0.8

    def get_margin_multiplier(self) -> float:
        """Position size multiplier based on current correlation regime.

        Returns:
            Multiplier: crisis_corr=0.3, high_corr=0.6, normal_corr=1.0, low_corr=1.2
        """
        regime, confidence = self.detect_regime()
        multipliers = {
            "crisis_corr": 0.3,
            "high_corr": 0.6,
            "normal_corr": 1.0,
            "low_corr": 1.2,
        }
        return multipliers.get(regime, 1.0)


class CrossAssetMarginMonitor:
    """Monitors total margin usage across all assets.

    Ensures total leveraged exposure doesn't exceed available margin.
    """

    def __init__(self) -> None:
        self._positions: Dict[str, Dict[str, float]] = {}

    def update(self, positions: Dict[str, Dict[str, float]]) -> None:
        """Feed current positions.

        Args:
            positions: {symbol: {qty, entry_price, current_price, leverage}}
        """
        self._positions = {}
        for symbol, pos in positions.items():
            self._positions[symbol] = {
                "qty": float(pos.get("qty", 0)),
                "entry_price": float(pos.get("entry_price", 0)),
                "current_price": float(pos.get("current_price", 0)),
                "leverage": float(pos.get("leverage", 1)),
            }

    def margin_used(self) -> float:
        """Total margin in use.

        Margin = sum(position_value / leverage)
        """
        total = 0.0
        for pos in self._positions.values():
            position_value = pos["qty"] * pos["current_price"]
            lev = max(pos["leverage"], 1)
            total += position_value / lev
        return total

    def margin_available(self, equity: float) -> float:
        """Available margin.

        Args:
            equity: Total account equity.

        Returns:
            Available margin (equity - margin_used).
        """
        return equity - self.margin_used()

    def margin_utilization(self, equity: float) -> float:
        """Margin utilization ratio (0-1).

        Args:
            equity: Total account equity.

        Returns:
            Utilization ratio clamped to [0, 1].
        """
        used = self.margin_used()
        if equity <= 0:
            return 1.0 if used > 0 else 0.0
        return min(1.0, used / equity)

    def check_margin_call(
        self,
        equity: float,
        maintenance_margin: float = 0.25,
    ) -> Dict[str, Any]:
        """Check if margin call conditions are met.

        Args:
            equity: Total account equity.
            maintenance_margin: Maintenance margin requirement (default 0.25 = 25%).

        Returns:
            Dict with margin_call (bool), excess, close_recommendations.
        """
        used = self.margin_used()
        excess = equity - used * (1 / maintenance_margin - 1) if used > 0 else equity
        margin_call = excess < 0 or self.margin_utilization(equity) > (1 - maintenance_margin)

        recommendations = []
        if margin_call:
            sorted_positions = sorted(
                self._positions.items(),
                key=lambda x: abs(x[1]["qty"] * x[1]["current_price"]),
                reverse=True,
            )
            for symbol, pos in sorted_positions:
                position_value = abs(pos["qty"] * pos["current_price"])
                recommendations.append({
                    "symbol": symbol,
                    "position_value": position_value,
                    "action": "REDUCE" if pos["qty"] != 0 else "CLOSE",
                })

        return {
            "margin_call": margin_call,
            "excess": round(excess, 2),
            "margin_used": round(used, 2),
            "equity": equity,
            "maintenance_margin": maintenance_margin,
            "utilization": round(self.margin_utilization(equity), 4),
            "close_recommendations": recommendations,
        }

    def status(self) -> Dict[str, Any]:
        """Full margin status.

        Returns:
            Dict with positions, margin_used, and position details.
        """
        positions_detail = []
        for symbol, pos in self._positions.items():
            position_value = pos["qty"] * pos["current_price"]
            margin = position_value / max(pos["leverage"], 1)
            positions_detail.append({
                "symbol": symbol,
                "qty": pos["qty"],
                "current_price": pos["current_price"],
                "leverage": pos["leverage"],
                "position_value": position_value,
                "margin": margin,
            })

        return {
            "positions": positions_detail,
            "margin_used": round(self.margin_used(), 2),
            "num_positions": len(self._positions),
        }
