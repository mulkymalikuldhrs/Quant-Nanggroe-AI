"""Risk of Ruin Calculator — Monte Carlo Simulation.

Computes the probability of reaching a ruin threshold given a trading
strategy's win rate, average win/loss, and position sizing. Uses Monte
Carlo simulation for robust estimation and provides an analytical
approximation based on the Kelly Criterion.

Key components:
- Monte Carlo simulation of equity curves
- Kelly-based analytical approximation of risk of ruin
- Binary search for optimal position sizing
- Comprehensive risk reports with confidence intervals
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger(__name__)


# ── Pydantic models ──────────────────────────────────────────────────────


class RiskOfRuinConfig(BaseModel):
    """Configuration for risk of ruin simulation."""

    initial_capital: float = Field(..., gt=0, description="Starting capital")
    target_capital: float = Field(
        0, description="Target capital (0 = no target, run until ruin or max trades)"
    )
    max_simulations: int = Field(
        10000, ge=100, description="Number of Monte Carlo simulations"
    )
    max_trades_per_sim: int = Field(
        1000, ge=10, description="Maximum trades per simulation"
    )
    win_rate: float = Field(..., ge=0, le=1, description="Probability of a winning trade")
    avg_win: float = Field(..., gt=0, description="Average winning trade amount (absolute)")
    avg_loss: float = Field(..., gt=0, description="Average losing trade amount (absolute)")
    position_size_pct: float = Field(
        0.02, gt=0, le=1, description="Position size as fraction of capital"
    )
    ruin_threshold: float = Field(
        0.0, ge=0, lt=1, description="Ruin threshold as fraction of initial capital"
    )
    cost_per_trade: float = Field(
        0.001, ge=0, description="Transaction cost as fraction of position"
    )


class RiskOfRuinResult(BaseModel):
    """Result of a risk of ruin Monte Carlo simulation."""

    probability_of_ruin: float = Field(
        ..., description="Probability of hitting the ruin threshold"
    )
    expected_survival_trades: float = Field(
        ..., description="Expected number of trades before ruin (or max)"
    )
    median_final_capital: float = Field(
        ..., description="Median final capital across simulations"
    )
    p5_final_capital: float = Field(
        ..., description="5th percentile of final capital"
    )
    p95_final_capital: float = Field(
        ..., description="95th percentile of final capital"
    )
    max_drawdown_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="Max drawdown distribution (mean, median, p95)",
    )
    capital_paths_sample: List[List[float]] = Field(
        default_factory=list,
        description="Sample of simulated equity paths",
    )
    confidence_interval: Tuple[float, float] = Field(
        ..., description="95% CI for probability of ruin"
    )
    is_acceptable: bool = Field(
        ..., description="True if probability of ruin < 0.01"
    )
    recommendation: str = Field(..., description="Human-readable recommendation")


class RiskOfRuinReport(BaseModel):
    """Comprehensive risk of ruin report."""

    config: RiskOfRuinConfig
    mc_result: RiskOfRuinResult
    analytical_ror: float = Field(
        ..., description="Analytical (Kelly-based) risk of ruin"
    )
    kelly_optimal_size: float = Field(
        ..., description="Optimal Kelly fraction"
    )
    recommended_max_position: float = Field(
        ..., description="Recommended maximum position size"
    )
    verdict: str = Field(
        ..., description="SAFE / CAUTION / DANGEROUS / CRITICAL"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )


# ── Core simulation ──────────────────────────────────────────────────────


def simulate_risk_of_ruin(config: RiskOfRuinConfig) -> RiskOfRuinResult:
    """Run Monte Carlo simulation to estimate risk of ruin.

    Parameters
    ----------
    config : RiskOfRuinConfig
        Simulation configuration.

    Returns
    -------
    RiskOfRuinResult
        Complete simulation results.
    """
    logger.info(
        "starting_ror_simulation",
        n_sims=config.max_simulations,
        win_rate=config.win_rate,
        position_size=config.position_size_pct,
    )

    rng = np.random.default_rng()

    ruin_level = config.initial_capital * config.ruin_threshold
    n_sims = config.max_simulations
    max_trades = config.max_trades_per_sim

    # Vectorised simulation
    # Generate all random numbers at once for performance
    # Shape: (n_sims, max_trades)
    trade_outcomes = rng.random((n_sims, max_trades))
    wins = trade_outcomes < config.win_rate  # Boolean mask

    # Pre-compute trade returns
    # Win: +avg_win * position_size * capital - cost
    # Loss: -avg_loss * position_size * capital - cost
    # We need to simulate path-dependent (capital changes each trade)

    final_capitals = np.zeros(n_sims)
    survival_trades = np.full(n_sims, float(max_trades))
    max_drawdowns = np.zeros(n_sims)

    # Store sample paths (first 5)
    n_sample_paths = min(5, n_sims)
    sample_paths: List[List[float]] = [[] for _ in range(n_sample_paths)]

    for sim_idx in range(n_sims):
        capital = config.initial_capital
        peak = capital
        max_dd = 0.0

        for trade_idx in range(max_trades):
            if capital <= ruin_level:
                survival_trades[sim_idx] = float(trade_idx)
                break

            if config.target_capital > 0 and capital >= config.target_capital:
                survival_trades[sim_idx] = float(trade_idx)
                break

            # Position size
            position_value = capital * config.position_size_pct

            # Determine outcome
            if wins[sim_idx, trade_idx]:
                pnl = config.avg_win * position_value / capital
            else:
                pnl = -config.avg_loss * position_value / capital

            # Transaction cost
            cost = config.cost_per_trade * position_value / capital

            # Update capital
            capital = capital * (1 + pnl - cost)
            capital = max(capital, 0.0)  # Cannot go below zero

            # Track drawdown
            if capital > peak:
                peak = capital
            if peak > 0:
                dd = (peak - capital) / peak
                if dd > max_dd:
                    max_dd = dd

            # Record sample path
            if sim_idx < n_sample_paths:
                sample_paths[sim_idx].append(round(capital, 4))

        final_capitals[sim_idx] = capital
        max_drawdowns[sim_idx] = max_dd

    # Compute statistics
    ruined = final_capitals <= ruin_level * 1.001  # Small tolerance
    prob_ruin = float(np.mean(ruined))

    # 95% confidence interval for probability (Wilson score)
    n_r = int(np.sum(ruined))
    z = 1.96
    denom = n_sims + z ** 2
    centre = (n_r + z ** 2 / 2) / denom
    margin = z * math.sqrt(n_r * (n_sims - n_r) / n_sims + z ** 2 / 4) / denom
    ci_lower = max(0.0, centre - margin)
    ci_upper = min(1.0, centre + margin)

    median_final = float(np.median(final_capitals))
    p5_final = float(np.percentile(final_capitals, 5))
    p95_final = float(np.percentile(final_capitals, 95))
    expected_survival = float(np.mean(survival_trades))

    # Drawdown distribution
    dd_distribution = {
        "mean": round(float(np.mean(max_drawdowns)), 6),
        "median": round(float(np.median(max_drawdowns)), 6),
        "p95": round(float(np.percentile(max_drawdowns, 95)), 6),
    }

    is_acceptable = prob_ruin < 0.01

    if prob_ruin < 0.01:
        recommendation = (
            f"Risk of ruin is {prob_ruin:.4f} (below 1% threshold). "
            "Position sizing appears safe."
        )
    elif prob_ruin < 0.05:
        recommendation = (
            f"Risk of ruin is {prob_ruin:.4f} (1-5%). Consider reducing "
            "position size or improving strategy edge."
        )
    elif prob_ruin < 0.20:
        recommendation = (
            f"Risk of ruin is {prob_ruin:.4f} (5-20%). Position sizing "
            "is aggressive. Reduce exposure significantly."
        )
    else:
        recommendation = (
            f"Risk of ruin is {prob_ruin:.4f} (>20%). Strategy is "
            "dangerously sized. Do not deploy with current parameters."
        )

    return RiskOfRuinResult(
        probability_of_ruin=round(prob_ruin, 6),
        expected_survival_trades=round(expected_survival, 2),
        median_final_capital=round(median_final, 4),
        p5_final_capital=round(p5_final, 4),
        p95_final_capital=round(p95_final, 4),
        max_drawdown_distribution=dd_distribution,
        capital_paths_sample=sample_paths,
        confidence_interval=(round(ci_lower, 6), round(ci_upper, 6)),
        is_acceptable=is_acceptable,
        recommendation=recommendation,
    )


def kelly_risk_of_ruin(kelly_fraction: float, win_rate: float) -> float:
    """Compute analytical approximation of risk of ruin using Kelly.

    Uses the formula:
        ROR ≈ ((1 - edge) / (1 + edge)) ^ (capital_units)

    where edge = win_rate * avg_win - (1 - win_rate) * avg_loss,
    and the Kelly fraction determines the capital units.

    A simpler approximation for full Kelly:
        ROR ≈ (1 - 2*edge) ^ capital_units

    For fractional Kelly (f * Kelly):
        ROR ≈ ((1 - 2*edge*f) / (1 + 2*edge*f)) ^ (capital_units / f)

    Parameters
    ----------
    kelly_fraction : float
        Fraction of the optimal Kelly bet being used (0 to 1+).
        1.0 = full Kelly, 0.5 = half Kelly.
    win_rate : float
        Probability of winning.

    Returns
    -------
    float
        Analytical risk of ruin approximation.
    """
    if kelly_fraction <= 0:
        return 1.0

    if win_rate <= 0:
        return 1.0

    if win_rate >= 1:
        return 0.0

    # Edge in terms of win probability
    # For a simplified model: assume avg_win/avg_loss = 1:1
    # Then Kelly = 2*p - 1, edge = 2*p - 1
    edge = 2 * win_rate - 1

    if edge <= 0:
        return 1.0  # Negative or zero edge -> certain ruin eventually

    # Using the approximation: ROR ≈ ((1-edge)/(1+edge))^(bankroll_units)
    # bankroll_units ≈ 1 / kelly_fraction (at full Kelly, 1 unit = full bankroll)
    ratio = (1 - edge) / (1 + edge)

    if ratio <= 0:
        return 0.0

    # Capital units: at fraction f of Kelly, capital is divided into 1/f units
    capital_units = 1.0 / kelly_fraction

    ror = ratio ** capital_units
    return float(min(1.0, max(0.0, ror)))


def optimal_position_size(
    config: RiskOfRuinConfig,
    max_ror: float = 0.01,
) -> float:
    """Find the optimal position size that keeps risk of ruin below a threshold.

    Uses binary search over position sizes.

    Parameters
    ----------
    config : RiskOfRuinConfig
        Simulation configuration (position_size_pct is used as starting upper bound).
    max_ror : float
        Maximum acceptable risk of ruin (default: 0.01 = 1%).

    Returns
    -------
    float
        Optimal position size as a fraction of capital.
    """
    # Binary search between a tiny position size and the configured size
    lo = 0.001
    hi = config.position_size_pct * 2  # Search up to 2x configured size

    # If even the smallest position has ROR > max_ror, return lo
    config_lo = config.model_copy(update={"position_size_pct": lo, "max_simulations": 2000})
    result_lo = simulate_risk_of_ruin(config_lo)
    if result_lo.probability_of_ruin > max_ror:
        return lo

    # If the max position has ROR < max_ror, return hi
    config_hi = config.model_copy(update={"position_size_pct": hi, "max_simulations": 2000})
    result_hi = simulate_risk_of_ruin(config_hi)
    if result_hi.probability_of_ruin <= max_ror:
        return hi

    # Binary search
    for _ in range(20):  # 20 iterations gives ~6 decimal precision
        mid = (lo + hi) / 2
        config_mid = config.model_copy(
            update={"position_size_pct": mid, "max_simulations": 2000}
        )
        result_mid = simulate_risk_of_ruin(config_mid)

        if result_mid.probability_of_ruin <= max_ror:
            lo = mid  # Safe, try larger
        else:
            hi = mid  # Too risky, try smaller

    return round(lo, 6)


def generate_risk_of_ruin_report(config: RiskOfRuinConfig) -> RiskOfRuinReport:
    """Generate a comprehensive risk of ruin report.

    One-call function that runs the MC simulation, computes the
    analytical approximation, and produces a full report.

    Parameters
    ----------
    config : RiskOfRuinConfig
        Simulation configuration.

    Returns
    -------
    RiskOfRuinReport
    """
    # Monte Carlo simulation
    mc_result = simulate_risk_of_ruin(config)

    # Kelly optimal fraction
    # Kelly = p - q/b where p=win_rate, q=1-p, b=avg_win/avg_loss
    b = config.avg_win / config.avg_loss
    p = config.win_rate
    q = 1 - p
    kelly_optimal = max(0, p - q / b) if b > 0 else 0.0

    # Analytical ROR at current position size
    # Map position_size_pct to a Kelly fraction
    if kelly_optimal > 0:
        current_kelly_fraction = config.position_size_pct / kelly_optimal
    else:
        current_kelly_fraction = 0.0

    analytical_ror = kelly_risk_of_ruin(current_kelly_fraction, config.win_rate)

    # Recommended max position size (half Kelly)
    recommended_max = kelly_optimal * 0.5

    # Verdict
    mc_ror = mc_result.probability_of_ruin
    if mc_ror < 0.01:
        verdict = "SAFE"
    elif mc_ror < 0.05:
        verdict = "CAUTION"
    elif mc_ror < 0.20:
        verdict = "DANGEROUS"
    else:
        verdict = "CRITICAL"

    # Recommendations
    recommendations: List[str] = []

    if verdict == "SAFE":
        recommendations.append(
            f"Risk of ruin ({mc_ror:.4f}) is within acceptable limits (<1%)."
        )
    elif verdict == "CAUTION":
        recommendations.append(
            f"Risk of ruin ({mc_ror:.4f}) is elevated. Consider reducing position size."
        )
        recommendations.append(
            f"Current position: {config.position_size_pct:.2%}. "
            f"Half-Kelly suggestion: {recommended_max:.2%}."
        )
    elif verdict == "DANGEROUS":
        recommendations.append(
            f"Risk of ruin ({mc_ror:.4f}) is dangerously high. "
            "Immediately reduce position sizing."
        )
        recommendations.append(
            f"Recommended maximum position size: {recommended_max:.2%} (half Kelly)."
        )
        recommendations.append(
            "Review strategy edge — win rate and reward/risk ratio may be insufficient."
        )
    else:  # CRITICAL
        recommendations.append(
            f"CRITICAL: Risk of ruin is {mc_ror:.4f} (>20%). Do not deploy this strategy."
        )
        recommendations.append(
            "The strategy is almost certain to blow up with current parameters."
        )
        recommendations.append(
            "Either dramatically reduce position size or improve the strategy's edge."
        )

    if config.cost_per_trade > 0.005:
        recommendations.append(
            f"Transaction costs ({config.cost_per_trade:.3%}) are high. "
            "Consider reducing trading frequency."
        )

    if kelly_optimal <= 0:
        recommendations.append(
            "Kelly optimal size is 0 or negative — the strategy has no edge. "
            "Do not trade."
        )

    return RiskOfRuinReport(
        config=config,
        mc_result=mc_result,
        analytical_ror=round(analytical_ror, 6),
        kelly_optimal_size=round(kelly_optimal, 6),
        recommended_max_position=round(recommended_max, 6),
        verdict=verdict,
        recommendations=recommendations,
    )
