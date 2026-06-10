"""
Fama-French 5-Factor Model
============================
Implementation of the Fama-French (2015) five-factor asset pricing model
for cross-sectional stock analysis using OHLCV price/volume data.

Factors:
    - MKT_RF: Market Risk Premium — excess return over risk-free proxy
    - SMB:    Small Minus Big — size factor (small-cap premium)
    - HML:    High Minus Low  — value factor (book-to-market premium)
    - RMW:    Robust Minus Weak — profitability factor
    - CMA:    Conservative Minus Aggressive — investment factor

Since pure Fama-French factors require fundamental data (book equity,
operating profitability, asset growth), this module provides price-based
proxies grounded in the academic literature. Each factor is computed as
a cross-sectionally z-scored signal suitable for long-short ranking.

References:
    Fama, E. F., & French, K. R. (1993). "Common risk factors in the
    returns on stocks and bonds." Journal of Financial Economics, 33(1), 3-56.

    Fama, E. F., & French, K. R. (2015). "A five-factor asset pricing model."
    Journal of Financial Economics, 116(1), 1-22.

    Sharpe, W. F. (1964). "Capital Asset Prices: A Theory of Market Equilibrium
    under Conditions of Risk." The Journal of Finance, 19(3), 425-442.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# CROSS-SECTIONAL UTILITIES
# ══════════════════════════════════════════════════════════════════════


def _cross_sectional_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Per-row z-score: ``(x - row_mean) / row_std``.

    Rows with zero or NaN standard deviation produce NaN for every element
    (no silent inf or zero).
    """
    mean = df.mean(axis=1, skipna=True)
    std = df.std(axis=1, ddof=1, skipna=True)
    centered = df.sub(mean, axis=0)
    result = centered.div(std.where(std > 0), axis=0)
    return result.replace([np.inf, -np.inf], np.nan)


def _safe_div(
    numerator: pd.DataFrame,
    denominator: pd.DataFrame,
    eps: float = 1e-12,
) -> pd.DataFrame:
    """Safe division: ``numerator / (denominator + eps * sign(denominator))``.

    Where ``denominator == 0`` exactly (or NaN), result is NaN.
    """
    denom_arr = denominator.to_numpy(dtype=np.float64, na_value=np.nan)
    sign = np.sign(denom_arr)
    denom_adjusted = denom_arr + eps * sign
    denom_df = pd.DataFrame(denom_adjusted, index=denominator.index, columns=denominator.columns)
    result = numerator.div(denom_df)
    return result.replace([np.inf, -np.inf], np.nan)


# ══════════════════════════════════════════════════════════════════════
# INDIVIDUAL FACTOR COMPUTE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════


def compute_mkt_rf(
    close: pd.DataFrame,
    window: int = 21,
) -> pd.DataFrame:
    """Compute MKT_RF (Market Risk Premium) factor.

    Price-based proxy: 21-day total return cross-sectionally z-scored.
    Top z-scores = strong recent winners; bottom = losers.

    Args:
        close: Wide DataFrame (index=dates, columns=instruments) of close prices.
        window: Lookback window in trading days for return calculation.
            Default 21 (≈1 month of trading days).

    Returns:
        DataFrame of cross-sectional z-scores, same shape as *close*.
        Warmup rows (first *window* rows) are NaN.
    """
    if window < 1:
        raise ValueError(f"MKT_RF window must be >= 1, got {window}")

    ret = _safe_div(close - close.shift(window), close.shift(window))
    return _cross_sectional_zscore(ret)


def compute_smb(
    close: pd.DataFrame,
    volume: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """Compute SMB (Small Minus Big) size factor.

    Price-based proxy: inverse log of *window*-day average dollar volume.
    Small caps typically have low dollar volume; higher z-scores = smaller
    (less liquid) names.

    Args:
        close: Wide DataFrame of close prices.
        volume: Wide DataFrame of volumes (same shape as *close*).
        window: Rolling mean window for dollar-volume averaging. Default 60.

    Returns:
        DataFrame of cross-sectional z-scores.
    """
    if window < 1:
        raise ValueError(f"SMB window must be >= 1, got {window}")

    dollar_volume = volume * close
    avg = dollar_volume.rolling(window=window, min_periods=window).mean()
    log_size = np.log(avg + 1.0)
    return _cross_sectional_zscore(-log_size)


def compute_hml(
    close: pd.DataFrame,
    window: int = 252,
) -> pd.DataFrame:
    """Compute HML (High Minus Low) value factor.

    Price-based proxy: negative trailing *window*-day return (long-term
    reversal). Value names tend to be long-term underperformers whose
    prices have declined relative to book value. Higher z-scores = larger
    long-term drawdowns (deeper value).

    Args:
        close: Wide DataFrame of close prices.
        window: Lookback for total return. Default 252 (≈1 year).

    Returns:
        DataFrame of cross-sectional z-scores. Short panels produce
        all-NaN (insufficient history is surfaced rather than a shrunk value).
    """
    if window < 1:
        raise ValueError(f"HML window must be >= 1, got {window}")

    ret = _safe_div(close - close.shift(window), close.shift(window))
    return _cross_sectional_zscore(-ret)


def compute_rmw(
    close: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """Compute RMW (Robust Minus Weak) profitability factor.

    Price-based proxy: negative trailing *window*-day realized return
    volatility. Robust (profitable) firms historically exhibit lower
    idiosyncratic volatility (the "low-vol anomaly" overlap).
    Higher z-scores = lower volatility = quality proxy.

    Args:
        close: Wide DataFrame of close prices.
        window: Rolling window for volatility estimation. Default 60.

    Returns:
        DataFrame of cross-sectional z-scores.
    """
    if window < 2:
        raise ValueError(f"RMW window must be >= 2 (need at least 2 points for std), got {window}")

    ret_1d = _safe_div(close - close.shift(1), close.shift(1))
    vol = ret_1d.rolling(window=window, min_periods=window).std(ddof=1)
    return _cross_sectional_zscore(-vol)


def compute_cma(
    volume: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """Compute CMA (Conservative Minus Aggressive) investment factor.

    Price-based proxy: negative *window*-day change in log average volume.
    Firms aggressively scaling activity tend to show rising trading volume;
    conservative firms show stable/shrinking volume.
    Higher z-scores = volume contraction (conservative).

    Args:
        volume: Wide DataFrame of volumes.
        window: Rolling mean window and delta lag. Default 60.

    Returns:
        DataFrame of cross-sectional z-scores.
    """
    if window < 1:
        raise ValueError(f"CMA window must be >= 1, got {window}")

    avg = volume.rolling(window=window, min_periods=window).mean()
    log_avg = np.log(avg + 1.0)
    growth = log_avg - log_avg.shift(window)
    return _cross_sectional_zscore(-growth)


# ══════════════════════════════════════════════════════════════════════
# FACTOR REGISTRY (mirrors alpha101 ALPHA_FACTORS pattern)
# ══════════════════════════════════════════════════════════════════════


FAMA_FRENCH_FACTORS: dict[str, Any] = {
    "MKT_RF": compute_mkt_rf,
    "SMB": compute_smb,
    "HML": compute_hml,
    "RMW": compute_rmw,
    "CMA": compute_cma,
}


# ══════════════════════════════════════════════════════════════════════
# FACTOR METADATA
# ══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class FactorInfo:
    """Metadata about a single Fama-French factor."""

    name: str
    full_name: str
    description: str
    columns_required: list[str]
    default_window: int
    min_warmup_bars: int
    reference: str


FACTOR_INFO: dict[str, FactorInfo] = {
    "MKT_RF": FactorInfo(
        name="MKT_RF",
        full_name="Market Risk Premium",
        description="21-day total return, cross-sectionally z-scored",
        columns_required=["close"],
        default_window=21,
        min_warmup_bars=21,
        reference="Sharpe (1964); Fama & French (1993)",
    ),
    "SMB": FactorInfo(
        name="SMB",
        full_name="Small Minus Big",
        description="Inverse log 60-day dollar-volume z-score (size proxy)",
        columns_required=["close", "volume"],
        default_window=60,
        min_warmup_bars=60,
        reference="Fama & French (1993)",
    ),
    "HML": FactorInfo(
        name="HML",
        full_name="High Minus Low",
        description="Inverse 252-day return z-score (value / long-term reversal proxy)",
        columns_required=["close"],
        default_window=252,
        min_warmup_bars=252,
        reference="Fama & French (1993)",
    ),
    "RMW": FactorInfo(
        name="RMW",
        full_name="Robust Minus Weak",
        description="Inverse 60-day return-volatility z-score (profitability / quality proxy)",
        columns_required=["close"],
        default_window=60,
        min_warmup_bars=60,
        reference="Fama & French (2015)",
    ),
    "CMA": FactorInfo(
        name="CMA",
        full_name="Conservative Minus Aggressive",
        description="Inverse 60-day log-volume change z-score (investment proxy)",
        columns_required=["volume"],
        default_window=60,
        min_warmup_bars=120,
        reference="Fama & French (2015)",
    ),
}


# ══════════════════════════════════════════════════════════════════════
# REGRESSION RESULT
# ══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class FactorRegressionResult:
    """Result of an OLS factor regression.

    Attributes:
        alphas: Intercept (annualised if *annualise* is True).
        betas: Dict mapping factor name to its coefficient.
        t_stats: Dict mapping factor name to its t-statistic.
        r_squared: In-sample R².
        adj_r_squared: Adjusted R².
        residual_std: Standard deviation of residuals.
        n_observations: Number of usable observations after dropping NaN.
        factor_names: Ordered list of factor names used in the regression.
    """

    alphas: float
    betas: dict[str, float]
    t_stats: dict[str, float]
    r_squared: float
    adj_r_squared: float
    residual_std: float
    n_observations: int
    factor_names: list[str]


# ══════════════════════════════════════════════════════════════════════
# FAMA-FRENCH MODEL
# ══════════════════════════════════════════════════════════════════════


class FamaFrenchModel:
    """Combined Fama-French 5-factor model.

    Provides a unified interface for computing all five factors and running
    cross-sectional OLS regressions of asset returns against factor exposures.

    The model operates on **wide** DataFrames where ``index = trading_date``
    and ``columns = instrument_code``, consistent with the Alpha Zoo convention.

    Args:
        mkt_rf_window: Lookback for market return. Default 21.
        smb_window: Lookback for dollar-volume average. Default 60.
        hml_window: Lookback for value reversal. Default 252.
        rmw_window: Lookback for profitability volatility. Default 60.
        cma_window: Lookback for investment volume growth. Default 60.

    Example::

        model = FamaFrenchModel()
        factors = model.compute_all(panel)
        reg = model.factor_regression(
            returns=returns_df,
            factors=factors,
        )
        print(reg.betas, reg.r_squared)
    """

    def __init__(
        self,
        mkt_rf_window: int = 21,
        smb_window: int = 60,
        hml_window: int = 252,
        rmw_window: int = 60,
        cma_window: int = 60,
    ) -> None:
        self._windows = {
            "MKT_RF": mkt_rf_window,
            "SMB": smb_window,
            "HML": hml_window,
            "RMW": rmw_window,
            "CMA": cma_window,
        }

        # Validate windows
        for name, w in self._windows.items():
            min_val = 2 if name == "RMW" else 1
            if w < min_val:
                raise ValueError(
                    f"Window for {name} must be >= {min_val}, got {w}"
                )

    # ── Factor Computation ────────────────────────────────────────────

    def compute_mkt_rf(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute MKT_RF factor from a data panel."""
        return compute_mkt_rf(panel["close"], window=self._windows["MKT_RF"])

    def compute_smb(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute SMB factor from a data panel."""
        return compute_smb(
            panel["close"], panel["volume"], window=self._windows["SMB"]
        )

    def compute_hml(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute HML factor from a data panel."""
        return compute_hml(panel["close"], window=self._windows["HML"])

    def compute_rmw(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute RMW factor from a data panel."""
        return compute_rmw(panel["close"], window=self._windows["RMW"])

    def compute_cma(self, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Compute CMA factor from a data panel."""
        return compute_cma(panel["volume"], window=self._windows["CMA"])

    def compute_all(self, panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """Compute all five Fama-French factors.

        Args:
            panel: Dict with at least ``close`` and ``volume`` keys,
                each mapping to a wide DataFrame. For the full 5-factor
                model both are required; if ``volume`` is missing, SMB
                and CMA will be all-NaN DataFrames.

        Returns:
            Dict mapping factor name to its DataFrame of z-scores.
            Keys: ``MKT_RF``, ``SMB``, ``HML``, ``RMW``, ``CMA``.
        """
        close = panel.get("close")
        volume = panel.get("volume")

        if close is None:
            raise KeyError("panel must contain 'close' for Fama-French computation")

        results: dict[str, pd.DataFrame] = {}

        # MKT_RF — only needs close
        results["MKT_RF"] = self.compute_mkt_rf(panel)

        # HML — only needs close
        results["HML"] = self.compute_hml(panel)

        # RMW — only needs close
        results["RMW"] = self.compute_rmw(panel)

        # SMB — needs close + volume
        if volume is not None:
            results["SMB"] = self.compute_smb(panel)
        else:
            logger.warning("panel missing 'volume'; SMB factor will be all-NaN")
            results["SMB"] = pd.DataFrame(
                np.nan, index=close.index, columns=close.columns
            )

        # CMA — needs volume
        if volume is not None:
            results["CMA"] = self.compute_cma(panel)
        else:
            logger.warning("panel missing 'volume'; CMA factor will be all-NaN")
            results["CMA"] = pd.DataFrame(
                np.nan, index=close.index, columns=close.columns
            )

        logger.info(
            "Computed %d Fama-French factors: %s",
            len(results),
            ", ".join(results.keys()),
        )

        return results

    # ── Factor Regression ─────────────────────────────────────────────

    def factor_regression(
        self,
        returns: pd.DataFrame,
        factors: dict[str, pd.DataFrame],
        factor_names: list[str] | None = None,
        annualise: bool = True,
        trading_days: int = 252,
    ) -> dict[str, FactorRegressionResult]:
        """Run OLS regression of per-instrument returns against factor values.

        For each instrument (column), regresses its return series onto the
        factor z-scores:

            R_i = alpha + b1*MKT_RF + b2*SMB + b3*HML + b4*RMW + b5*CMA + e

        Uses numpy OLS (normal equations) — no statsmodels dependency required.

        Args:
            returns: Wide DataFrame of asset returns (same index/columns
                convention as factor DataFrames).
            factors: Dict mapping factor name to DataFrame, typically the
                output of :meth:`compute_all`.
            factor_names: Subset of factors to use. If ``None``, all five
                are used.
            annualise: If ``True``, alpha is annualised by multiplying by
                ``trading_days``. Default ``True``.
            trading_days: Number of trading days per year for annualisation.
                Default 252.

        Returns:
            Dict mapping instrument name to its :class:`FactorRegressionResult`.
        """
        if factor_names is None:
            factor_names = [name for name in FAMA_FACTORS_ORDER if name in factors]

        if not factor_names:
            raise ValueError("No factor names provided or found in factors dict")

        # Stack factors into a 3D structure: (dates, factors)
        # and align with returns index
        factor_dfs = [factors[name] for name in factor_names]
        common_index = returns.index
        for fdf in factor_dfs:
            common_index = common_index.intersection(fdf.index)

        if len(common_index) < len(factor_names) + 2:
            logger.warning(
                "Insufficient overlapping dates (%d) for regression with %d factors",
                len(common_index),
                len(factor_names),
            )
            return {}

        results: dict[str, FactorRegressionResult] = {}

        for instrument in returns.columns:
            try:
                reg = self._regress_single(
                    y=returns.loc[common_index, instrument],
                    factor_dfs=[fdf.loc[common_index, instrument] for fdf in factor_dfs],
                    factor_names=factor_names,
                    annualise=annualise,
                    trading_days=trading_days,
                )
                results[instrument] = reg
            except Exception as exc:
                logger.debug(
                    "Regression failed for %s: %s", instrument, exc
                )
                continue

        logger.info(
            "Factor regression completed for %d / %d instruments",
            len(results),
            len(returns.columns),
        )

        return results

    @staticmethod
    def _regress_single(
        y: pd.Series,
        factor_dfs: list[pd.Series],
        factor_names: list[str],
        annualise: bool,
        trading_days: int,
    ) -> FactorRegressionResult:
        """OLS regression for a single instrument.

        Uses the normal equation: β = (X'X)⁻¹ X'y
        Standard errors from: Var(β) = σ² (X'X)⁻¹
        """
        # Build design matrix
        k = len(factor_names)
        y_vals = y.to_numpy(dtype=np.float64)

        # Stack factor series into X matrix with intercept
        x_cols = [np.ones(len(y_vals))]
        for fs in factor_dfs:
            x_cols.append(fs.to_numpy(dtype=np.float64))
        X = np.column_stack(x_cols)

        # Drop rows with any NaN
        mask = ~(np.isnan(y_vals) | np.isnan(X).any(axis=1))
        y_clean = y_vals[mask]
        X_clean = X[mask]

        n = len(y_clean)
        if n < k + 2:
            raise ValueError(f"Insufficient clean observations: {n} < {k + 2}")

        # Normal equations
        XtX = X_clean.T @ X_clean
        Xty = X_clean.T @ y_clean

        try:
            beta = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            # Singular matrix — use pseudoinverse
            beta = np.linalg.lstsq(X_clean, y_clean, rcond=None)[0]

        # Residuals
        residuals = y_clean - X_clean @ beta
        residual_var = np.sum(residuals ** 2) / max(n - k - 1, 1)
        residual_std = float(np.sqrt(residual_var))

        # R² and adjusted R²
        ss_total = np.sum((y_clean - y_clean.mean()) ** 2)
        ss_residual = np.sum(residuals ** 2)
        r_squared = 1.0 - ss_residual / ss_total if ss_total > 0 else 0.0
        adj_r_squared = (
            1.0 - (1.0 - r_squared) * (n - 1) / max(n - k - 1, 1)
            if n > k + 1 else 0.0
        )

        # Standard errors and t-stats
        try:
            XtX_inv = np.linalg.inv(XtX)
        except np.linalg.LinAlgError:
            XtX_inv = np.linalg.pinv(XtX)

        se = np.sqrt(np.diag(XtX_inv) * residual_var)
        t_stats_vals = beta / np.where(se > 0, se, np.nan)

        # Extract results (beta[0] = intercept, beta[1:] = factor coefficients)
        alpha = float(beta[0])
        if annualise:
            alpha *= trading_days

        betas = {name: float(beta[i + 1]) for i, name in enumerate(factor_names)}
        t_stats = {name: float(t_stats_vals[i + 1]) for i, name in enumerate(factor_names)}

        return FactorRegressionResult(
            alphas=alpha,
            betas=betas,
            t_stats=t_stats,
            r_squared=float(r_squared),
            adj_r_squared=float(adj_r_squared),
            residual_std=residual_std,
            n_observations=n,
            factor_names=list(factor_names),
        )


# Canonical factor ordering for display and regression
FAMA_FACTORS_ORDER: list[str] = ["MKT_RF", "SMB", "HML", "RMW", "CMA"]
