"""
DCC-GARCH — Dynamic Conditional Correlation with univariate GARCH volatilities.

Pure-Python implementation (no R dependency required).
Uses the `arch` package for univariate GARCH(1,1) on each asset, then
computes the DCC correlation matrix via the Engle (2002) two-step estimator.

Formula (Engle 2002, Journal of Business & Economic Statistics):
    Step 1: GARCH(1,1) for each asset i:
        sigma_{i,t}^2 = omega_i + alpha_i * epsilon_{i,t-1}^2 + beta_i * sigma_{i,t-1}^2

    Step 2: DCC(1,1) correlation:
        Q_t = (1 - a - b) * Qbar + a * (epsilon_{t-1} * epsilon_{t-1}') + b * Q_{t-1}
        R_t = diag(Q_t)^{-1/2} * Q_t * diag(Q_t)^{-1/2}

Usage:
    from quant_nanggroe.engine.risk import DCCGARCH

    dcc = DCCGARCH()
    corr_matrix, vols = dcc.fit(returns_df)  # returns_df: (n_days x n_assets)
    forecast_corr = dcc.forecast(horizon=1)

References:
    - Engle (2002): "Dynamic Conditional Correlation: A Simple Class of
      Multivariate Generalized Autoregressive Conditional Heteroskedasticity Models"
    - The `arch` package for univariate GARCH estimation
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Helper: GARCH(1,1) volatility forecast
# ══════════════════════════════════════════════════════════════════════


def garch_vol_forecast(
    returns: np.ndarray,
    horizon: int = 1,
) -> np.ndarray:
    """
    Fit GARCH(1,1) on a returns series and forecast volatility.

    Args:
        returns: 1D array of historical returns.
        horizon: Number of steps ahead to forecast (default: 1).

    Returns:
        Array of forecasted volatilities (standard deviations) for each step ahead.
        Returns [0.0] if fitting fails.
    """
    try:
        from arch import arch_model

        model = arch_model(returns * 100, vol="Garch", p=1, q=1, dist="normal")
        res = model.fit(disp="off", update_freq=0)
        # Forecast variance
        forecast = res.forecast(horizon=horizon)
        var_forecast = forecast.variance.values[-1] / 10000  # scale back
        # Ensure non-negative
        var_forecast = np.maximum(var_forecast, 1e-12)
        return np.sqrt(var_forecast)
    except Exception as e:
        logger.debug("GARCH vol forecast failed: %s", e)
        # Fallback: rolling standard deviation
        if len(returns) > 5:
            return np.full(horizon, float(np.std(returns[-60:])))
        return np.full(horizon, 0.01)


# ══════════════════════════════════════════════════════════════════════
#  Helper: Compute DCC correlation matrix from standardized residuals
# ══════════════════════════════════════════════════════════════════════


def compute_dcc_corr(
    residuals: np.ndarray,
    a: float = 0.05,
    b: float = 0.90,
) -> np.ndarray:
    """
    Compute the DCC(1,1) correlation matrix from standardized residuals.

    Args:
        residuals: (n_days x n_assets) array of standardized residuals
                   (returns / conditional vol).
        a: DCC parameter for the innovation term (default: 0.05).
        b: DCC parameter for the persistence term (default: 0.90).

    Returns:
        (n_assets x n_assets) dynamic correlation matrix R_t at the last time step.
    """
    # Unconditional correlation matrix Qbar
    Qbar = np.cov(residuals, rowvar=False)
    Qbar = _nearest_pd(Qbar)

    # Initialize Q_t = Qbar
    Q_t = Qbar.copy()

    # Iterate through time to update DCC dynamics
    for t in range(1, len(residuals)):
        eps_t = residuals[t - 1: t]  # (1 x n_assets)
        innovation = eps_t.T @ eps_t  # (n_assets x n_assets)
        Q_t = (1 - a - b) * Qbar + a * innovation + b * Q_t

    # Convert Q_t to correlation matrix R_t
    D_inv = np.diag(1.0 / np.sqrt(np.maximum(np.diag(Q_t), 1e-12)))
    R_t = D_inv @ Q_t @ D_inv

    # Ensure symmetry and positive semi-definiteness
    R_t = (R_t + R_t.T) / 2.0
    R_t = _nearest_pd(R_t)

    return R_t


# ══════════════════════════════════════════════════════════════════════
#  Helper: Nearest Positive Semi-Definite Matrix
# ══════════════════════════════════════════════════════════════════════


def _nearest_pd(matrix: np.ndarray) -> np.ndarray:
    """
    Find the nearest positive semi-definite matrix.

    Uses eigenvalue clipping: negative eigenvalues are set to a small positive.

    Args:
        matrix: Input matrix (should be symmetric).

    Returns:
        Positive semi-definite matrix.
    """
    try:
        eigvals, eigvecs = np.linalg.eigh((matrix + matrix.T) / 2.0)
        eigvals = np.maximum(eigvals, 1e-12)
        return eigvecs @ np.diag(eigvals) @ eigvecs.T
    except np.linalg.LinAlgError:
        # Fallback: add small diagonal perturbation
        n = matrix.shape[0]
        return matrix + 1e-6 * np.eye(n)


# ══════════════════════════════════════════════════════════════════════
#  Volatility-Regulated Kelly (VRK) using DCC-GARCH
# ══════════════════════════════════════════════════════════════════════


def dcc_kelly_weights(
    expected_returns: np.ndarray,
    dcc_corr: np.ndarray,
    vols: np.ndarray,
    target_vol: float = 0.15,
    safety_factor: float = 0.25,
    max_single_asset_pct: float = 0.25,
    max_risk_per_trade: float = 0.005,
) -> np.ndarray:
    """
    Compute Volatility-Regulated Kelly weights from DCC-GARCH estimates.

    Full pipeline:
        1. Build covariance: Sigma = diag(vols) * R * diag(vols)
        2. Standard Kelly: w = inv(Sigma) * mu
        3. Scale down if portfolio vol > target_vol
        4. Apply safety factor (fractional Kelly)
        5. Clamp each asset to max_single_asset_pct
        6. Cap risk per trade at max_risk_per_trade (0.5%)

    Args:
        expected_returns: (n_assets,) array of expected returns.
        dcc_corr: (n_assets x n_assets) DCC correlation matrix.
        vols: (n_assets,) array of GARCH forecast volatilities (annualized).
        target_vol: Target portfolio annualized volatility (default: 15%).
        safety_factor: Fractional Kelly safety factor lambda (default: 0.25).
        max_single_asset_pct: Max allocation per asset (default: 25%).
        max_risk_per_trade: Max risk per trade as fraction of capital (default: 0.5%).

    Returns:
        (n_assets,) array of portfolio weights (fraction of capital per asset).
    """
    n = len(expected_returns)

    # 1. Build covariance matrix from vols + DCC correlation
    vol_diag = np.diag(vols)
    cov_matrix = vol_diag @ dcc_corr @ vol_diag
    cov_matrix = _nearest_pd(cov_matrix)

    # 2. Standard Kelly: w = inv(Sigma) * mu
    try:
        inv_cov = np.linalg.inv(cov_matrix + 1e-8 * np.eye(n))
    except np.linalg.LinAlgError:
        inv_cov = np.linalg.pinv(cov_matrix + 1e-8 * np.eye(n))
    raw_kelly = inv_cov @ expected_returns

    # 3. Scale down if portfolio volatility exceeds target
    port_vol = np.sqrt(raw_kelly @ cov_matrix @ raw_kelly)
    if port_vol > target_vol and port_vol > 0:
        raw_kelly *= target_vol / port_vol

    # 4. Apply safety factor (fractional Kelly)
    weights = raw_kelly * safety_factor

    # 5. Clamp each asset
    weights = np.clip(weights, -max_single_asset_pct, max_single_asset_pct)

    # 6. Cap total risk per trade at max_risk_per_trade (0.5%)
    total_risk = np.sum(np.abs(weights))
    if total_risk > max_risk_per_trade:
        weights = weights * (max_risk_per_trade / total_risk)

    return weights


# ══════════════════════════════════════════════════════════════════════
#  DCCGARCH Class — Full estimator with state
# ══════════════════════════════════════════════════════════════════════


class DCCGARCH:
    """
    Dynamic Conditional Correlation — GARCH volatility & correlation estimator.

    Fits univariate GARCH(1,1) for each asset, then computes DCC(1,1)
    correlations. Supports rolling re-estimation for live updates.

    Usage:
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(returns_df)

        # Get latest correlation + vols
        corr = dcc.correlation
        vols = dcc.volatilities

        # Get Kelly-optimal weights
        weights = dcc.kelly_weights(expected_returns=np.array([...]))
    """

    def __init__(
        self,
        dcc_a: float = 0.05,
        dcc_b: float = 0.90,
        garch_p: int = 1,
        garch_q: int = 1,
        target_vol: float = 0.15,
        safety_factor: float = 0.25,
    ):
        """
        Args:
            dcc_a: DCC innovation parameter alpha (default: 0.05).
            dcc_b: DCC persistence parameter beta  (default: 0.90).
            garch_p: GARCH lag order p (default: 1).
            garch_q: GARCH lag order q (default: 1).
            target_vol: Target portfolio annualized vol (default: 15%).
            safety_factor: Fractional Kelly safety factor (default: 0.25).
        """
        self.dcc_a = dcc_a
        self.dcc_b = dcc_b
        self.garch_p = garch_p
        self.garch_q = garch_q
        self.target_vol = target_vol
        self.safety_factor = safety_factor

        # State (set after fit)
        self._volatilities: np.ndarray | None = None
        self._correlation: np.ndarray | None = None
        self._covariance: np.ndarray | None = None
        self._asset_names: list[str] | None = None
        self._fitted = False

    # ── Properties ────────────────────────────────────────────────

    @property
    def volatilities(self) -> np.ndarray:
        """Latest forecast volatilities (n_assets,)."""
        if self._volatilities is None:
            return np.array([])
        return self._volatilities

    @property
    def correlation(self) -> np.ndarray:
        """Latest DCC correlation matrix (n_assets x n_assets)."""
        if self._correlation is None:
            return np.array([[]])
        return self._correlation

    @property
    def covariance(self) -> np.ndarray:
        """Latest covariance matrix (n_assets x n_assets)."""
        if self._covariance is None:
            return np.array([[]])
        return self._covariance

    @property
    def asset_names(self) -> list[str]:
        """Names of assets in the model."""
        return self._asset_names or []

    @property
    def fitted(self) -> bool:
        """True if the model has been fitted."""
        return self._fitted

    # ── Fit ───────────────────────────────────────────────────────

    def fit(
        self,
        returns: pd.DataFrame | np.ndarray,
        asset_names: Optional[list[str]] = None,
    ) -> "DCCGARCH":
        """
        Fit DCC-GARCH on historical returns.

        Step 1 (per asset): Fit GARCH(1,1) → conditional volatilities.
        Step 2 (cross-section): Standardize residuals → DCC correlation.

        Args:
            returns: (n_days x n_assets) DataFrame or array of returns.
            asset_names: Optional list of asset names (required if returns is ndarray).

        Returns:
            Self for chaining.
        """
        if isinstance(returns, pd.DataFrame):
            self._asset_names = list(returns.columns)
            data = returns.values
        else:
            data = np.asarray(returns)
            self._asset_names = asset_names or [f"asset_{i}" for i in range(data.shape[1])]

        n_days, n_assets = data.shape

        if n_days < 30 or n_assets < 1:
            logger.warning(
                "DCC-GARCH: insufficient data (%d days, %d assets)", n_days, n_assets
            )
            self._fitted = False
            return self

        # ── Step 1: GARCH(1,1) per asset ─────────────────────────
        vols = np.zeros(n_assets)
        standardized_residuals = np.zeros_like(data)

        for i in range(n_assets):
            asset_returns = data[:, i]
            try:
                # Fit GARCH and forecast vol
                garch_vol = garch_vol_forecast(asset_returns, horizon=1)
                vols[i] = garch_vol[0] if len(garch_vol) > 0 else 0.01

                # Compute conditional vols for each time step
                from arch import arch_model
                model = arch_model(asset_returns * 100, vol="Garch", p=1, q=1)
                res = model.fit(disp="off", update_freq=0)
                cond_vol = res.conditional_volatility.values / 100  # scale back

                # Standardized residuals
                with np.errstate(divide="ignore", invalid="ignore"):
                    std_resid = asset_returns / np.maximum(cond_vol, 1e-12)
                    std_resid = np.where(np.isfinite(std_resid), std_resid, 0.0)
                standardized_residuals[:, i] = std_resid

            except Exception as e:
                logger.debug("GARCH fail for asset %s: %s", self._asset_names[i], e)
                vols[i] = float(np.std(asset_returns[-60:])) if len(asset_returns) > 5 else 0.01
                standardized_residuals[:, i] = asset_returns / max(vols[i], 1e-12)

        # ── Step 2: DCC correlation ──────────────────────────────
        try:
            corr_matrix = compute_dcc_corr(
                residuals=standardized_residuals,
                a=self.dcc_a,
                b=self.dcc_b,
            )
        except Exception as e:
            logger.warning("DCC correlation failed, using EWMA: %s", e)
            # Fallback: EWMA correlation
            corr_matrix = pd.DataFrame(data).ewm(span=20).corr().values[-1]
            corr_matrix = corr_matrix.reshape(n_assets, n_assets)
            corr_matrix = _nearest_pd((corr_matrix + corr_matrix.T) / 2.0)

        # ── Build covariance ─────────────────────────────────────
        vol_diag = np.diag(vols)
        cov_matrix = vol_diag @ corr_matrix @ vol_diag
        cov_matrix = _nearest_pd(cov_matrix)

        # ── Store state ──────────────────────────────────────────
        self._volatilities = vols
        self._correlation = corr_matrix
        self._covariance = cov_matrix
        self._fitted = True

        logger.info(
            "DCC-GARCH fitted: %d assets, mean vol=%.2f%%, "
            "mean corr=%.2f",
            n_assets,
            float(np.mean(vols) * 100),
            float(np.mean(corr_matrix[np.triu_indices(n_assets, k=1)])),
        )
        return self

    # ── Volatility-Regulated Kelly ───────────────────────────────

    def kelly_weights(
        self,
        expected_returns: np.ndarray,
        target_vol: Optional[float] = None,
        safety_factor: Optional[float] = None,
    ) -> np.ndarray:
        """
        Compute Volatility-Regulated Kelly weights using the fitted DCC-GARCH.

        Args:
            expected_returns: (n_assets,) expected returns vector.
            target_vol: Override target portfolio volatility (default: self.target_vol).
            safety_factor: Override safety factor (default: self.safety_factor).

        Returns:
            (n_assets,) portfolio weights. Zeros if not fitted.
        """
        if not self._fitted:
            logger.warning("DCC-GARCH not fitted — returning zero weights")
            return np.zeros(len(expected_returns))

        return dcc_kelly_weights(
            expected_returns=expected_returns,
            dcc_corr=self._correlation,
            vols=self._volatilities,
            target_vol=target_vol or self.target_vol,
            safety_factor=safety_factor or self.safety_factor,
        )

    # ── Status / Diagnostics ─────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Return a diagnostic summary of the fitted model."""
        if not self._fitted:
            return {"fitted": False, "n_assets": 0}

        n = len(self._volatilities)
        return {
            "fitted": True,
            "n_assets": n,
            "asset_names": self._asset_names,
            "mean_vol_pct": round(float(np.mean(self._volatilities) * 100), 2),
            "max_vol_pct": round(float(np.max(self._volatilities) * 100), 2),
            "min_vol_pct": round(float(np.min(self._volatilities) * 100), 2),
            "mean_corr": round(
                float(np.mean(self._correlation[np.triu_indices(n, k=1)])), 4
            ),
            "max_corr": round(float(np.max(self._correlation)), 4),
            "min_corr": round(float(np.min(self._correlation)), 4),
            "dcc_a": self.dcc_a,
            "dcc_b": self.dcc_b,
        }


# ══════════════════════════════════════════════════════════════════════
#  Convenience function: full pipeline from returns to optimized weights
# ══════════════════════════════════════════════════════════════════════


def dcc_garch_pipeline(
    returns: pd.DataFrame,
    expected_returns: np.ndarray,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Run full DCC-GARCH pipeline: fit → correlation → VRK weights.

    Args:
        returns: (n_days x n_assets) historical returns.
        expected_returns: (n_assets,) expected returns.
        **kwargs: Passed through to DCCGARCH constructor.

    Returns:
        Dict with 'correlation', 'volatilities', 'covariance', 'weights', 'status'.
    """
    dcc = DCCGARCH(**kwargs)
    dcc.fit(returns)
    weights = dcc.kelly_weights(expected_returns)

    return {
        "correlation": dcc.correlation,
        "volatilities": dcc.volatilities,
        "covariance": dcc.covariance,
        "weights": weights,
        "status": dcc.get_status(),
    }
