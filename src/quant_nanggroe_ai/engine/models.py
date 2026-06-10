"""
Factor Models Engine
====================
From Quant-Nanggroe-AI — Multi-factor risk and return decomposition.

Implements industry-standard factor models for portfolio analysis:
  - Barra-style multi-factor model (market, size, value, momentum, volatility)
  - Fama-French 3-factor model (MKT, SMB, HML)
  - Fama-French 5-factor model (MKT, SMB, HML, RMW, CMA)
  - Cross-sectional z-score normalization
  - Factor return decomposition and risk attribution
  - Integration with factors/alpha101.py and factors/technical.py

All models follow the linear factor structure:
    r_i = α_i + Σ(β_ik * f_k) + ε_i

where r_i is asset return, β_ik is factor exposure, f_k is factor return,
and ε_i is the idiosyncratic residual.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from quant_nanggroe_ai.exceptions import InsufficientDataError, InvalidParameterError
from quant_nanggroe_ai.logging import get_logger

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════


class FactorExposure(BaseModel):
    """Factor exposure (beta/loading) for a single asset-factor pair."""

    asset: str
    factor: str
    beta: float
    t_stat: float = 0.0
    p_value: float = 1.0


class FactorReturnDecomposition(BaseModel):
    """Decomposition of an asset's return into factor contributions."""

    asset: str
    total_return: float
    factor_contributions: dict[str, float] = Field(
        default_factory=dict,
        description="Contribution of each factor to total return",
    )
    idiosyncratic_return: float = Field(
        default=0.0,
        description="Residual return not explained by factors",
    )
    r_squared: float = Field(
        default=0.0,
        description="R² of the factor model fit",
    )
    adjusted_r_squared: float = Field(default=0.0)


class RiskAttribution(BaseModel):
    """Risk attribution by factor for a portfolio."""

    total_risk: float = Field(default=0.0, description="Total portfolio volatility (annualized)")
    factor_risk: dict[str, float] = Field(
        default_factory=dict,
        description="Risk contribution of each factor",
    )
    idiosyncratic_risk: float = Field(default=0.0)
    factor_risk_pct: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage of total risk from each factor",
    )
    idiosyncratic_risk_pct: float = Field(default=0.0)


class FactorModelResult(BaseModel):
    """Complete result from a factor model estimation."""

    model_type: str
    factors: list[str] = Field(default_factory=list)
    factor_returns: dict[str, float] = Field(
        default_factory=dict,
        description="Estimated factor returns",
    )
    factor_covariance: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Factor return covariance matrix",
    )
    exposures: list[FactorExposure] = Field(default_factory=list)
    decompositions: list[FactorReturnDecomposition] = Field(default_factory=list)
    risk_attribution: RiskAttribution | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ZScoreResult(BaseModel):
    """Result of cross-sectional z-score normalization."""

    asset: str
    raw_value: float
    z_score: float
    rank: int = 0
    percentile: float = 0.0


# ══════════════════════════════════════════════════════════════════════
# BARRA MULTI-FACTOR MODEL
# ══════════════════════════════════════════════════════════════════════

# Barra-style factor definitions
BARRA_FACTORS = ["MARKET", "SIZE", "VALUE", "MOMENTUM", "VOLATILITY"]

BARRA_FACTOR_DESCRIPTIONS = {
    "MARKET": "Market risk premium (systematic risk)",
    "SIZE": "Large-cap vs small-cap return differential",
    "VALUE": "High book-to-market vs low book-to-market differential",
    "MOMENTUM": "Recent winner vs recent loser return differential",
    "VOLATILITY": "Low volatility vs high volatility return differential",
}


# ══════════════════════════════════════════════════════════════════════
# FAMA-FRENCH FACTOR DEFINITIONS
# ══════════════════════════════════════════════════════════════════════

FF3_FACTORS = ["MKT", "SMB", "HML"]

FF3_FACTOR_DESCRIPTIONS = {
    "MKT": "Market excess return (Rm - Rf)",
    "SMB": "Small Minus Big (size factor)",
    "HML": "High Minus Low (value factor)",
}

FF5_FACTORS = ["MKT", "SMB", "HML", "RMW", "CMA"]

FF5_FACTOR_DESCRIPTIONS = {
    "MKT": "Market excess return (Rm - Rf)",
    "SMB": "Small Minus Big (size factor)",
    "HML": "High Minus Low (value factor)",
    "RMW": "Robust Minus Weak (profitability factor)",
    "CMA": "Conservative Minus Aggressive (investment factor)",
}


# ══════════════════════════════════════════════════════════════════════
# FACTOR MODELS ENGINE
# ══════════════════════════════════════════════════════════════════════


class FactorModelsEngine:
    """
    Multi-factor model engine for return decomposition and risk attribution.

    Implements:
    - Barra-style multi-factor model with 5 risk factors
    - Fama-French 3-factor model (MKT, SMB, HML)
    - Fama-French 5-factor model (MKT, SMB, HML, RMW, CMA)
    - Cross-sectional z-score normalization
    - Factor return decomposition
    - Risk attribution by factor
    - Integration with factors/alpha101.py and factors/technical.py

    The engine uses OLS regression (via numpy least squares) for factor
    return estimation, with proper statistical tests (t-stats, R²).

    Example:
        engine = FactorModelsEngine()
        result = engine.fama_french_3_factor(
            asset_returns=[0.01, -0.02, 0.03, ...],
            market_returns=[0.005, -0.01, 0.02, ...],
            smb_returns=[0.002, -0.003, 0.001, ...],
            hml_returns=[-0.001, 0.004, -0.002, ...],
        )
    """

    MIN_OBSERVATIONS = 30  # Minimum data points for regression

    def __init__(self) -> None:
        self._last_result: FactorModelResult | None = None
        self._factor_history: list[FactorModelResult] = []

    @property
    def last_result(self) -> FactorModelResult | None:
        """Get the most recent factor model result."""
        return self._last_result

    # ══════════════════════════════════════════════════════════════════
    # Fama-French 3-Factor Model
    # ══════════════════════════════════════════════════════════════════

    def fama_french_3_factor(
        self,
        asset_returns: list[float],
        market_returns: list[float],
        smb_returns: list[float],
        hml_returns: list[float],
        asset_name: str = "ASSET",
    ) -> FactorModelResult:
        """
        Estimate Fama-French 3-factor model.

        Model: r_i = α + β_MKT*(Rm-Rf) + β_SMB*SMB + β_HML*HML + ε

        Args:
            asset_returns: Time series of asset excess returns
            market_returns: Time series of market excess returns (MKT factor)
            smb_returns: Time series of SMB factor returns
            hml_returns: Time series of HML factor returns
            asset_name: Name identifier for the asset

        Returns:
            FactorModelResult with estimated exposures, decompositions, and risk

        Raises:
            InsufficientDataError: If not enough observations for regression
            InvalidParameterError: If input arrays have mismatched lengths
        """
        n = len(asset_returns)
        if n < self.MIN_OBSERVATIONS:
            raise InsufficientDataError(
                required=self.MIN_OBSERVATIONS,
                actual=n,
                indicator="fama_french_3_factor",
            )

        lengths = [len(market_returns), len(smb_returns), len(hml_returns)]
        if any(l != n for l in lengths):
            raise InvalidParameterError(
                "factor_returns",
                lengths,
                f"All factor return series must have length {n}",
            )

        # Build factor matrix [1, MKT, SMB, HML]
        factor_data = {
            "MKT": market_returns,
            "SMB": smb_returns,
            "HML": hml_returns,
        }

        result = self._estimate_factor_model(
            asset_returns=asset_returns,
            factor_data=factor_data,
            model_type="FAMA_FRENCH_3",
            factor_descriptions=FF3_FACTOR_DESCRIPTIONS,
            asset_name=asset_name,
        )

        self._last_result = result
        self._factor_history.append(result)
        if len(self._factor_history) > 100:
            self._factor_history = self._factor_history[-100:]

        logger.info(
            "ff3_estimation_complete",
            asset=asset_name,
            r_squared=round(result.decompositions[0].r_squared, 4) if result.decompositions else 0,
            n_observations=n,
        )

        return result

    # ══════════════════════════════════════════════════════════════════
    # Fama-French 5-Factor Model
    # ══════════════════════════════════════════════════════════════════

    def fama_french_5_factor(
        self,
        asset_returns: list[float],
        market_returns: list[float],
        smb_returns: list[float],
        hml_returns: list[float],
        rmw_returns: list[float],
        cma_returns: list[float],
        asset_name: str = "ASSET",
    ) -> FactorModelResult:
        """
        Estimate Fama-French 5-factor model.

        Model: r_i = α + β_MKT*MKT + β_SMB*SMB + β_HML*HML
                       + β_RMW*RMW + β_CMA*CMA + ε

        Args:
            asset_returns: Time series of asset excess returns
            market_returns: Market excess returns
            smb_returns: SMB factor returns
            hml_returns: HML factor returns
            rmw_returns: RMW (profitability) factor returns
            cma_returns: CMA (investment) factor returns
            asset_name: Name identifier for the asset

        Returns:
            FactorModelResult with estimated exposures, decompositions, and risk

        Raises:
            InsufficientDataError: If not enough observations
            InvalidParameterError: If input arrays have mismatched lengths
        """
        n = len(asset_returns)
        if n < self.MIN_OBSERVATIONS:
            raise InsufficientDataError(
                required=self.MIN_OBSERVATIONS,
                actual=n,
                indicator="fama_french_5_factor",
            )

        lengths = [len(market_returns), len(smb_returns), len(hml_returns),
                    len(rmw_returns), len(cma_returns)]
        if any(l != n for l in lengths):
            raise InvalidParameterError(
                "factor_returns",
                lengths,
                f"All factor return series must have length {n}",
            )

        factor_data = {
            "MKT": market_returns,
            "SMB": smb_returns,
            "HML": hml_returns,
            "RMW": rmw_returns,
            "CMA": cma_returns,
        }

        result = self._estimate_factor_model(
            asset_returns=asset_returns,
            factor_data=factor_data,
            model_type="FAMA_FRENCH_5",
            factor_descriptions=FF5_FACTOR_DESCRIPTIONS,
            asset_name=asset_name,
        )

        self._last_result = result
        self._factor_history.append(result)
        if len(self._factor_history) > 100:
            self._factor_history = self._factor_history[-100:]

        logger.info(
            "ff5_estimation_complete",
            asset=asset_name,
            r_squared=round(result.decompositions[0].r_squared, 4) if result.decompositions else 0,
            n_observations=n,
        )

        return result

    # ══════════════════════════════════════════════════════════════════
    # Barra Multi-Factor Model
    # ══════════════════════════════════════════════════════════════════

    def barra_model(
        self,
        asset_returns: list[float],
        factor_exposures_matrix: dict[str, list[float]],
        asset_name: str = "ASSET",
    ) -> FactorModelResult:
        """
        Estimate Barra-style multi-factor model.

        The Barra model uses pre-specified factor exposures (industry and
        style factors) and estimates factor returns via cross-sectional
        regression.

        Model: r_i = Σ(β_ik * f_k) + ε_i

        where β_ik are the known exposures and f_k are the factor returns
        to be estimated.

        Args:
            asset_returns: Cross-sectional asset returns (N assets)
            factor_exposures_matrix: Dict mapping factor name to exposure vector.
                Each value is a list of N exposures for that factor.
                Must include at least 'MARKET' factor.
            asset_name: Name for the portfolio/asset context

        Returns:
            FactorModelResult with estimated factor returns and risk attribution

        Raises:
            InsufficientDataError: If insufficient data for estimation
            InvalidParameterError: If factor exposures are invalid
        """
        n_assets = len(asset_returns)
        if n_assets < len(factor_exposures_matrix) + 2:
            raise InsufficientDataError(
                required=len(factor_exposures_matrix) + 2,
                actual=n_assets,
                indicator="barra_model",
            )

        # Validate factor exposure dimensions
        for factor_name, exposures in factor_exposures_matrix.items():
            if len(exposures) != n_assets:
                raise InvalidParameterError(
                    f"factor_exposures[{factor_name}]",
                    len(exposures),
                    f"Must have length {n_assets} (same as asset_returns)",
                )

        # Build exposure matrix X (N x K)
        factor_names = list(factor_exposures_matrix.keys())
        X = np.column_stack([factor_exposures_matrix[f] for f in factor_names])

        # Add intercept
        X_with_intercept = np.column_stack([np.ones(n_assets), X])
        y = np.array(asset_returns)

        # OLS regression: f = (X'X)^{-1} X'y
        try:
            betas, residuals, rank, sv = np.linalg.lstsq(X_with_intercept, y, rcond=None)
        except np.linalg.LinAlgError:
            raise InvalidParameterError(
                "factor_exposures_matrix",
                factor_exposures_matrix,
                "Singular matrix — factor exposures may be collinear",
            )

        # Extract results
        alpha = betas[0]
        factor_returns = {factor_names[i]: float(betas[i + 1]) for i in range(len(factor_names))}

        # Compute factor covariance matrix
        factor_covariance = self._compute_factor_covariance(
            {f: [exposures[i]] for f, exposures in factor_exposures_matrix.items() for i in range(n_assets)},
            factor_names,
        )

        # Compute R²
        y_hat = X_with_intercept @ betas
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        n_factors = len(factor_names)
        adjusted_r_squared = (
            1 - (1 - r_squared) * (n_assets - 1) / (n_assets - n_factors - 1)
            if n_assets > n_factors + 1 else 0.0
        )

        # Build factor exposures list
        exposures_list = [
            FactorExposure(
                asset=asset_name,
                factor=f,
                beta=float(factor_exposures_matrix[f][i]) if i < len(factor_exposures_matrix[f]) else 0.0,
            )
            for f in factor_names
            for i in range(min(1, n_assets))  # Representative exposure
        ]

        # Build decomposition for portfolio
        factor_contributions = {
            f: round(float(factor_exposures_matrix[f][0]) * factor_returns[f], 6)
            if factor_exposures_matrix[f]
            else 0.0
            for f in factor_names
        }
        total_factor_return = sum(factor_contributions.values())
        idiosyncratic = float(np.mean(y - y_hat))

        decomposition = FactorReturnDecomposition(
            asset=asset_name,
            total_return=round(float(np.mean(asset_returns)), 6),
            factor_contributions=factor_contributions,
            idiosyncratic_return=round(idiosyncratic, 6),
            r_squared=round(r_squared, 4),
            adjusted_r_squared=round(adjusted_r_squared, 4),
        )

        # Risk attribution
        risk_attr = self._compute_risk_attribution(
            factor_returns_dict=factor_returns,
            factor_covariance=factor_covariance,
            exposures={f: float(np.mean(factor_exposures_matrix[f])) for f in factor_names},
            residual_variance=float(np.var(residuals, ddof=1)) if len(residuals) > 1 else 0.0,
        )

        result = FactorModelResult(
            model_type="BARRA",
            factors=factor_names,
            factor_returns={k: round(v, 6) for k, v in factor_returns.items()},
            factor_covariance=factor_covariance,
            exposures=exposures_list,
            decompositions=[decomposition],
            risk_attribution=risk_attr,
        )

        self._last_result = result
        self._factor_history.append(result)
        if len(self._factor_history) > 100:
            self._factor_history = self._factor_history[-100:]

        logger.info(
            "barra_estimation_complete",
            asset=asset_name,
            r_squared=round(r_squared, 4),
            n_factors=len(factor_names),
            n_assets=n_assets,
        )

        return result

    # ══════════════════════════════════════════════════════════════════
    # Cross-Sectional Z-Score Normalization
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def z_score_normalize(
        values: dict[str, float],
        winsorize: bool = True,
        winsorize_std: float = 3.0,
    ) -> list[ZScoreResult]:
        """
        Cross-sectional z-score normalization with optional winsorization.

        For each value, computes the z-score relative to the cross-sectional
        distribution. Winsorization caps extreme values before z-scoring
        to reduce the impact of outliers.

        Args:
            values: Dict mapping asset name to raw factor value
            winsorize: Whether to winsorize extreme values (default True)
            winsorize_std: Number of std devs for winsorization (default 3.0)

        Returns:
            List of ZScoreResult with z-scores, ranks, and percentiles
        """
        if not values:
            return []

        assets = list(values.keys())
        raw = np.array(list(values.values()))

        if len(raw) < 2:
            return [ZScoreResult(asset=assets[0], raw_value=raw[0], z_score=0.0, rank=1, percentile=50.0)]

        # Winsorize
        if winsorize:
            mean = float(np.mean(raw))
            std = float(np.std(raw, ddof=1))
            if std > 0:
                lower = mean - winsorize_std * std
                upper = mean + winsorize_std * std
                raw = np.clip(raw, lower, upper)

        # Z-score
        mean = float(np.mean(raw))
        std = float(np.std(raw, ddof=1))

        results: list[ZScoreResult] = []
        for i, asset in enumerate(assets):
            z = (raw[i] - mean) / std if std > 0 else 0.0
            rank = int(np.sum(raw <= raw[i]))
            percentile = rank / len(raw) * 100

            results.append(
                ZScoreResult(
                    asset=asset,
                    raw_value=round(float(values[asset]), 6),
                    z_score=round(float(z), 4),
                    rank=rank,
                    percentile=round(percentile, 1),
                )
            )

        return results

    # ══════════════════════════════════════════════════════════════════
    # Factor Return Decomposition
    # ══════════════════════════════════════════════════════════════════

    def decompose_returns(
        self,
        asset_returns: list[float],
        factor_returns_data: dict[str, list[float]],
        asset_name: str = "ASSET",
    ) -> FactorReturnDecomposition:
        """
        Decompose asset returns into factor contributions.

        Uses OLS regression to estimate factor exposures (betas),
        then attributes the total return to each factor.

        Args:
            asset_returns: Time series of asset returns
            factor_returns_data: Dict mapping factor name to time series of factor returns
            asset_name: Asset identifier

        Returns:
            FactorReturnDecomposition with contributions and R²
        """
        n = len(asset_returns)
        for fname, fdata in factor_returns_data.items():
            if len(fdata) != n:
                raise InvalidParameterError(
                    f"factor_returns[{fname}]",
                    len(fdata),
                    f"Must have length {n}",
                )

        # Run regression
        result = self._estimate_factor_model(
            asset_returns=asset_returns,
            factor_data=factor_returns_data,
            model_type="DECOMPOSITION",
            factor_descriptions={k: k for k in factor_returns_data},
            asset_name=asset_name,
        )

        if result.decompositions:
            return result.decompositions[0]

        return FactorReturnDecomposition(
            asset=asset_name,
            total_return=0.0,
        )

    # ══════════════════════════════════════════════════════════════════
    # Integration with Alpha101 and Technical factors
    # ══════════════════════════════════════════════════════════════════

    def compute_alpha101_factor_exposures(
        self,
        close: pd.Series,
        open_: pd.Series,
        high: pd.Series,
        low: pd.Series,
        volume: pd.Series,
        returns: pd.Series,
    ) -> dict[str, list[float]]:
        """
        Compute Alpha101 factor exposures for use in factor models.

        Integrates with factors/alpha101.py to generate cross-sectional
        factor values that can be fed into the Barra model.

        Args:
            close: Close price series
            open_: Open price series
            high: High price series
            low: Low price series
            volume: Volume series
            returns: Returns series

        Returns:
            Dict mapping factor name to exposure values
        """
        from quant_nanggroe_ai.factors.alpha101 import ALPHA_FACTORS

        exposures: dict[str, list[float]] = {}

        # Select a subset of alpha factors for the model
        alpha_subset = {
            "alpha001": ALPHA_FACTORS["alpha001"],
            "alpha002": ALPHA_FACTORS["alpha002"],
            "alpha012": ALPHA_FACTORS["alpha012"],
        }

        for name, fn in alpha_subset.items():
            try:
                # Determine which arguments the function needs
                import inspect
                sig = inspect.signature(fn)
                kwargs: dict[str, Any] = {}
                if "close" in sig.parameters:
                    kwargs["close"] = close
                if "open_" in sig.parameters:
                    kwargs["open_"] = open_
                if "high" in sig.parameters:
                    kwargs["high"] = high
                if "low" in sig.parameters:
                    kwargs["low"] = low
                if "volume" in sig.parameters:
                    kwargs["volume"] = volume
                if "returns" in sig.parameters:
                    kwargs["returns"] = returns

                result = fn(**kwargs)
                # Convert to list, replacing NaN with 0
                if isinstance(result, pd.Series):
                    exposures[name] = result.fillna(0).tolist()
                else:
                    exposures[name] = [float(v) if not math.isnan(v) else 0.0 for v in result]
            except Exception as e:
                logger.warning("alpha101_factor_failed", factor=name, error=str(e))
                exposures[name] = [0.0] * len(close)

        return exposures

    def compute_technical_factor_exposures(
        self,
        closes: list[float],
    ) -> dict[str, float]:
        """
        Compute technical factor exposures for a single asset.

        Integrates with factors/technical.py to generate factor values
        from technical indicators.

        Args:
            closes: Close price series for the asset

        Returns:
            Dict mapping factor name to exposure value
        """
        from quant_nanggroe_ai.factors.technical import (
            compute_rsi_factor,
            compute_macd_factor,
            compute_bollinger_factor,
        )

        exposures: dict[str, float] = {}

        # RSI as momentum factor
        rsi = compute_rsi_factor(closes)
        if rsi is not None:
            exposures["rsi_momentum"] = round(rsi / 100.0, 4)  # Normalize to 0-1

        # MACD as trend factor
        macd = compute_macd_factor(closes)
        if macd.get("histogram") is not None:
            exposures["macd_trend"] = round(float(macd["histogram"]), 4)

        # Bollinger %B as mean-reversion factor
        bb = compute_bollinger_factor(closes)
        if bb.get("percent_b") is not None:
            exposures["bollinger_reversion"] = round(float(bb["percent_b"]), 4)

        return exposures

    # ══════════════════════════════════════════════════════════════════
    # Internal Estimation Methods
    # ══════════════════════════════════════════════════════════════════

    def _estimate_factor_model(
        self,
        asset_returns: list[float],
        factor_data: dict[str, list[float]],
        model_type: str,
        factor_descriptions: dict[str, str],
        asset_name: str = "ASSET",
    ) -> FactorModelResult:
        """
        Core OLS factor model estimation.

        Estimates: r = α + Σ(β_k * f_k) + ε

        Args:
            asset_returns: Dependent variable (asset returns)
            factor_data: Dict mapping factor name to return series
            model_type: Model type identifier
            factor_descriptions: Dict mapping factor name to description
            asset_name: Asset identifier

        Returns:
            FactorModelResult with full estimation output
        """
        n = len(asset_returns)
        factor_names = list(factor_data.keys())
        n_factors = len(factor_names)

        # Build design matrix X with intercept
        X = np.column_stack(
            [np.ones(n)] + [np.array(factor_data[f]) for f in factor_names]
        )
        y = np.array(asset_returns)

        # OLS regression
        try:
            betas, residuals_arr, rank, sv = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            raise InvalidParameterError(
                "factor_data",
                factor_data,
                "Singular matrix — factors may be collinear",
            )

        alpha = float(betas[0])
        factor_betas = {factor_names[i]: float(betas[i + 1]) for i in range(n_factors)}

        # Compute fitted values and residuals
        y_hat = X @ betas
        residuals = y - y_hat

        # R² and adjusted R²
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        adjusted_r_squared = (
            1 - (1 - r_squared) * (n - 1) / (n - n_factors - 1)
            if n > n_factors + 1
            else 0.0
        )

        # T-statistics for each beta
        dof = n - n_factors - 1
        mse = ss_res / dof if dof > 0 else 1.0
        try:
            cov_matrix = mse * np.linalg.inv(X.T @ X)
            se = np.sqrt(np.diag(cov_matrix))
            t_stats = betas / se
        except np.linalg.LinAlgError:
            t_stats = np.zeros(len(betas))

        # Factor returns (mean of each factor series)
        factor_returns = {f: float(np.mean(factor_data[f])) for f in factor_names}

        # Factor covariance matrix
        factor_covariance = self._compute_factor_covariance(factor_data, factor_names)

        # Build factor exposures
        exposures: list[FactorExposure] = []
        for i, f in enumerate(factor_names):
            exposures.append(
                FactorExposure(
                    asset=asset_name,
                    factor=f,
                    beta=round(factor_betas[f], 4),
                    t_stat=round(float(t_stats[i + 1]), 4),
                )
            )

        # Factor return decomposition
        factor_contributions = {
            f: round(factor_betas[f] * factor_returns[f], 6) for f in factor_names
        }
        total_return = float(np.mean(asset_returns))
        idiosyncratic = total_return - sum(factor_contributions.values())

        decomposition = FactorReturnDecomposition(
            asset=asset_name,
            total_return=round(total_return, 6),
            factor_contributions=factor_contributions,
            idiosyncratic_return=round(idiosyncratic, 6),
            r_squared=round(r_squared, 4),
            adjusted_r_squared=round(adjusted_r_squared, 4),
        )

        # Risk attribution
        residual_var = float(np.var(residuals, ddof=1)) if len(residuals) > 1 else 0.0
        risk_attr = self._compute_risk_attribution(
            factor_returns_dict=factor_betas,
            factor_covariance=factor_covariance,
            exposures=factor_betas,
            residual_variance=residual_var,
        )

        return FactorModelResult(
            model_type=model_type,
            factors=factor_names,
            factor_returns={k: round(v, 6) for k, v in factor_returns.items()},
            factor_covariance=factor_covariance,
            exposures=exposures,
            decompositions=[decomposition],
            risk_attribution=risk_attr,
        )

    @staticmethod
    def _compute_factor_covariance(
        factor_data: dict[str, list[float]],
        factor_names: list[str],
    ) -> dict[str, dict[str, float]]:
        """
        Compute factor return covariance matrix.

        Args:
            factor_data: Dict mapping factor name to return series
            factor_names: Ordered list of factor names

        Returns:
            Nested dict representing the covariance matrix
        """
        if not factor_data or not factor_names:
            return {}

        # Build matrix of factor returns
        try:
            arrays = [np.array(factor_data[f]) for f in factor_names]
            # Ensure we have 2D data with multiple observations
            if any(len(arr.shape) == 0 or arr.shape[0] < 2 for arr in arrays):
                return {f: {f: 0.0 for f in factor_names} for f in factor_names}

            matrix = np.column_stack(arrays)
            if matrix.ndim < 2 or matrix.shape[0] < 2:
                return {f: {f: 0.0 for f in factor_names} for f in factor_names}

            cov = np.cov(matrix, rowvar=False)
            # Handle case where single factor results in scalar
            if cov.ndim == 0:
                return {factor_names[0]: {factor_names[0]: round(float(cov), 8)}}

            result: dict[str, dict[str, float]] = {}
            for i, fi in enumerate(factor_names):
                result[fi] = {}
                for j, fj in enumerate(factor_names):
                    result[fi][fj] = round(float(cov[i, j]), 8)

            return result
        except (ValueError, np.linalg.LinAlgError):
            return {f: {f: 0.0 for f in factor_names} for f in factor_names}

    @staticmethod
    def _compute_risk_attribution(
        factor_returns_dict: dict[str, float],
        factor_covariance: dict[str, dict[str, float]],
        exposures: dict[str, float],
        residual_variance: float,
    ) -> RiskAttribution:
        """
        Compute risk attribution by factor.

        Total variance = β'·Σ·β + σ²_ε

        where Σ is the factor covariance matrix, β is the exposure vector,
        and σ²_ε is the idiosyncratic variance.

        Args:
            factor_returns_dict: Factor exposures/betas
            factor_covariance: Factor covariance matrix
            exposures: Factor exposures (same as factor_returns_dict for time-series)
            residual_variance: Idiosyncratic variance
            annualize: Whether to annualize (multiply by 252)

        Returns:
            RiskAttribution with factor risk contributions
        """
        factor_names = list(exposures.keys())
        n_factors = len(factor_names)

        if n_factors == 0:
            return RiskAttribution(
                total_risk=0.0,
                idiosyncratic_risk=math.sqrt(max(0, residual_variance)) * math.sqrt(252),
                idiosyncratic_risk_pct=100.0,
            )

        # Build exposure vector and covariance matrix
        beta = np.array([exposures.get(f, 0.0) for f in factor_names])
        sigma = np.zeros((n_factors, n_factors))

        for i, fi in enumerate(factor_names):
            for j, fj in enumerate(factor_names):
                sigma[i, j] = factor_covariance.get(fi, {}).get(fj, 0.0)

        # Total systematic variance: β'·Σ·β
        systematic_var = float(beta @ sigma @ beta)

        # Per-factor risk contribution
        factor_risk: dict[str, float] = {}
        for i, f in enumerate(factor_names):
            # Marginal contribution: (Σ·β)_i * β_i
            marginal = float((sigma @ beta)[i])
            contribution = beta[i] * marginal
            factor_risk[f] = round(math.sqrt(max(0, abs(contribution))) * math.sqrt(252), 6)

        total_var = systematic_var + residual_variance
        total_risk = math.sqrt(max(0, total_var)) * math.sqrt(252)
        idio_risk = math.sqrt(max(0, residual_variance)) * math.sqrt(252)

        # Percentage attribution
        factor_risk_pct: dict[str, float] = {}
        if total_var > 0:
            for f in factor_names:
                pct = factor_risk.get(f, 0.0) / total_risk * 100 if total_risk > 0 else 0.0
                factor_risk_pct[f] = round(pct, 2)
            idio_pct = idio_risk / total_risk * 100 if total_risk > 0 else 0.0
        else:
            idio_pct = 100.0

        return RiskAttribution(
            total_risk=round(total_risk, 6),
            factor_risk=factor_risk,
            idiosyncratic_risk=round(idio_risk, 6),
            factor_risk_pct=factor_risk_pct,
            idiosyncratic_risk_pct=round(idio_pct, 2),
        )

    def status(self) -> dict[str, Any]:
        """Get current factor models engine status."""
        return {
            "last_model_type": self._last_result.model_type if self._last_result else None,
            "history_size": len(self._factor_history),
            "supported_models": ["FAMA_FRENCH_3", "FAMA_FRENCH_5", "BARRA", "DECOMPOSITION"],
            "min_observations": self.MIN_OBSERVATIONS,
            "timestamp": datetime.now().isoformat(),
        }
