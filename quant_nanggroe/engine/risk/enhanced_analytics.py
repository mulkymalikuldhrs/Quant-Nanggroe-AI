"""
Enhanced Risk Analytics — Monte Carlo + Kelly + Performance Metrics
Ported from E:\\trading\\risk_module.py, enhanced for QNA async pipeline.

Provides:
- Kelly Criterion position sizing (fractional, safe)
- Monte Carlo simulation (VaR, CVaR, probability analysis)
- Performance metrics (Sharpe, Sortino, Calmar, max DD)
"""
from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Try numpy/pandas — fall back gracefully
try:
    import numpy as np
    import pandas as pd
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy/pandas not available — Monte Carlo will use pure Python")


@dataclass
class KellyResult:
    fraction: float  # optimal fraction (0-1)
    kelly_raw: float  # raw Kelly before fractional adjustment
    lot_size: float  # calculated lot size
    risk_amount: float  # dollar amount at risk
    confidence_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fraction": round(self.fraction, 6),
            "kelly_raw": round(self.kelly_raw, 6),
            "lot_size": round(self.lot_size, 2),
            "risk_amount": round(self.risk_amount, 2),
            "confidence_note": self.confidence_note,
        }


@dataclass
class MonteCarloResult:
    simulations: int
    confidence: float
    mean_return: float
    median_return: float
    var_95: float  # Value at Risk
    cvar_95: float  # Conditional VaR
    prob_profit: float  # probability of profit (%)
    best_case: float
    worst_case: float
    std_dev: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulations": self.simulations,
            "confidence": self.confidence,
            "mean_return": self.mean_return,
            "median_return": self.median_return,
            "var_95": self.var_95,
            "cvar_95": self.cvar_95,
            "prob_profit": self.prob_profit,
            "best_case": self.best_case,
            "worst_case": self.worst_case,
            "std_dev": self.std_dev,
        }


@dataclass
class PerformanceMetrics:
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    total_return: float
    annualized_return: float
    win_rate: float
    profit_factor: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "total_return": round(self.total_return, 4),
            "annualized_return": round(self.annualized_return, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
        }


class EnhancedRiskAnalytics:
    """Production risk analytics suite.

    Integrates:
    - Fractional Kelly for position sizing
    - Monte Carlo for forward-looking risk
    - Performance metrics for strategy evaluation
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.kelly_fraction_pct = self.config.get("kelly_fraction", 0.0025)
        self.mc_simulations = self.config.get("mc_simulations", 10000)
        self.mc_confidence = self.config.get("mc_confidence", 0.95)
        self.rf_rate = self.config.get("risk_free_rate", 0.05)
        # Annualization factor: assuming 15min bars = 35040/year
        self.ann_factor = self.config.get("annualization_factor", 35040)

    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        balance: float,
        stop_loss_pips: float = 50.0,
        pip_value: float = 10.0,
    ) -> KellyResult:
        """Calculate Kelly-optimal position size.

        Args:
            win_rate: Win rate as percentage (e.g., 60 for 60%)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size (positive number)
            balance: Current account balance
            stop_loss_pips: Stop loss in pips
            pip_value: Dollar value per pip (default $10 for 1 lot EURUSD)

        Returns:
            KellyResult with optimal sizing
        """
        if avg_loss == 0:
            return KellyResult(0, 0, 0, 0, "avg_loss is zero")

        b = avg_win / abs(avg_loss)  # odds ratio
        p = win_rate / 100 if win_rate > 1 else win_rate
        q = 1 - p

        kelly_raw = (p * b - q) / b if b > 0 else 0

        # Fractional Kelly for safety
        kelly_frac = max(0, min(self.kelly_fraction_pct, kelly_raw * self.kelly_fraction_pct))

        # Calculate lot size
        risk_amount = balance * kelly_frac
        if stop_loss_pips > 0 and pip_value > 0:
            lot_size = risk_amount / (stop_loss_pips * pip_value)
            lot_size = round(max(0.01, min(lot_size, balance / 5000)), 2)
        else:
            lot_size = 0

        note = "optimal" if kelly_raw > 0 else "negative edge — no position"
        if kelly_raw > 0.25:
            note = "high Kelly — capped at 25%"

        return KellyResult(
            fraction=kelly_frac,
            kelly_raw=kelly_raw,
            lot_size=lot_size,
            risk_amount=risk_amount,
            confidence_note=note,
        )

    def monte_carlo(
        self,
        trade_pnls: list[float],
        simulations: int | None = None,
        confidence: float | None = None,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation on historical trade P&Ls.

        Args:
            trade_pnls: List of P&L values from historical trades
            simulations: Number of MC runs (default from config)
            confidence: Confidence level for VaR (default 0.95)

        Returns:
            MonteCarloResult with risk metrics
        """
        sims = simulations or self.mc_simulations
        conf = confidence or self.mc_confidence

        if len(trade_pnls) < 5:
            return MonteCarloResult(
                simulations=sims, confidence=conf,
                mean_return=0, median_return=0, var_95=0, cvar_95=0,
                prob_profit=0, best_case=0, worst_case=0, std_dev=0,
            )

        results = []
        for _ in range(sims):
            sampled = random.choices(trade_pnls, k=len(trade_pnls))
            results.append(sum(sampled))

        results.sort()
        var_idx = int((1 - conf) * sims)
        cvar_idx = int((1 - conf) * sims / 2)

        prob_profit = sum(1 for r in results if r > 0) / sims * 100

        if HAS_NUMPY:
            mean_ret = round(float(np.mean(results)), 2)
            median_ret = round(float(np.median(results)), 2)
            std_dev = round(float(np.std(results)), 2)
        else:
            mean_ret = round(sum(results) / len(results), 2)
            median_ret = round(results[len(results) // 2], 2)
            variance = sum((r - mean_ret) ** 2 for r in results) / len(results)
            std_dev = round(math.sqrt(variance), 2)

        return MonteCarloResult(
            simulations=sims,
            confidence=conf,
            mean_return=mean_ret,
            median_return=median_ret,
            var_95=round(results[var_idx], 2),
            cvar_95=round(sum(results[:cvar_idx]) / max(cvar_idx, 1), 2),
            prob_profit=round(prob_profit, 1),
            best_case=round(results[-1], 2),
            worst_case=round(results[0], 2),
            std_dev=std_dev,
        )

    def performance_metrics(
        self,
        equity_curve: list[float],
        trades: list[dict[str, Any]] | None = None,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics.

        Args:
            equity_curve: Sequence of equity values over time
            trades: Optional list of trade dicts with 'pnl' key

        Returns:
            PerformanceMetrics with all ratios
        """
        if len(equity_curve) < 2:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0)

        if HAS_NUMPY:
            eq = pd.Series(equity_curve) if not isinstance(equity_curve, pd.Series) else equity_curve
            ret = eq.pct_change().dropna()
            ann_ret = float(ret.mean() * self.ann_factor)
            ann_vol = float(ret.std() * math.sqrt(self.ann_factor))
        else:
            rets = []
            for i in range(1, len(equity_curve)):
                if equity_curve[i - 1] != 0:
                    rets.append((equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1])
            if not rets:
                return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0)
            ann_ret = (sum(rets) / len(rets)) * self.ann_factor
            variance = sum((r - sum(rets) / len(rets)) ** 2 for r in rets) / len(rets)
            ann_vol = math.sqrt(variance) * math.sqrt(self.ann_factor)

        # Sharpe
        sharpe = (ann_ret - self.rf_rate) / ann_vol if ann_vol > 0 else 0

        # Sortino (downside deviation only)
        if HAS_NUMPY:
            downside = ret[ret < 0]
            downside_std = float(downside.std() * math.sqrt(self.ann_factor)) if len(downside) > 0 else 0
        else:
            neg_rets = [r for r in rets if r < 0]
            if neg_rets:
                ds_var = sum(r ** 2 for r in neg_rets) / len(neg_rets)
                downside_std = math.sqrt(ds_var) * math.sqrt(self.ann_factor)
            else:
                downside_std = 0
        sortino = (ann_ret - self.rf_rate) / downside_std if downside_std > 0 else 0

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0
        for v in equity_curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Calmar
        calmar = ann_ret / max_dd if max_dd > 0 else 0

        # Total return
        total_ret = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] if equity_curve[0] != 0 else 0

        # Win rate & profit factor from trades
        win_rate = 0
        profit_factor = 0
        if trades:
            pnls = [t.get("pnl", 0) for t in trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            win_rate = len(wins) / len(pnls) if pnls else 0
            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return PerformanceMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            total_return=total_ret,
            annualized_return=ann_ret,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )
