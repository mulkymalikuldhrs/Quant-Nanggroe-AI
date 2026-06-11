"""Position Sizing Algorithms.

Implements various position sizing algorithms for risk management:

1. Fixed Fractional: Risk a fixed percentage of equity per trade
2. Volatility-Based: Size inversely proportional to ATR/volatility
3. Kelly-Based: Kelly Criterion derived sizing
4. Risk Parity: Equal risk contribution sizing
5. Optimal-f: Ralph Vince's optimal fraction

All methods enforce the CONSTITUTIONAL MAX_RISK_PER_TRADE limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.risk.manager import MAX_RISK_PER_TRADE


@dataclass
class PositionSizeResult:
    """Result from position sizing calculation."""

    size: float
    risk_amount: float
    risk_pct: float
    method: str
    capped: bool
    max_risk_used: float


class PositionSizer:
    """Position Sizing with Constitutional Limits.

    All methods enforce MAX_RISK_PER_TRADE as a hard cap.
    No method can exceed this limit regardless of input parameters.
    """

    @staticmethod
    def fixed_fractional(
        equity: float,
        risk_pct: float = 0.01,
        entry_price: float = 100.0,
        stop_price: float = 99.0,
    ) -> PositionSizeResult:
        """Fixed fractional position sizing.

        Size = (equity * risk_pct) / |entry - stop|

        Args:
            equity: Current portfolio equity.
            risk_pct: Desired risk percentage (capped at MAX_RISK_PER_TRADE).
            entry_price: Entry price.
            stop_price: Stop loss price.

        Returns:
            PositionSizeResult with calculated size.
        """
        effective_risk = min(risk_pct, MAX_RISK_PER_TRADE)
        capped = risk_pct > MAX_RISK_PER_TRADE
        risk_amount = equity * effective_risk

        price_risk = abs(entry_price - stop_price)
        if price_risk <= 0:
            return PositionSizeResult(0.0, 0.0, 0.0, "fixed_fractional", True, MAX_RISK_PER_TRADE)

        size = risk_amount / price_risk
        return PositionSizeResult(
            size=size,
            risk_amount=risk_amount,
            risk_pct=effective_risk,
            method="fixed_fractional",
            capped=capped,
            max_risk_used=MAX_RISK_PER_TRADE,
        )

    @staticmethod
    def volatility_based(
        equity: float,
        atr: float,
        atr_multiplier: float = 2.0,
        entry_price: float = 100.0,
        risk_pct: float = 0.01,
    ) -> PositionSizeResult:
        """Volatility-based position sizing using ATR.

        Stop distance = atr_multiplier * ATR
        Size = (equity * risk_pct) / stop_distance

        Args:
            equity: Current portfolio equity.
            atr: Average True Range value.
            atr_multiplier: ATR multiplier for stop distance.
            entry_price: Entry price.
            risk_pct: Risk percentage (capped at MAX_RISK_PER_TRADE).

        Returns:
            PositionSizeResult.
        """
        effective_risk = min(risk_pct, MAX_RISK_PER_TRADE)
        capped = risk_pct > MAX_RISK_PER_TRADE
        risk_amount = equity * effective_risk

        stop_distance = atr_multiplier * atr
        if stop_distance <= 0:
            return PositionSizeResult(0.0, 0.0, 0.0, "volatility_based", True, MAX_RISK_PER_TRADE)

        size = risk_amount / stop_distance
        return PositionSizeResult(
            size=size,
            risk_amount=risk_amount,
            risk_pct=effective_risk,
            method="volatility_based",
            capped=capped,
            max_risk_used=MAX_RISK_PER_TRADE,
        )

    @staticmethod
    def kelly_based(
        equity: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.5,
    ) -> PositionSizeResult:
        """Kelly-based position sizing.

        Args:
            equity: Current portfolio equity.
            win_rate: Historical win rate.
            avg_win: Average winning trade amount.
            avg_loss: Average losing trade amount.
            fraction: Kelly fraction (0.5 = half Kelly).

        Returns:
            PositionSizeResult.
        """
        if avg_loss <= 0:
            return PositionSizeResult(0.0, 0.0, 0.0, "kelly_based", False, MAX_RISK_PER_TRADE)

        b = avg_win / avg_loss
        kelly_f = (b * win_rate - (1 - win_rate)) / b if b > 0 else 0.0
        kelly_f = max(0.0, kelly_f) * fraction

        # Enforce constitutional limit
        effective_risk = min(kelly_f, MAX_RISK_PER_TRADE)
        capped = kelly_f > MAX_RISK_PER_TRADE

        risk_amount = equity * effective_risk
        size = risk_amount / avg_loss if avg_loss > 0 else 0.0

        return PositionSizeResult(
            size=size,
            risk_amount=risk_amount,
            risk_pct=effective_risk,
            method="kelly_based",
            capped=capped,
            max_risk_used=MAX_RISK_PER_TRADE,
        )

    @staticmethod
    def optimal_f(
        equity: float,
        trades_pnl: list,
    ) -> PositionSizeResult:
        """Ralph Vince's Optimal-f position sizing.

        Finds the fraction that maximizes geometric growth from
        historical trade results.

        Args:
            equity: Current portfolio equity.
            trades_pnl: List of historical trade P&L values.

        Returns:
            PositionSizeResult.
        """
        if not trades_pnl:
            return PositionSizeResult(0.0, 0.0, 0.0, "optimal_f", False, MAX_RISK_PER_TRADE)

        max_loss = abs(min(trades_pnl))
        if max_loss <= 0:
            return PositionSizeResult(0.0, 0.0, 0.0, "optimal_f", False, MAX_RISK_PER_TRADE)

        best_f = 0.0
        best_growth = -np.inf

        for f_pct in np.arange(0.01, 1.0, 0.01):
            terminal = 1.0
            for pnl in trades_pnl:
                hpr = 1.0 + f_pct * (-pnl / max_loss)
                terminal *= hpr

            growth = terminal ** (1.0 / len(trades_pnl)) if terminal > 0 else 0.0
            if growth > best_growth:
                best_growth = growth
                best_f = f_pct

        # Enforce constitutional limit
        effective_risk = min(best_f, MAX_RISK_PER_TRADE)
        capped = best_f > MAX_RISK_PER_TRADE

        risk_amount = equity * effective_risk
        size = risk_amount / max_loss

        return PositionSizeResult(
            size=size,
            risk_amount=risk_amount,
            risk_pct=effective_risk,
            method="optimal_f",
            capped=capped,
            max_risk_used=MAX_RISK_PER_TRADE,
        )
