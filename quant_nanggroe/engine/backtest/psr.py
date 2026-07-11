"""Probabilistic Sharpe Ratio (PSR) & Deflated Sharpe Ratio (DSR).

Statistical tests that account for non-normal return distributions and
multiple testing (data snooping) bias.

PSR → probability that true Sharpe > benchmark given observed skew/kurtosis.
DSR → PSR adjusted for the number of independent trials (strategy count).

References:
    - Bailey & López de Prado (2012), "The Sharpe Ratio Efficient Frontier"
    - Bailey et al. (2014), "The Deflated Sharpe Ratio: Correction for Multiple Testing"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class PSRResult:
    psr: float
    sharpe_observed: float
    sharpe_benchmark: float
    skewness: float
    kurtosis: float
    n_observations: int
    is_significant: bool


@dataclass
class DSRResult:
    dsr: float
    psr: float
    sharpe_observed: float
    sharpe_threshold: float
    num_trials: int
    num_independent_trials: int
    is_significant: bool


@dataclass
class ValidationReport:
    strategy_name: str
    psr: PSRResult
    dsr: Optional[DSRResult]
    sharpe_annualized: float
    num_trades: int
    notes: List[str] = field(default_factory=list)


def estimate_sharpe(returns: np.ndarray, annual_factor: float = 252.0) -> float:
    """Compute annualized Sharpe ratio from a return series."""
    if len(returns) < 2:
        return 0.0
    excess = returns - returns.mean()  # excess is same as returns if rf=0 (common in crypto)
    return returns.mean() / returns.std() * np.sqrt(annual_factor) if returns.std() > 0 else 0.0


def _moments(returns: np.ndarray) -> tuple[float, float]:
    """Compute skewness and excess kurtosis of a return series."""
    n = len(returns)
    if n < 3:
        return 0.0, 0.0
    std = returns.std(ddof=1)
    if std == 0:
        return 0.0, 0.0
    demeaned = returns - returns.mean()
    skew = np.mean(demeaned ** 3) / (std ** 3)
    kurt = np.mean(demeaned ** 4) / (std ** 4) - 3.0
    return float(skew), float(kurt)


def probabilistic_sharpe_ratio(
    returns: np.ndarray,
    sharpe_benchmark: float = 0.0,
    annual_factor: float = 252.0,
) -> PSRResult:
    """Compute the Probabilistic Sharpe Ratio (PSR).

    ``PSR = Z{ (SR_obs - SR_bench) * sqrt(N-1) / sqrt(1 - skew*SR + (kurt-1)/4 * SR^2) }``

    where ``Z`` is the standard normal CDF.

    Args:
        returns: Array of periodic returns (e.g., daily).
        sharpe_benchmark: Benchmark Sharpe to exceed. 0.0 means any positive Sharpe.
        annual_factor: Number of periods per year for annualization.

    Returns:
        PSRResult with the PSR and significance decision.
    """
    n = len(returns)
    if n < 3:
        return PSRResult(0.0, 0.0, sharpe_benchmark, 0.0, 0.0, n, False)

    sr_obs = estimate_sharpe(returns, annual_factor)
    skew, kurt = _moments(returns)

    # Standard error adjustment
    numerator = sr_obs - sharpe_benchmark
    denom_term = max(1.0 - skew * sr_obs + (kurt - 1.0) / 4.0 * sr_obs ** 2, 1e-8)
    denom = np.sqrt(denom_term / (n - 1))

    z = numerator / denom
    psr = float(stats.norm.cdf(z))
    is_sig = psr > 0.95  # 95% confidence

    return PSRResult(psr, sr_obs, sharpe_benchmark, skew, kurt, n, is_sig)


def _estimate_num_independent_trials(num_strategies: int, correlation: float = 0.5) -> int:
    """Estimate effective number of independent trials.

    When strategies share data (same historical period, overlapping assets),
    the effective number is lower than the raw count.

    Uses a simple shrinkage: ``N_eff = N / (1 + rho * (N - 1))``
    """
    if num_strategies <= 1:
        return 1
    return max(1, int(num_strategies / (1.0 + correlation * (num_strategies - 1))))


def _expected_maximum_sharpe(num_trials: int, num_observations: int) -> float:
    """Estimate the expected maximum Sharpe ratio under the null (no alpha).

    Uses the approximation from Bailey et al. (2014):

    ``E[max(SR)] ~ (1 - gamma) * Z{1 - 1/N} + gamma * Z{1 - 1/(N*e)}``

    where gamma ≈ 0.5772 (Euler-Mascheroni constant) and Z is the normal PPF.
    """
    if num_trials <= 1 or num_observations < 3:
        return 0.0

    gamma = 0.5772156649
    z1 = stats.norm.ppf(1.0 - 1.0 / num_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (num_trials * np.e))

    e_max_sr = (1.0 - gamma) * z1 + gamma * z2
    # Scale by standard error
    se = 1.0 / np.sqrt(num_observations - 1)
    return float(e_max_sr * se)


def deflated_sharpe_ratio(
    returns: np.ndarray,
    num_trials: int = 1,
    num_observations: Optional[int] = None,
    annual_factor: float = 252.0,
    correlation: float = 0.5,
) -> DSRResult:
    """Compute the Deflated Sharpe Ratio (DSR).

    ``DSR = PSR{SR_threshold = E[max(SR) | N, T]}``

    Uses the expected maximum Sharpe given the number of trials as the
    benchmark, adjusting for the inflation caused by multiple testing.

    Args:
        returns: Array of periodic returns.
        num_trials: Number of strategies/parameter combinations tested.
        num_observations: Length of return series (defaults to len(returns)).
        annual_factor: Number of periods per year.
        correlation: Average correlation between strategy returns.

    Returns:
        DSRResult with DSR value and significance decision.
    """
    n = num_observations or len(returns)
    ind_trials = _estimate_num_independent_trials(num_trials, correlation)
    sr_threshold = _expected_maximum_sharpe(ind_trials, n)

    psr_result = probabilistic_sharpe_ratio(returns, sr_threshold, annual_factor)
    is_sig = psr_result.psr > 0.95

    return DSRResult(
        dsr=psr_result.psr,
        psr=psr_result.psr,
        sharpe_observed=psr_result.sharpe_observed,
        sharpe_threshold=sr_threshold,
        num_trials=num_trials,
        num_independent_trials=ind_trials,
        is_significant=is_sig,
    )


def validate_backtest_metrics(
    strategy_name: str,
    returns: np.ndarray,
    num_trials: int = 1,
    annual_factor: float = 252.0,
) -> ValidationReport:
    """Full statistical validation for a backtested strategy.

    Computes PSR + DSR (if num_trials > 1) and generates diagnostic notes.

    Args:
        strategy_name: Name of the strategy being validated.
        returns: Array of periodic returns.
        num_trials: Number of strategies tested in the research process.
        annual_factor: Number of periods per year.

    Returns:
        ValidationReport with all results and interpretation notes.
    """
    psr_result = probabilistic_sharpe_ratio(returns, 0.0, annual_factor)
    dsr_result = None
    notes: List[str] = []

    sharpe_ann = estimate_sharpe(returns, annual_factor)
    n = len(returns)

    if n < 30:
        notes.append(f"Insufficient observations ({n}); results unreliable")
    elif n < 100:
        notes.append(f"Marginal sample size ({n}); bootstrap recommended")

    if abs(psr_result.skewness) > 1.0:
        notes.append(f"High skewness ({psr_result.skewness:.2f}); Sharpe may mislead")
    if psr_result.kurtosis > 3.0:
        notes.append(f"Fat tails (kurtosis={psr_result.kurtosis:.2f}); expect tail risk")

    if psr_result.is_significant:
        notes.append(f"PSR={psr_result.psr:.3f} (>0.95): statistically significant alpha (SR>{psr_result.sharpe_benchmark:.2f})")
    else:
        notes.append(f"PSR={psr_result.psr:.3f} (≤0.95): cannot reject SR<={psr_result.sharpe_benchmark:.2f}")

    if num_trials > 1:
        dsr_result = deflated_sharpe_ratio(returns, num_trials, n, annual_factor)
        if dsr_result.is_significant:
            notes.append(f"DSR={dsr_result.dsr:.3f}: survives multiple-testing correction ({num_trials} trials)")
        else:
            notes.append(
                f"DSR={dsr_result.dsr:.3f}: fails multiple-testing correction "
                f"(expected max SR by chance={dsr_result.sharpe_threshold:.3f})"
            )

    return ValidationReport(
        strategy_name=strategy_name,
        psr=psr_result,
        dsr=dsr_result,
        sharpe_annualized=sharpe_ann,
        num_trades=n,
        notes=notes,
    )


def psr_vs_sharpe(
    returns: np.ndarray,
    sharpe_range: np.ndarray,
    annual_factor: float = 252.0,
) -> np.ndarray:
    """Compute PSR for a range of benchmark Sharpe values.

    Useful for plotting the "PSR efficient frontier."

    Args:
        returns: Array of periodic returns.
        sharpe_range: Array of benchmark Sharpe values to test.
        annual_factor: Number of periods per year.

    Returns:
        Array of PSR values corresponding to each benchmark Sharpe.
    """
    skew, kurt = _moments(returns)
    n = len(returns)
    if n < 3:
        return np.zeros_like(sharpe_range)
    sr_obs = estimate_sharpe(returns, annual_factor)

    results = np.zeros_like(sharpe_range)
    for i, sr_bench in enumerate(sharpe_range):
        num = sr_obs - sr_bench
        denom = np.sqrt(max((1.0 - skew * sr_obs + (kurt - 1.0) / 4.0 * sr_obs ** 2) / (n - 1), 1e-8))
        results[i] = stats.norm.cdf(num / denom)

    return results
