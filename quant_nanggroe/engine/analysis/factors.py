"""Multi-factor regression framework for strategy returns attribution.

Decomposes strategy returns into factor exposures (market, momentum, volatility,
size, trend) and computes risk-adjusted alpha via OLS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

# ── Built-in factor constructors ─────────────────────────────────────────

class MarketFactor:
    """Market return factor — proxied by the portfolio return itself."""

    def __init__(self) -> None:
        self.name = "Market"

    def compute(self, returns: pd.Series) -> pd.Series:
        return returns


class MomentumFactor:
    """12-1 month momentum (skip one month)."""

    def __init__(self, lookback: int = 252, skip: int = 21) -> None:
        self.lookback = lookback
        self.skip = skip
        self.name = "Momentum"

    def compute(self, returns: pd.Series) -> pd.Series:
        price = (1 + returns).cumprod()
        mom = price / price.shift(self.lookback + self.skip) - 1
        return mom


class VolatilityFactor:
    """Inverse volatility — low-vol anomaly factor."""

    def __init__(self, window: int = 60) -> None:
        self.window = window
        self.name = "Volatility"

    def compute(self, returns: pd.Series) -> pd.Series:
        vol = returns.rolling(self.window).std()
        inv = 1.0 / vol
        return inv.replace([np.inf, -np.inf], np.nan)


class SizeFactor:
    """Size effect proxied by inverse log price."""

    def __init__(self) -> None:
        self.name = "Size"

    def compute(self, returns: pd.Series) -> pd.Series:
        price = (1 + returns).cumprod()
        return -np.log(price)


class TrendFactor:
    """Time-series momentum — sign of recent return."""

    def __init__(self, window: int = 21) -> None:
        self.window = window
        self.name = "Trend"

    def compute(self, returns: pd.Series) -> pd.Series:
        rolling = returns.rolling(self.window).mean()
        return np.sign(rolling)


# ── OLS helpers ──────────────────────────────────────────────────────────

def _ols_estimate(y: np.ndarray, X: np.ndarray) -> tuple:
    n, k = X.shape
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    residuals = y - X @ beta
    mse = np.sum(residuals ** 2) / (n - k)
    try:
        xtxi = np.linalg.inv(X.T @ X)
        var_beta = mse * xtxi
        se = np.sqrt(np.diag(var_beta))
    except np.linalg.LinAlgError:
        se = np.full(k, np.nan)
    t_stats = beta / se if not np.any(np.isnan(se)) else np.full(k, np.nan)
    p_values = 2 * (1 - sp_stats.t.cdf(np.abs(t_stats), n - k))
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k)
    if k > 1 and ss_res > 0:
        ss_reg = ss_tot - ss_res
        f_stat = (ss_reg / (k - 1)) / (ss_res / (n - k))
    else:
        f_stat = 0.0
    return beta, t_stats, p_values, r_squared, adj_r_squared, f_stat, residuals


# ── Result container ─────────────────────────────────────────────────────

@dataclass
class FactorResult:
    """Result of a multi-factor regression fit."""
    factors: Dict[str, float]  # factor name → coefficient
    t_stats: Dict[str, float]
    p_values: Dict[str, float]
    alpha: float
    alpha_t_stat: float
    alpha_p_value: float
    r_squared: float
    adj_r_squared: float
    f_stat: float
    residuals: np.ndarray
    n_obs: int = 0
    n_factors: int = 0

    def __post_init__(self) -> None:
        self.n_factors = len(self.factors)


# ── FactorModel ──────────────────────────────────────────────────────────

class FactorModel:
    """Multi-factor regression model for strategy returns attribution.

    Decomposes strategy returns into factor exposures and computes
    risk-adjusted alpha.

    Usage:
        model = FactorModel()
        result = model.fit(returns, factors_df)
        print(model.summary())
    """

    def __init__(self) -> None:
        self._custom_factors: Dict[str, pd.Series] = {}
        self._result: Optional[FactorResult] = None
        self._factor_names: List[str] = []

    def add_factor(self, name: str, series: pd.Series) -> None:
        """Register a custom factor series for later use."""
        self._custom_factors[name] = series

    def fit(
        self,
        returns: pd.Series,
        factors_df: pd.DataFrame,
        add_constant: bool = True,
    ) -> FactorResult:
        """Run OLS regression of returns on factors.

        Args:
            returns: Strategy returns Series (index aligned with factors_df).
            factors_df: Factor exposures DataFrame. Each column is a factor.
            add_constant: If True, includes an intercept (alpha).

        Returns:
            FactorResult with coefficients, t-stats, p-values, alpha, R².
        """
        merged = pd.concat({"__return__": returns, **{c: factors_df[c] for c in factors_df.columns}}, axis=1)
        merged = merged.dropna()

        if len(merged) < 3:
            raise ValueError(f"Only {len(merged)} valid observations after dropping NaN — need at least 3")

        y = merged["__return__"].values
        factor_cols = [c for c in merged.columns if c != "__return__"]
        X_raw = merged[factor_cols].values
        self._factor_names = factor_cols

        if add_constant:
            X = np.column_stack([np.ones(len(X_raw)), X_raw])
            const_idx = 0
            factor_offset = 1
        else:
            X = X_raw
            const_idx = -1
            factor_offset = 0

        beta, t_stats, p_values, r2, adj_r2, f_stat, residuals = _ols_estimate(y, X)

        factor_beta = {
            name: float(beta[factor_offset + i])
            for i, name in enumerate(factor_cols)
        }
        factor_t = {
            name: float(t_stats[factor_offset + i])
            for i, name in enumerate(factor_cols)
        }
        factor_p = {
            name: float(p_values[factor_offset + i])
            for i, name in enumerate(factor_cols)
        }

        if add_constant:
            alpha = float(beta[const_idx])
            alpha_t = float(t_stats[const_idx])
            alpha_p = float(p_values[const_idx])
        else:
            alpha = 0.0
            alpha_t = 0.0
            alpha_p = 1.0

        self._result = FactorResult(
            factors=factor_beta,
            t_stats=factor_t,
            p_values=factor_p,
            alpha=alpha,
            alpha_t_stat=alpha_t,
            alpha_p_value=alpha_p,
            r_squared=float(r2),
            adj_r_squared=float(adj_r2),
            f_stat=float(f_stat),
            residuals=residuals,
            n_obs=len(y),
            n_factors=len(factor_cols),
        )
        return self._result

    def summary(self) -> str:
        """Return a formatted table of factor exposures."""
        if self._result is None:
            return "No model fitted yet — call .fit() first."

        r = self._result

        header = f"{'Factor':<20} {'Coef':>10} {'t-stat':>10} {'p-value':>10} {'Signif':>8}"
        sep = "-" * len(header)

        rows = [header, sep]
        for name in self._factor_names:
            coef = r.factors.get(name, 0.0)
            tst = r.t_stats.get(name, 0.0)
            pv = r.p_values.get(name, 1.0)
            sig = "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.10 else ""
            rows.append(f"{name:<20} {coef:>10.4f} {tst:>10.4f} {pv:>10.4f} {sig:>8}")

        rows.append(sep)
        rows.append(f"{'Alpha':<20} {r.alpha:>10.4f} {r.alpha_t_stat:>10.4f} {r.alpha_p_value:>10.4f}")
        rows.append("")
        rows.append(f"R²: {r.r_squared:.4f}   Adj R²: {r.adj_r_squared:.4f}   F: {r.f_stat:.4f}   N: {r.n_obs}")
        return "\n".join(rows)

    def plot_weights(self, top_n: int = 10) -> str:
        """ASCII bar chart of factor loadings."""
        if self._result is None:
            return "No model fitted yet."

        sorted_factors = sorted(
            self._result.factors.items(), key=lambda x: abs(x[1]), reverse=True
        )[:top_n]

        max_abs = max(abs(v) for _, v in sorted_factors) if sorted_factors else 1.0
        scale = 30 / max_abs if max_abs != 0 else 1.0

        lines = ["Factor Loadings (ASCII bar chart):", ""]
        for name, coef in sorted_factors:
            bar_len = max(1, int(abs(coef) * scale))
            bar = "█" * bar_len
            sign = "+" if coef >= 0 else "-"
            lines.append(f"{name:<20} {sign}{bar} {coef:>8.4f}")

        return "\n".join(lines)

    def result(self) -> Optional[FactorResult]:
        return self._result


def get_builtin_factors() -> Dict[str, Any]:
    """Return dict of built-in factor constructors."""
    return {
        "Market": MarketFactor,
        "Momentum": MomentumFactor,
        "Volatility": VolatilityFactor,
        "Size": SizeFactor,
        "Trend": TrendFactor,
    }
