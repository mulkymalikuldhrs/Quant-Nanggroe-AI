"""Bootstrap confidence intervals for Sharpe ratio and other metrics.

Uses stationary bootstrap (block bootstrap) to account for autocorrelation
in financial returns.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from quant_nanggroe.engine.analysis.factors import FactorModel


def _stationary_bootstrap(
    data: np.ndarray,
    block_size: int,
    n_bootstrap: int,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Generate stationary bootstrap samples.

    Samples random blocks of geometric(mean=block_size) length,
    concatenates until >= original length, then trims.

    Supports both 1D arrays (n,) and 2D arrays (n, k) — returns
    the same shape as input with the first dimension bootstrapped.
    """
    if rng is None:
        rng = np.random.default_rng()
    is_1d = data.ndim == 1
    n = len(data)
    if is_1d:
        samples = np.zeros((n_bootstrap, n))
    else:
        samples = np.zeros((n_bootstrap, n, data.shape[1]))

    for i in range(n_bootstrap):
        indices: list[int] = []
        while len(indices) < n:
            start = rng.integers(0, n)
            block_len = int(rng.geometric(1.0 / max(block_size, 1)))
            for j in range(block_len):
                indices.append((start + j) % n)
                if len(indices) >= n:
                    break
        samples[i] = np.asarray(data)[indices[:n]]

    return samples


class BootstrapCI:
    """Bootstrap confidence intervals on Sharpe ratio and other metrics.

    Uses stationary bootstrap to preserve autocorrelation structure.

    Usage:
        ci = BootstrapCI()
        result = ci.sharpe_ci(returns)
    """

    @staticmethod
    def sharpe_ratio(returns: np.ndarray, annual_factor: int = 252) -> float:
        """Compute annualized Sharpe ratio.

        Args:
            returns: Array of periodic returns.
            annual_factor: Number of periods per year (252 for daily).

        Returns:
            Annualized Sharpe ratio.
        """
        if len(returns) < 2:
            return 0.0
        mean_ret = np.mean(returns)
        std_ret = np.std(returns, ddof=1)
        if std_ret == 0:
            return 0.0
        return mean_ret / std_ret * np.sqrt(annual_factor)

    def sharpe_ci(
        self,
        returns: pd.Series,
        confidence: float = 0.95,
        n_bootstrap: int = 10_000,
        block_size: Optional[int] = None,
        annual_factor: int = 252,
    ) -> Dict[str, float]:
        """Bootstrap confidence interval for annualized Sharpe ratio.

        Args:
            returns: Series of periodic returns.
            confidence: Confidence level (e.g. 0.95 for 95% CI).
            n_bootstrap: Number of bootstrap replications.
            block_size: Mean block length for stationary bootstrap.
                Defaults to int(sqrt(len(returns))).
            annual_factor: Annualization factor.

        Returns:
            Dict with lower, upper, point_estimate, std_error, ci_method.
        """
        arr = returns.dropna().to_numpy(dtype=float)
        n = len(arr)

        if n < 3:
            return {
                "lower": float("nan"),
                "upper": float("nan"),
                "point_estimate": BootstrapCI.sharpe_ratio(arr, annual_factor),
                "std_error": float("nan"),
                "ci_method": "bootstrap_stationary",
                "n_bootstrap": n_bootstrap,
                "block_size": 0,
                "confidence": confidence,
            }

        if block_size is None:
            block_size = max(1, int(np.sqrt(n)))

        point = BootstrapCI.sharpe_ratio(arr, annual_factor)

        samples = _stationary_bootstrap(arr, block_size, n_bootstrap)
        sharpe_samples = np.array([
            BootstrapCI.sharpe_ratio(sample, annual_factor) for sample in samples
        ])

        alpha = 1 - confidence
        lower = float(np.percentile(sharpe_samples, 100 * alpha / 2))
        upper = float(np.percentile(sharpe_samples, 100 * (1 - alpha / 2)))
        std_err = float(np.std(sharpe_samples, ddof=1))

        return {
            "lower": round(lower, 6),
            "upper": round(upper, 6),
            "point_estimate": round(point, 6),
            "std_error": round(std_err, 6),
            "ci_method": "bootstrap_stationary",
            "n_bootstrap": n_bootstrap,
            "block_size": block_size,
            "confidence": confidence,
        }

    def alpha_ci(
        self,
        returns: pd.Series,
        factor_returns: pd.DataFrame,
        confidence: float = 0.95,
        n_bootstrap: int = 5_000,
        block_size: Optional[int] = None,
    ) -> Dict[str, float]:
        """Bootstrap confidence interval on regression alpha.

        Runs factor regression on each bootstrap sample and collects the
        distribution of alpha (intercept).

        Args:
            returns: Strategy returns.
            factor_returns: Factor returns DataFrame.
            confidence: Confidence level.
            n_bootstrap: Number of bootstrap replications.
            block_size: Mean block length for stationary bootstrap.

        Returns:
            Dict with lower, upper, point_estimate (from full sample),
            std_error, and p_value (H0: alpha=0).
        """
        arr_r = returns.dropna().to_numpy(dtype=float)
        arr_f = factor_returns.loc[returns.dropna().index].to_numpy(dtype=float)
        n = len(arr_r)

        if n < 3:
            return {
                "lower": float("nan"),
                "upper": float("nan"),
                "point_estimate": 0.0,
                "std_error": float("nan"),
                "p_value": 1.0,
            }

        if block_size is None:
            block_size = max(1, int(np.sqrt(n)))

        # Point estimate from full sample
        sr = returns.dropna()
        fr = factor_returns.loc[sr.index]
        model = FactorModel()
        full_result = model.fit(sr, fr)
        point_alpha = full_result.alpha

        # Bootstrap
        stacked = np.column_stack([arr_r, arr_f])
        samples = _stationary_bootstrap(stacked, block_size, n_bootstrap)
        alpha_samples = np.zeros(n_bootstrap)

        for i in range(n_bootstrap):
            boot = samples[i]
            boot_r = pd.Series(boot[:, 0])
            boot_f = pd.DataFrame(boot[:, 1:], columns=factor_returns.columns)
            try:
                m = FactorModel()
                r = m.fit(boot_r, boot_f)
                alpha_samples[i] = r.alpha
            except Exception:
                alpha_samples[i] = float("nan")

        valid = alpha_samples[~np.isnan(alpha_samples)]
        if len(valid) < 100:
            return {
                "lower": float("nan"),
                "upper": float("nan"),
                "point_estimate": round(point_alpha, 6),
                "std_error": float("nan"),
                "p_value": float("nan"),
            }

        alpha_pct = 1 - confidence
        lower = float(np.percentile(valid, 100 * alpha_pct / 2))
        upper = float(np.percentile(valid, 100 * (1 - alpha_pct / 2)))
        std_err = float(np.std(valid, ddof=1))

        # Bootstrap p-value: proportion of bootstrapped alphas with opposite sign to point
        if point_alpha > 0:
            p_value = float(np.mean(valid <= 0))
        elif point_alpha < 0:
            p_value = float(np.mean(valid >= 0))
        else:
            p_value = 1.0

        return {
            "lower": round(lower, 6),
            "upper": round(upper, 6),
            "point_estimate": round(point_alpha, 6),
            "std_error": round(std_err, 6),
            "p_value": round(p_value, 6),
            "n_bootstrap": n_bootstrap,
            "block_size": block_size,
            "confidence": confidence,
        }

    def compare_strategies(
        self,
        returns1: pd.Series,
        returns2: pd.Series,
        n_bootstrap: int = 10_000,
        block_size: Optional[int] = None,
        annual_factor: int = 252,
    ) -> Dict[str, float]:
        """Bootstrap test for difference in Sharpe ratios.

        Tests H0: Sharpe1 == Sharpe2 by bootstrapping the paired difference.

        Args:
            returns1: Returns of strategy 1.
            returns2: Returns of strategy 2.
            n_bootstrap: Number of bootstrap replications.
            block_size: Mean block length for stationary bootstrap.
            annual_factor: Annualization factor.

        Returns:
            Dict with sharpe_diff, sharpe_diff_ci, prob_diff (probability
            that strategy 1 has higher Sharpe), p_value.
        """
        common = returns1.dropna().index.intersection(returns2.dropna().index)
        if len(common) < 3:
            return {
                "sharpe1": float("nan"),
                "sharpe2": float("nan"),
                "sharpe_diff": float("nan"),
                "sharpe_diff_ci": [float("nan"), float("nan")],
                "prob_diff": float("nan"),
                "p_value": float("nan"),
            }

        r1 = returns1.loc[common].to_numpy(dtype=float)
        r2 = returns2.loc[common].to_numpy(dtype=float)

        s1 = BootstrapCI.sharpe_ratio(r1, annual_factor)
        s2 = BootstrapCI.sharpe_ratio(r2, annual_factor)
        diff = s1 - s2

        if block_size is None:
            block_size = max(1, int(np.sqrt(len(common))))

        # Bootstrap the paired difference
        stacked = np.column_stack([r1, r2])
        samples = _stationary_bootstrap(stacked, block_size, n_bootstrap)

        diff_samples = np.array([
            BootstrapCI.sharpe_ratio(s[:, 0], annual_factor)
            - BootstrapCI.sharpe_ratio(s[:, 1], annual_factor)
            for s in samples
        ])

        lower = float(np.percentile(diff_samples, 2.5))
        upper = float(np.percentile(diff_samples, 97.5))
        prob_diff = float(np.mean(diff_samples > 0))

        # Two-sided p-value
        if diff > 0:
            p_value = float(np.mean(diff_samples <= 0)) * 2
        elif diff < 0:
            p_value = float(np.mean(diff_samples >= 0)) * 2
        else:
            p_value = 1.0
        p_value = min(p_value, 1.0)

        return {
            "sharpe1": round(s1, 6),
            "sharpe2": round(s2, 6),
            "sharpe_diff": round(diff, 6),
            "sharpe_diff_ci": [round(lower, 6), round(upper, 6)],
            "prob_diff": round(prob_diff, 6),
            "p_value": round(p_value, 6),
            "n_bootstrap": n_bootstrap,
            "block_size": block_size,
        }
