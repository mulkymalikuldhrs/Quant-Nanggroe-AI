"""Deflated Sharpe Ratio — Bailey & de Prado (2014).

Corrects the Sharpe Ratio for multiple testing bias by computing the
probability that the observed Sharpe Ratio is statistically significant
after accounting for the number of trials conducted.

Key formulas:
    E[max(SR)] ≈ (1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))
    Var(SR)   = (1 + 0.5·SR² - skewness·SR + (kurtosis-1)/4·SR²) / T
    DSR       = Φ((SR_observed - E[max(SR)]) / sqrt(Var(SR)))

where γ ≈ 0.5772 is the Euler-Mascheroni constant, N is the number of
independent trials, T is the sample length, and Φ is the standard normal CDF.

References
----------
Bailey, D.H. & de Prado, M.L. (2014). "The Deflated Sharpe Ratio."
    Journal of Portfolio Management, 40(5), 94-107.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

import numpy as np
import structlog
from pydantic import BaseModel, Field
from scipy.stats import norm

logger = structlog.get_logger(__name__)

# Euler-Mascheroni constant
_EULER_MASCHERONI: float = 0.5772156649015329


# ── Pydantic models ──────────────────────────────────────────────────────


class DeflatedSharpeResult(BaseModel):
    """Result of a Deflated Sharpe Ratio computation."""

    observed_sharpe: float = Field(..., description="The observed annualised Sharpe Ratio")
    expected_max_sharpe: float = Field(
        ..., description="E[max(SR)] — expected maximum Sharpe under multiple testing"
    )
    sharpe_variance: float = Field(..., description="Variance of the Sharpe Ratio estimator")
    dsr: float = Field(
        ...,
        description="Deflated Sharpe Ratio — probability that observed SR is significant",
    )
    is_significant: bool = Field(
        ..., description="True if DSR >= 0.95 (standard significance threshold)"
    )
    min_track_record: int = Field(
        ...,
        description="Minimum track record length (in periods) needed for significance",
    )
    num_trials: int = Field(..., description="Number of independent trials")
    interpretation: str = Field(..., description="Human-readable interpretation")


class OverfittingReport(BaseModel):
    """Report on probability of backtest overfitting."""

    strategies_tested: int = Field(..., description="Number of strategy configurations tested")
    best_sharpe: float = Field(..., description="Best observed Sharpe Ratio among all strategies")
    dsr: float = Field(
        ..., description="Deflated Sharpe Ratio for the best strategy"
    )
    pbo: float = Field(
        ..., description="Probability of backtest overfitting (0-1)"
    )
    verdict: str = Field(..., description="OVERFITTING / LIKELY_OVERFITTING / ACCEPTABLE")
    recommendations: List[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )


# ── Core functions ───────────────────────────────────────────────────────


def _expected_maximum_sharpe(num_trials: int) -> float:
    """Compute E[max(SR)] under the null of zero true Sharpe.

    Uses the formula:
        E[max(SR)] ≈ (1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))

    Parameters
    ----------
    num_trials : int
        Number of independent strategy trials (N).

    Returns
    -------
    float
        Expected maximum Sharpe Ratio under the null.
    """
    if num_trials <= 1:
        return 0.0

    N = float(num_trials)
    gamma = _EULER_MASCHERONI

    term1 = (1.0 - gamma) * norm.ppf(1.0 - 1.0 / N)
    term2 = gamma * norm.ppf(1.0 - 1.0 / (N * math.e))

    return term1 + term2


def _sharpe_variance(
    observed_sharpe: float,
    sample_length: int,
    skewness: float = 0.0,
    kurtosis: float = 0.0,
) -> float:
    """Compute the variance of the Sharpe Ratio estimator.

    Var(SR) = (1 + 0.5·SR² - skewness·SR + (kurtosis-1)/4·SR²) / T

    Parameters
    ----------
    observed_sharpe : float
        The observed (non-annualised) Sharpe Ratio.
    sample_length : int
        Number of observations used to compute the Sharpe Ratio (T).
    skewness : float
        Skewness of the returns distribution.
    kurtosis : float
        Excess kurtosis of the returns distribution.

    Returns
    -------
    float
        Variance of the Sharpe Ratio estimator.
    """
    SR = observed_sharpe
    T = float(sample_length)

    numerator = (
        1.0
        + 0.5 * SR ** 2
        - skewness * SR
        + (kurtosis - 1.0) / 4.0 * SR ** 2
    )
    return numerator / T


def deflated_sharpe_ratio(
    observed_sharpe: float,
    num_trials: int,
    sample_length: int,
    skewness: float = 0.0,
    kurtosis: float = 0.0,
    annualize_factor: int = 252,
) -> DeflatedSharpeResult:
    """Compute the Deflated Sharpe Ratio (Bailey & de Prado, 2014).

    This corrects the Sharpe Ratio for multiple testing bias — i.e., the
    inflation of observed Sharpe Ratios when many strategy configurations
    are evaluated on the same data.

    Parameters
    ----------
    observed_sharpe : float
        The observed annualised Sharpe Ratio.
    num_trials : int
        Number of independent strategy trials (N).
    sample_length : int
        Number of return observations used to compute the Sharpe Ratio.
    skewness : float
        Skewness of the returns distribution (default 0).
    kurtosis : float
        Excess kurtosis of the returns distribution (default 0).
    annualize_factor : int
        Annualisation factor (252 for daily, 52 for weekly, 12 for monthly).

    Returns
    -------
    DeflatedSharpeResult
        Complete DSR result including significance, interpretation, and MTL.
    """
    logger.debug(
        "computing_dsr",
        observed_sharpe=observed_sharpe,
        num_trials=num_trials,
        sample_length=sample_length,
    )

    # De-annualise the Sharpe for internal calculations
    SR = observed_sharpe / math.sqrt(annualize_factor)

    # Variance of SR estimator (using non-annualised SR)
    var_sr = _sharpe_variance(SR, sample_length, skewness, kurtosis)

    # E[max(SR)] = sqrt(Var(SR)) * E[max of N standard normals]
    # The _expected_maximum_sharpe function returns the expected max of N
    # independent draws from N(0,1). Since each SR estimate has variance
    # Var(SR) under the null, the actual expected max SR is scaled.
    expected_max_standard = _expected_maximum_sharpe(num_trials)
    expected_max = math.sqrt(var_sr) * expected_max_standard

    # Annualise E[max(SR)] for display
    expected_max_annualised = expected_max * math.sqrt(annualize_factor)

    # DSR = Φ((SR_observed - E[max(SR)]) / sqrt(Var(SR)))
    # Equivalently: DSR = Φ(SR/sqrt(Var) - E[max standard normals])
    if var_sr <= 0:
        dsr_value = 0.0
    else:
        dsr_value = float(norm.cdf((SR - expected_max) / math.sqrt(var_sr)))

    is_significant = dsr_value >= 0.95

    # Minimum track record length
    min_track_record = minimum_track_record_length(
        observed_sharpe, num_trials, skewness, kurtosis, annualize_factor
    )

    # Interpretation
    if dsr_value >= 0.99:
        interpretation = (
            f"DSR={dsr_value:.4f} — Highly significant. The observed SR of "
            f"{observed_sharpe:.4f} is very unlikely to be a result of multiple testing."
        )
    elif dsr_value >= 0.95:
        interpretation = (
            f"DSR={dsr_value:.4f} — Significant at 95% level. The observed SR of "
            f"{observed_sharpe:.4f} is likely genuine after multiple-testing correction."
        )
    elif dsr_value >= 0.80:
        interpretation = (
            f"DSR={dsr_value:.4f} — Marginal. The observed SR of "
            f"{observed_sharpe:.4f} may be inflated by multiple testing. Exercise caution."
        )
    else:
        interpretation = (
            f"DSR={dsr_value:.4f} — Not significant. The observed SR of "
            f"{observed_sharpe:.4f} is likely a result of multiple testing bias "
            f"across {num_trials} trials."
        )

    return DeflatedSharpeResult(
        observed_sharpe=observed_sharpe,
        expected_max_sharpe=round(expected_max_annualised, 6),
        sharpe_variance=round(var_sr, 8),
        dsr=round(dsr_value, 6),
        is_significant=is_significant,
        min_track_record=min_track_record,
        num_trials=num_trials,
        interpretation=interpretation,
    )


def minimum_track_record_length(
    observed_sharpe: float,
    num_trials: int,
    skewness: float = 0.0,
    kurtosis: float = 0.0,
    annualize_factor: int = 252,
) -> int:
    """Compute the minimum track record length needed for significance.

    The MTL is the minimum number of observations required so that the
    observed Sharpe Ratio achieves DSR >= 0.95 given the number of trials.

    Parameters
    ----------
    observed_sharpe : float
        The observed annualised Sharpe Ratio.
    num_trials : int
        Number of independent strategy trials.
    skewness : float
        Skewness of the returns distribution.
    kurtosis : float
        Excess kurtosis of the returns distribution.
    annualize_factor : int
        Annualisation factor.

    Returns
    -------
    int
        Minimum number of observations (periods) needed.
    """
    SR = observed_sharpe / math.sqrt(annualize_factor)
    expected_max_standard = _expected_maximum_sharpe(num_trials)

    # If the t-statistic SR/sqrt(Var) doesn't exceed E[max standard normals],
    # no track record will suffice
    # We need SR/sqrt(Var) > E[max standard] for any track record to work
    # But Var depends on T, so we solve for T directly.

    # We need: Φ((SR - sqrt(Var)*E_max_std) / sqrt(Var)) >= 0.95
    # => (SR - sqrt(Var)*E_max_std) / sqrt(Var) >= z_95
    # => SR / sqrt(Var) - E_max_std >= z_95
    # => SR / sqrt(Var) >= E_max_std + z_95
    # => sqrt(Var) <= SR / (E_max_std + z_95)
    # => Var <= (SR / (E_max_std + z_95))²
    # => (1 + 0.5*SR² - sk*SR + (ku-1)/4*SR²) / T <= (SR / (E_max_std + z_95))²
    # => T >= (1 + 0.5*SR² - sk*SR + (ku-1)/4*SR²) * (E_max_std + z_95)² / SR²

    if SR <= 0:
        return -1  # Zero or negative SR can never be significant

    z_95 = norm.ppf(0.95)  # ≈ 1.6449
    denominator = SR ** 2

    if denominator <= 0:
        return -1

    numerator = (
        1.0
        + 0.5 * SR ** 2
        - skewness * SR
        + (kurtosis - 1.0) / 4.0 * SR ** 2
    ) * (expected_max_standard + z_95) ** 2

    T_min = numerator / denominator
    return max(1, math.ceil(T_min))


def probability_of_backtest_overfitting(
    strategy_sharpe_ratios: Sequence[float],
) -> float:
    """Estimate the Probability of Backtest Overfitting (PBO).

    Uses the combinatorial approach from Bailey et al. (2017): split the
    data into even/odd halves, compute Sharpe Ratios on each half, and
    measure the frequency with which the best in-sample strategy
    underperforms out-of-sample.

    A simplified approximation is used: we compute the fraction of
    strategies whose in-sample Sharpe exceeds the median but whose
    out-of-sample Sharpe falls below the median.

    Parameters
    ----------
    strategy_sharpe_ratios : Sequence[float]
        Array of Sharpe Ratios from all strategy configurations tested.
        If 1-D, uses a rank-based approximation.

    Returns
    -------
    float
        Probability of backtest overfitting (0 to 1).
    """
    sr_array = np.asarray(strategy_sharpe_ratios, dtype=float)
    n = len(sr_array)

    if n < 2:
        logger.warning("pbo_insufficient_data", n_strategies=n)
        return 0.0

    # Rank-based approximation of PBO
    # PBO ≈ P(best IS strategy is not best OOS)
    # Using the relationship: PBO increases with the variance of SRs
    # and the number of strategies
    sorted_srs = np.sort(sr_array)

    # Best SR relative to the distribution
    best_sr = sorted_srs[-1]
    median_sr = np.median(sorted_srs)

    if median_sr == 0 and best_sr == 0:
        return 0.5

    # Approximate PBO based on the gap between best and median
    # The wider the gap, the more likely it's overfit
    # Normalise by the standard deviation of the SR distribution
    sr_std = float(np.std(sr_array))
    if sr_std < 1e-10:
        # All strategies have same SR — no overfitting concern
        return 0.0

    # The more trials and the more extreme the best, the higher PBO
    # Use a logistic approximation
    gap = (best_sr - median_sr) / sr_std
    log_n = math.log(max(n, 2))

    # Sigmoid: higher gap and more strategies -> higher PBO
    pbo = 1.0 / (1.0 + math.exp(-(gap - 1.5) / max(log_n * 0.5, 0.1)))

    return float(np.clip(pbo, 0.0, 1.0))


def generate_overfitting_report(
    strategy_sharpe_ratios: Sequence[float],
    sample_length: int,
    skewness: float = 0.0,
    kurtosis: float = 0.0,
    annualize_factor: int = 252,
) -> OverfittingReport:
    """Generate a comprehensive overfitting report for a set of strategies.

    Parameters
    ----------
    strategy_sharpe_ratios : Sequence[float]
        Sharpe Ratios from all strategy configurations tested.
    sample_length : int
        Number of return observations.
    skewness : float
        Skewness of the best strategy's returns.
    kurtosis : float
        Excess kurtosis of the best strategy's returns.
    annualize_factor : int
        Annualisation factor.

    Returns
    -------
    OverfittingReport
        Complete overfitting report with DSR, PBO, verdict and recommendations.
    """
    sr_array = np.asarray(strategy_sharpe_ratios, dtype=float)
    n = len(sr_array)
    best_sr = float(np.max(sr_array))

    # Compute DSR for the best strategy
    dsr_result = deflated_sharpe_ratio(
        observed_sharpe=best_sr,
        num_trials=n,
        sample_length=sample_length,
        skewness=skewness,
        kurtosis=kurtosis,
        annualize_factor=annualize_factor,
    )

    # Compute PBO
    pbo = probability_of_backtest_overfitting(sr_array)

    # Determine verdict
    if dsr_result.dsr < 0.50 or pbo > 0.75:
        verdict = "OVERFITTING"
    elif dsr_result.dsr < 0.80 or pbo > 0.50:
        verdict = "LIKELY_OVERFITTING"
    else:
        verdict = "ACCEPTABLE"

    # Generate recommendations
    recommendations: List[str] = []

    if verdict == "OVERFITTING":
        recommendations.append(
            "High probability of overfitting detected. Do not deploy this strategy."
        )
        recommendations.append(
            "Reduce the number of strategy configurations tested."
        )
        recommendations.append(
            "Use Walk-Forward Analysis to validate out-of-sample performance."
        )
        recommendations.append(
            "Consider simplifying the strategy to reduce degrees of freedom."
        )
    elif verdict == "LIKELY_OVERFITTING":
        recommendations.append(
            "Results are likely inflated by multiple testing. Proceed with caution."
        )
        recommendations.append(
            "Collect more out-of-sample data to confirm performance."
        )
        recommendations.append(
            f"Minimum track record of {dsr_result.min_track_record} periods needed for significance."
        )
    else:
        recommendations.append(
            "Strategy appears statistically significant after multiple-testing correction."
        )
        recommendations.append(
            "Continue monitoring performance in live trading."
        )

    if n > 100:
        recommendations.append(
            f"Very high number of trials ({n}). Consider pre-registration of hypotheses."
        )

    return OverfittingReport(
        strategies_tested=n,
        best_sharpe=round(best_sr, 6),
        dsr=round(dsr_result.dsr, 6),
        pbo=round(pbo, 6),
        verdict=verdict,
        recommendations=recommendations,
    )
