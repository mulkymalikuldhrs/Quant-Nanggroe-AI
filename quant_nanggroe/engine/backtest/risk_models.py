"""Advanced Risk Models for Quantitative Trading.

Production-grade implementations of:
1. Parametric VaR (variance-covariance)
2. Historical VaR (empirical quantile)
3. Monte Carlo VaR
4. Cornish-Fisher VaR (skewness/kurtosis adjusted)
5. Expected Shortfall (CVaR)
6. Component VaR and Marginal VaR
7. Conditional Drawdown-at-Risk (CDaR)
8. Stress Testing Framework
9. Copula-based Joint Risk
10. Liquidity-adjusted VaR

References:
- Jorion (2007), "Value at Risk"
- McNeil, Frey, Embrechts (2015), "Quantitative Risk Management"
- Rockafellar & Uryasev (2000), "Optimization of Conditional Value-at-Risk"
- Bangia et al. (1999), "Liquidity Adjusted VaR"
- Nelsen (2006), "An Introduction to Copulas"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Enums and Data Classes
# ══════════════════════════════════════════════════════════════════════


class VaRMethod(str, Enum):
    """Value-at-Risk calculation method."""
    PARAMETRIC = "parametric"
    HISTORICAL = "historical"
    MONTE_CARLO = "monte_carlo"
    CORNISH_FISHER = "cornish_fisher"


@dataclass
class VaRResult:
    """Value-at-Risk result at multiple confidence levels."""

    method: str
    confidence_levels: List[float]
    var_values: Dict[float, float]  # confidence -> VaR
    cvar_values: Dict[float, float]  # confidence -> CVaR
    portfolio_value: float


@dataclass
class ComponentVaRResult:
    """Component and Marginal VaR results.

    Attributes:
        component_var: Dict of symbol -> component VaR.
        marginal_var: Dict of symbol -> marginal VaR.
        percentage_contrib: Dict of symbol -> % contribution to total VaR.
        total_var: Total portfolio VaR.
    """

    component_var: Dict[str, float]
    marginal_var: Dict[str, float]
    percentage_contrib: Dict[str, float]
    total_var: float


@dataclass
class StressTestResult:
    """Stress test result for a single scenario.

    Attributes:
        scenario_name: Name of the stress scenario.
        description: Description of what the scenario models.
        shocked_var: VaR under the stressed scenario.
        shocked_cvar: CVaR under the stressed scenario.
        portfolio_loss: Estimated portfolio loss.
        loss_pct: Loss as percentage of portfolio value.
    """

    scenario_name: str
    description: str
    shocked_var: float
    shocked_cvar: float
    portfolio_loss: float
    loss_pct: float


@dataclass
class CorrelationBreakdownResult:
    """Correlation breakdown detection result."""

    is_breakdown_detected: bool
    current_correlation: float
    long_term_correlation: float
    correlation_ratio: float
    z_score: float
    p_value: float


@dataclass
class LiquidityAdjustedVaRResult:
    """Liquidity-adjusted VaR result.

    Attributes:
        base_var: Standard VaR without liquidity adjustment.
        liquidity_adjustment: Additional VaR from liquidity risk.
        adjusted_var: Total VaR with liquidity adjustment.
        liquidation_cost: Estimated cost of liquidation.
        liquidation_time: Estimated time to liquidate (days).
    """

    base_var: float
    liquidity_adjustment: float
    adjusted_var: float
    liquidation_cost: float
    liquidation_time: float


# ══════════════════════════════════════════════════════════════════════
# ValueAtRisk Class
# ══════════════════════════════════════════════════════════════════════


class ValueAtRisk:
    """Value-at-Risk calculations using multiple methods.

    Implements four VaR methods:
    1. Parametric (variance-covariance) - assumes normal distribution
    2. Historical - empirical quantile method
    3. Monte Carlo - simulated from fitted distribution
    4. Cornish-Fisher - adjusted for skewness and kurtosis

    Usage:
        var_calc = ValueAtRisk()
        p_var = var_calc.parametric_var(returns, confidence=0.99)
        h_var = var_calc.historical_var(returns, confidence=0.99)
        cf_var = var_calc.cornish_fisher_var(returns, confidence=0.99)
        mc_var = var_calc.monte_carlo_var(returns, confidence=0.99)
    """

    @staticmethod
    def parametric_var(
        returns: np.ndarray,
        confidence: float = 0.99,
        horizon: int = 1,
    ) -> float:
        """Parametric VaR (Variance-Covariance method).

        Assumes returns are normally distributed.

        VaR_alpha = -(mu - z_alpha * sigma) * sqrt(horizon)

        where z_alpha = Phi^{-1}(1 - alpha), Phi = standard normal CDF.

        Reference: Jorion (2007), Chapter 5.

        Args:
            returns: Array of historical returns.
            confidence: Confidence level (e.g., 0.99 for 99%).
            horizon: Time horizon in days.

        Returns:
            VaR value (positive number representing potential loss).
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return 0.0

        mean = np.mean(returns)
        std = np.std(returns, ddof=1)

        if std <= 0:
            return 0.0

        alpha = 1 - confidence
        z_alpha = sp_stats.norm.ppf(1 - alpha)  # Positive z-score

        # VaR = -(mu - z_alpha * sigma) * sqrt(horizon)
        # This is the loss threshold at the given confidence level
        var_val = abs((-mean + z_alpha * std) * np.sqrt(horizon))

        return float(var_val)

    @staticmethod
    def historical_var(
        returns: np.ndarray,
        confidence: float = 0.99,
        horizon: int = 1,
    ) -> float:
        """Historical VaR using empirical quantile method.

        Simply takes the (1 - confidence) percentile of the empirical
        return distribution.

        VaR_alpha = -percentile(returns, (1-alpha)*100) * sqrt(horizon)

        Reference: Jorion (2007), Chapter 5.

        Args:
            returns: Array of historical returns.
            confidence: Confidence level (e.g., 0.99 for 99%).
            horizon: Time horizon in days (scaled by sqrt).

        Returns:
            VaR value (positive number representing potential loss).
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return 0.0

        alpha = 1 - confidence
        var_threshold = np.percentile(returns, alpha * 100)

        # Scale for horizon using sqrt-of-time rule
        var_val = abs(var_threshold * np.sqrt(horizon))

        return float(var_val)

    @staticmethod
    def cornish_fisher_var(
        returns: np.ndarray,
        confidence: float = 0.99,
    ) -> float:
        """Cornish-Fisher VaR adjusted for skewness and kurtosis.

        Adjusts the normal quantile for non-normality:

            z_cf = z + (z^2 - 1)*S/6 + (z^3 - 3z)*K/24 - (2z^3 - 5z)*S^2/36

        where:
            z = standard normal quantile at (1 - confidence)
            S = sample skewness
            K = sample excess kurtosis

        CF-VaR = mu + z_cf * sigma

        Reference: Favre & Galeano (2002), "Mean-Modified Value-at-Risk
        Optimization with Hedge Funds"

        Args:
            returns: Array of historical returns.
            confidence: Confidence level (e.g., 0.99 for 99%).

        Returns:
            Cornish-Fisher adjusted VaR (positive number = potential loss).
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 4:
            return ValueAtRisk.parametric_var(returns, confidence)

        mean = np.mean(returns)
        std = np.std(returns, ddof=1)

        if std <= 0:
            return 0.0

        alpha = 1 - confidence
        z = sp_stats.norm.ppf(alpha)  # Negative for high confidence

        S = float(sp_stats.skew(returns, bias=False))
        K = float(sp_stats.kurtosis(returns, bias=False))  # Excess kurtosis

        # Cornish-Fisher expansion (equation from the paper)
        cf_adjustment = (
            (z ** 2 - 1) * S / 6
            + (z ** 3 - 3 * z) * K / 24
            - (2 * z ** 3 - 5 * z) * S ** 2 / 36
        )

        z_cf = z + cf_adjustment

        # CF-VaR = mu + z_cf * sigma (z_cf is negative for high confidence)
        cf_var = abs(mean + z_cf * std)

        return float(cf_var)

    @staticmethod
    def monte_carlo_var(
        returns: np.ndarray,
        confidence: float = 0.99,
        n_sims: int = 10000,
        horizon: int = 1,
        random_seed: Optional[int] = None,
    ) -> float:
        """Monte Carlo VaR through simulation.

        Fits a Student-t distribution to capture fat tails, then
        simulates n_sims scenarios and computes VaR from the
        simulated distribution.

        Reference: McNeil, Frey, Embrechts (2015), Chapter 5.

        Args:
            returns: Array of historical returns.
            confidence: Confidence level (e.g., 0.99 for 99%).
            n_sims: Number of Monte Carlo simulations.
            horizon: Time horizon in days.
            random_seed: Random seed for reproducibility.

        Returns:
            Monte Carlo VaR (positive number = potential loss).
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return 0.0

        alpha = 1 - confidence
        rng = np.random.default_rng(random_seed)

        mean = np.mean(returns)
        std = np.std(returns, ddof=1)

        if std <= 0:
            return 0.0

        # Fit Student-t distribution for better tail modeling
        try:
            df_t, loc_t, scale_t = sp_stats.t.fit(returns)
            simulated = sp_stats.t.rvs(
                df_t, loc=loc_t, scale=scale_t,
                size=n_sims, random_state=rng,
            )
        except Exception:
            simulated = rng.normal(mean, std, size=n_sims)

        # Scale for horizon
        simulated_horizon = simulated * np.sqrt(horizon)

        var_threshold = np.percentile(simulated_horizon, alpha * 100)
        var_val = abs(var_threshold)

        return float(var_val)


# ══════════════════════════════════════════════════════════════════════
# ConditionalVaR Class
# ══════════════════════════════════════════════════════════════════════


class ConditionalVaR:
    """Conditional Value-at-Risk (Expected Shortfall) calculations.

    CVaR (also known as Expected Shortfall) is the expected loss
    GIVEN that the loss exceeds the VaR threshold:

        CVaR_alpha = E[X | X <= VaR_alpha]

    CVaR is a coherent risk measure (sub-additive, convex) unlike VaR.

    Reference: Rockafellar & Uryasev (2000), "Optimization of
    Conditional Value-at-Risk"

    Usage:
        cvar_calc = ConditionalVaR()
        h_cvar = cvar_calc.historical_cvar(returns, confidence=0.99)
        p_cvar = cvar_calc.parametric_cvar(returns, confidence=0.99)
        ru_cvar = cvar_calc.rockafellar_uryasev_cvar(returns, confidence=0.99)
    """

    @staticmethod
    def historical_cvar(
        returns: np.ndarray,
        confidence: float = 0.99,
    ) -> float:
        """Historical CVaR (Expected Shortfall).

        Average of losses beyond VaR:
            CVaR_alpha = -E[R | R <= VaR_alpha]
            = -mean(returns[returns <= VaR_threshold])

        Reference: McNeil, Frey, Embrechts (2015), Section 2.2.

        Args:
            returns: Array of historical returns.
            confidence: Confidence level (e.g., 0.99 for 99%).

        Returns:
            CVaR value (positive number representing expected loss).
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return 0.0

        alpha = 1 - confidence
        var_threshold = np.percentile(returns, alpha * 100)

        # CVaR = E[R | R <= VaR]
        tail = returns[returns <= var_threshold]
        if len(tail) > 0:
            cvar_val = abs(float(np.mean(tail)))
        else:
            cvar_val = abs(float(var_threshold))

        return cvar_val

    @staticmethod
    def parametric_cvar(
        returns: np.ndarray,
        confidence: float = 0.99,
    ) -> float:
        """Parametric CVaR assuming normal distribution.

        For normal distribution:
            CVaR_alpha = -mu + sigma * phi(z_alpha) / alpha

        where:
            z_alpha = Phi^{-1}(1 - alpha)
            phi = standard normal PDF
            alpha = 1 - confidence

        Reference: Jorion (2007), Chapter 5.

        Args:
            returns: Array of historical returns.
            confidence: Confidence level (e.g., 0.99 for 99%).

        Returns:
            Parametric CVaR value (positive number).
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return 0.0

        mean = np.mean(returns)
        std = np.std(returns, ddof=1)

        if std <= 0:
            return 0.0

        alpha = 1 - confidence
        z_alpha = sp_stats.norm.ppf(1 - alpha)

        # CVaR for normal distribution: -mu + sigma * phi(z_alpha) / alpha
        cvar_val = abs(-mean + std * sp_stats.norm.pdf(z_alpha) / alpha)

        return float(cvar_val)

    @staticmethod
    def rockafellar_uryasev_cvar(
        returns: np.ndarray,
        confidence: float = 0.99,
    ) -> float:
        """Rockafellar-Uryasev CVaR via linear programming formulation.

        CVaR is the solution to:
            CVaR_alpha = min_zeta { zeta + (1/(n*alpha)) * sum(max(-R_i - zeta, 0)) }

        This is the Rockafellar-Uryasev (2000) characterization that
        makes CVaR amenable to optimization.

        Reference: Rockafellar & Uryasev (2000), "Optimization of
        Conditional Value-at-Risk"

        Args:
            returns: Array of historical returns.
            confidence: Confidence level (e.g., 0.99 for 99%).

        Returns:
            CVaR value (positive number).
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return 0.0

        alpha = 1 - confidence
        n = len(returns)

        # Optimization: min_{zeta, u} zeta + (1/(n*alpha)) * sum(u_i)
        # subject to: u_i >= -R_i - zeta, u_i >= 0
        # This can be solved as a simple 1D optimization over zeta

        def objective(zeta: float) -> float:
            """Rockafellar-Uryasev objective."""
            losses = -returns  # Loss = -return
            excess = np.maximum(losses - zeta, 0)
            return zeta + (1.0 / (n * alpha)) * np.sum(excess)

        # Find the optimal zeta using scipy
        try:
            # Reasonable bounds for zeta
            loss_min = float(np.min(-returns))
            loss_max = float(np.max(-returns))
            from scipy.optimize import minimize_scalar
            result = minimize_scalar(
                objective,
                bounds=(loss_min - 0.1, loss_max + 0.1),
                method="bounded",
            )
            cvar_val = float(result.fun)
        except Exception:
            # Fallback to historical CVaR
            var_threshold = np.percentile(returns, alpha * 100)
            tail = returns[returns <= var_threshold]
            cvar_val = abs(float(np.mean(tail))) if len(tail) > 0 else abs(float(var_threshold))

        return cvar_val


# ══════════════════════════════════════════════════════════════════════
# ComponentVaR Class
# ══════════════════════════════════════════════════════════════════════


class ComponentVaR:
    """Component and Marginal VaR calculations.

    Component VaR decomposes portfolio VaR into the risk contribution
    of each position:

        Component_VaR_i = w_i * Marginal_VaR_i
        Marginal_VaR_i = dVaR/dw_i

    The sum of Component VaRs equals Total Portfolio VaR.

    Reference: Jorion (2007), Chapter 7.

    Usage:
        comp_var = ComponentVaR()
        result = comp_var.component_var(weights, cov_matrix, confidence=0.99)
        m_var = comp_var.marginal_var(position_returns, portfolio_returns)
    """

    @staticmethod
    def component_var(
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        confidence: float = 0.99,
        symbols: Optional[List[str]] = None,
    ) -> ComponentVaRResult:
        """Calculate each position's contribution to portfolio VaR.

        Uses parametric (delta-normal) approach:

            Marginal_VaR_i = (z_alpha / sigma_p) * (Sigma @ w)_i
            Component_VaR_i = w_i * Marginal_VaR_i
            Total_VaR = sum(Component_VaR_i)

        where:
            sigma_p = sqrt(w' Sigma w) is portfolio volatility
            z_alpha = Phi^{-1}(confidence) is the normal quantile

        Property: sum(Component_VaR_i) = Total_VaR

        Args:
            weights: Portfolio weights (1D array).
            cov_matrix: Covariance matrix of returns (2D array).
            confidence: Confidence level for VaR.
            symbols: Optional list of symbol names.

        Returns:
            ComponentVaRResult with component, marginal, and percentage VaR.
        """
        weights = np.asarray(weights, dtype=np.float64)
        cov_matrix = np.asarray(cov_matrix, dtype=np.float64)

        n_assets = len(weights)

        if n_assets < 1:
            empty = {} if symbols is None else {s: 0.0 for s in symbols}
            return ComponentVaRResult(
                component_var=empty,
                marginal_var=empty.copy(),
                percentage_contrib=empty.copy(),
                total_var=0.0,
            )

        if symbols is None:
            symbols = [f"Asset_{i}" for i in range(n_assets)]

        z_alpha = sp_stats.norm.ppf(confidence)

        # Portfolio variance: sigma_p^2 = w' Sigma w
        port_var = weights @ cov_matrix @ weights

        if port_var <= 0:
            empty = {s: 0.0 for s in symbols}
            return ComponentVaRResult(
                component_var=empty,
                marginal_var=empty.copy(),
                percentage_contrib=empty.copy(),
                total_var=0.0,
            )

        sigma_p = np.sqrt(port_var)

        # Marginal VaR: dVaR/dw_i = (z_alpha / sigma_p) * (Sigma @ w)_i
        sigma_w = cov_matrix @ weights
        marginal_var = z_alpha * sigma_w / sigma_p

        # Component VaR: w_i * Marginal_VaR_i
        comp_var = weights * marginal_var

        # Total VaR
        total_var = float(np.sum(comp_var))

        # Percentage contribution
        pct_contrib = comp_var / total_var if total_var > 0 else np.zeros_like(comp_var)

        return ComponentVaRResult(
            component_var={s: round(float(comp_var[i]), 6) for i, s in enumerate(symbols)},
            marginal_var={s: round(float(marginal_var[i]), 6) for i, s in enumerate(symbols)},
            percentage_contrib={s: round(float(pct_contrib[i]), 4) for i, s in enumerate(symbols)},
            total_var=round(total_var, 6),
        )

    @staticmethod
    def marginal_var(
        position_returns: np.ndarray,
        portfolio_returns: np.ndarray,
        confidence: float = 0.99,
    ) -> float:
        """Impact of adding a position on portfolio VaR.

        Estimates the marginal VaR by computing the derivative of
        portfolio VaR with respect to position weight:

            Marginal_VaR_i = dVaR/dw_i

        Approximated via the covariance between position and portfolio:

            dVaR/dw_i = (z_alpha / sigma_p) * Cov(R_i, R_p)

        Args:
            position_returns: Returns of the position to add.
            portfolio_returns: Current portfolio returns.
            confidence: Confidence level for VaR.

        Returns:
            Marginal VaR of adding the position.
        """
        position_returns = np.asarray(position_returns, dtype=np.float64)
        portfolio_returns = np.asarray(portfolio_returns, dtype=np.float64)

        # Align lengths
        min_len = min(len(position_returns), len(portfolio_returns))
        if min_len < 2:
            return 0.0

        pos_ret = position_returns[:min_len]
        port_ret = portfolio_returns[:min_len]

        z_alpha = sp_stats.norm.ppf(confidence)
        sigma_p = np.std(port_ret, ddof=1)

        if sigma_p <= 1e-10:
            return 0.0

        # Cov(R_i, R_p)
        cov_ip = np.cov(pos_ret, port_ret, ddof=1)[0, 1]

        # Marginal VaR = (z_alpha / sigma_p) * Cov(R_i, R_p)
        marginal = float(z_alpha * cov_ip / sigma_p)

        return marginal


# ══════════════════════════════════════════════════════════════════════
# StressTestFramework Class
# ══════════════════════════════════════════════════════════════════════


class StressTestFramework:
    """Stress Testing Framework for portfolio risk assessment.

    Provides three types of stress testing:
    1. Scenario Analysis - Apply predefined stress scenarios
    2. Historical Stress Test - Replay historical crises
    3. Reverse Stress Test - Find scenarios that cause a target loss

    Usage:
        stress = StressTestFramework(bars_per_year=252)
        # Scenario analysis
        results = stress.scenario_analysis(returns, scenarios)
        # Historical stress test
        results = stress.historical_stress_test(returns, crisis_periods)
        # Reverse stress test
        result = stress.reverse_stress_test(returns, target_loss=0.20)
    """

    # Default historical crisis periods (approximate)
    DEFAULT_CRISES = {
        "GFC_2008": ("Global Financial Crisis 2008", "2008-09-01", "2009-03-01"),
        "COVID_2020": ("COVID-19 Crash 2020", "2020-02-19", "2020-03-23"),
        "Dotcom_2000": ("Dotcom Bubble Burst", "2000-03-01", "2002-10-01"),
        "Asian_1997": ("Asian Financial Crisis", "1997-07-01", "1998-01-01"),
        "BlackMonday_1987": ("Black Monday 1987", "1987-10-01", "1987-11-01"),
    }

    def __init__(self, bars_per_year: int = 252) -> None:
        """Initialize stress test framework.

        Args:
            bars_per_year: Bars per year for annualization.
        """
        self.bars_per_year = bars_per_year

    def scenario_analysis(
        self,
        returns: pd.Series,
        scenarios: Optional[Dict[str, Tuple[str, float, float]]] = None,
        portfolio_value: float = 1_000_000.0,
    ) -> List[StressTestResult]:
        """Apply stress scenarios to portfolio.

        Each scenario specifies a return shock and volatility multiplier:
        - Stressed return = base_annual_return + return_shock
        - Stressed vol = base_annual_vol * vol_multiplier

        Args:
            returns: Historical returns series.
            scenarios: Dict of {name: (description, return_shock, vol_multiplier)}.
                return_shock: Direct annual return impact (e.g., -0.40 for 40% loss).
                vol_multiplier: Multiplier on annual volatility.
            portfolio_value: Current portfolio value.

        Returns:
            List of StressTestResult for each scenario.
        """
        if scenarios is None:
            scenarios = {
                "2008_GFC": ("Global Financial Crisis 2008", -0.40, 2.5),
                "COVID_Crash": ("COVID-19 Market Crash 2020", -0.30, 2.0),
                "Flash_Crash": ("Flash Crash 2010", -0.10, 3.0),
                "Rate_Shock": ("Interest Rate Shock", -0.15, 1.5),
                "Liquidity_Crisis": ("Liquidity Crisis", -0.20, 2.0),
                "Sovereign_Debt": ("Sovereign Debt Crisis", -0.25, 1.8),
            }

        results: List[StressTestResult] = []
        base_return = float(returns.mean()) * self.bars_per_year
        base_vol = float(returns.std()) * np.sqrt(self.bars_per_year)

        for name, (description, return_shock, vol_mult) in scenarios.items():
            stressed_return = base_return + return_shock
            stressed_vol = base_vol * vol_mult

            # Stressed VaR (95%): -stressed_return + 1.645 * stressed_vol
            z_95 = 1.645
            stressed_var = abs(stressed_return - z_95 * stressed_vol) * portfolio_value

            # Stressed CVaR (95%): -stressed_return + phi(z_95)/0.05 * stressed_vol
            stressed_cvar = abs(
                stressed_return - stressed_vol * sp_stats.norm.pdf(z_95) / 0.05
            ) * portfolio_value

            portfolio_loss = abs(return_shock) * portfolio_value
            loss_pct = abs(return_shock)

            results.append(StressTestResult(
                scenario_name=name,
                description=description,
                shocked_var=round(stressed_var, 2),
                shocked_cvar=round(stressed_cvar, 2),
                portfolio_loss=round(portfolio_loss, 2),
                loss_pct=round(loss_pct, 4),
            ))

        return results

    def historical_stress_test(
        self,
        returns: pd.Series,
        crisis_periods: Optional[Dict[str, Tuple[str, str, str]]] = None,
        portfolio_value: float = 1_000_000.0,
    ) -> List[StressTestResult]:
        """Replay historical crises on current portfolio.

        Takes actual returns from historical crisis periods and
        applies them to the current portfolio.

        Args:
            returns: Historical returns series (must have DatetimeIndex).
            crisis_periods: Dict of {name: (description, start_date, end_date)}.
                Dates in 'YYYY-MM-DD' format.
            portfolio_value: Current portfolio value.

        Returns:
            List of StressTestResult for each crisis period.
        """
        crisis = crisis_periods or self.DEFAULT_CRISES

        results: List[StressTestResult] = []

        for name, (description, start, end) in crisis.items():
            try:
                start_dt = pd.Timestamp(start)
                end_dt = pd.Timestamp(end)

                if isinstance(returns.index, pd.DatetimeIndex):
                    crisis_returns = returns.loc[start_dt:end_dt]
                else:
                    # Can't filter non-datetime index
                    crisis_returns = returns

                if len(crisis_returns) == 0:
                    continue

                # Compute actual losses during the crisis
                cumulative_return = float((1 + crisis_returns).prod() - 1)
                crisis_vol = float(crisis_returns.std()) * np.sqrt(self.bars_per_year)

                portfolio_loss = abs(cumulative_return) * portfolio_value
                loss_pct = abs(cumulative_return)

                # Stressed VaR during crisis
                z_95 = 1.645
                crisis_mean = float(crisis_returns.mean()) * self.bars_per_year
                stressed_var = abs(crisis_mean - z_95 * crisis_vol) * portfolio_value
                stressed_cvar = abs(
                    crisis_mean - crisis_vol * sp_stats.norm.pdf(z_95) / 0.05
                ) * portfolio_value

                results.append(StressTestResult(
                    scenario_name=name,
                    description=description,
                    shocked_var=round(stressed_var, 2),
                    shocked_cvar=round(stressed_cvar, 2),
                    portfolio_loss=round(portfolio_loss, 2),
                    loss_pct=round(loss_pct, 4),
                ))

            except Exception as e:
                logger.warning("Failed to process crisis period %s: %s", name, e)
                continue

        return results

    def reverse_stress_test(
        self,
        returns: pd.Series,
        target_loss: float = 0.20,
    ) -> Dict[str, Any]:
        """Find scenarios that cause a target loss.

        Determines what combination of return and volatility would
        cause the portfolio to lose at least target_loss (as fraction).

        Uses the parametric model to solve for the stress scenario:

            target_loss = -(mu_stressed - z_alpha * sigma_stressed)
            mu_stressed = base_mu + delta_mu
            sigma_stressed = base_sigma * vol_multiplier

        We find the minimum vol_multiplier that causes the target loss.

        Args:
            returns: Historical returns series.
            target_loss: Target loss as fraction of portfolio (e.g., 0.20 for 20%).

        Returns:
            Dict with scenario parameters that cause the target loss.
        """
        base_mu = float(returns.mean()) * self.bars_per_year
        base_sigma = float(returns.std()) * np.sqrt(self.bars_per_year)
        z_95 = 1.645

        if base_sigma <= 1e-10:
            return {
                "target_loss": target_loss,
                "feasible": False,
                "required_return_shock": -target_loss - base_mu,
                "required_vol_multiplier": 0.0,
                "message": "Zero volatility portfolio",
            }

        # Solve: target_loss = -(base_mu + delta_mu) + z_95 * base_sigma * vol_mult
        # For delta_mu = 0 (no return shock):
        # target_loss = -base_mu + z_95 * base_sigma * vol_mult
        # vol_mult = (target_loss + base_mu) / (z_95 * base_sigma)

        vol_mult_no_shock = (target_loss + base_mu) / (z_95 * base_sigma)

        # For delta_mu = -target_loss (worst case return shock):
        # vol_mult_full_shock = (target_loss + base_mu + target_loss) / (z_95 * base_sigma)
        # = (2*target_loss + base_mu) / (z_95 * base_sigma)

        vol_mult_full_shock = (2 * target_loss + base_mu) / (z_95 * base_sigma)

        # Return shock needed with current vol (vol_mult = 1):
        # target_loss = -(base_mu + delta_mu) + z_95 * base_sigma
        # delta_mu = -(target_loss + base_mu - z_95 * base_sigma)
        return_shock_current_vol = -(target_loss + base_mu - z_95 * base_sigma)

        return {
            "target_loss": target_loss,
            "base_return": round(base_mu, 4),
            "base_volatility": round(base_sigma, 4),
            "feasible": True,
            "scenarios": {
                "vol_only": {
                    "description": "Volatility increase with no return shock",
                    "required_vol_multiplier": round(max(1.0, vol_mult_no_shock), 4),
                    "return_shock": 0.0,
                },
                "return_only": {
                    "description": "Return shock with current volatility",
                    "required_vol_multiplier": 1.0,
                    "return_shock": round(return_shock_current_vol, 4),
                },
                "combined": {
                    "description": "Moderate return shock and volatility increase",
                    "required_vol_multiplier": round(max(1.0, vol_mult_full_shock / 2), 4),
                    "return_shock": round(return_shock_current_vol / 2, 4),
                },
            },
        }


# ══════════════════════════════════════════════════════════════════════
# LiquidityAdjustedVaR Class
# ══════════════════════════════════════════════════════════════════════


class LiquidityAdjustedVaR:
    """Liquidity-adjusted VaR (L-VaR).

    Adjusts standard VaR for the cost and time required to liquidate
    a position. Incorporates:
    - Bid-ask spread cost
    - Market impact from large orders
    - Liquidation time horizon

    L-VaR = VaR * sqrt(T) + 0.5 * spread + market_impact

    Reference: Bangia et al. (1999), "Liquidity Adjusted VaR";
    Almgren & Chriss (2001), "Optimal Execution of Portfolio Transactions"

    Usage:
        lvar_calc = LiquidityAdjustedVaR()
        result = lvar_calc.lvav(returns, volumes, confidence=0.99, liquidation_days=5)
    """

    @staticmethod
    def lvav(
        returns: np.ndarray,
        volumes: Optional[np.ndarray] = None,
        confidence: float = 0.99,
        liquidation_days: int = 5,
        position_size: float = 1.0,
        avg_daily_volume: float = 1.0,
        bid_ask_spread: float = 0.001,
        market_impact_coeff: float = 0.1,
        portfolio_value: float = 1.0,
    ) -> LiquidityAdjustedVaRResult:
        """Calculate Liquidity-adjusted VaR.

        L-VaR combines market risk VaR with liquidity costs:

        1. Base VaR = parametric VaR scaled by sqrt(liquidation_days)
        2. Spread cost = 0.5 * bid_ask_spread * portfolio_value
        3. Market impact = market_impact_coeff * sqrt(participation_rate) * portfolio_value
        4. L-VaR = Base_VaR + Spread_cost + Market_impact

        where participation_rate = position_size / avg_daily_volume

        Args:
            returns: Array of historical returns.
            volumes: Optional array of daily trading volumes.
            confidence: Confidence level for VaR.
            liquidation_days: Number of days to liquidate position.
            position_size: Size of the position in units.
            avg_daily_volume: Average daily trading volume.
            bid_ask_spread: Bid-ask spread as fraction of price.
            market_impact_coeff: Market impact coefficient (Almgren-Chriss).
            portfolio_value: Total portfolio value.

        Returns:
            LiquidityAdjustedVaRResult with adjusted VaR.
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return LiquidityAdjustedVaRResult(
                base_var=0.0,
                liquidity_adjustment=0.0,
                adjusted_var=0.0,
                liquidation_cost=0.0,
                liquidation_time=float(liquidation_days),
            )

        # Use volumes to compute average if provided
        if volumes is not None:
            volumes = np.asarray(volumes, dtype=np.float64)
            volumes = volumes[~np.isnan(volumes)]
            if len(volumes) > 0:
                avg_daily_volume = float(np.mean(volumes))

        # Base parametric VaR
        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        alpha = 1 - confidence
        z_alpha = sp_stats.norm.ppf(1 - alpha)

        if std <= 0:
            base_var = 0.0
        else:
            # VaR scaled for liquidation period using sqrt-of-time
            base_var = abs((-mean + z_alpha * std) * np.sqrt(liquidation_days) * portfolio_value)

        # Liquidity adjustments
        # 1. Spread cost (half spread for one-way trade)
        spread_cost = 0.5 * bid_ask_spread * portfolio_value

        # 2. Market impact (Almgren-Chriss square-root model)
        participation_rate = position_size / avg_daily_volume if avg_daily_volume > 0 else 1.0
        market_impact = market_impact_coeff * np.sqrt(participation_rate) * portfolio_value

        liquidity_adjustment = spread_cost + market_impact

        # Adjusted VaR
        adjusted_var = base_var + liquidity_adjustment

        # Liquidation cost
        liquidation_cost = spread_cost + market_impact

        return LiquidityAdjustedVaRResult(
            base_var=round(base_var, 2),
            liquidity_adjustment=round(liquidity_adjustment, 2),
            adjusted_var=round(adjusted_var, 2),
            liquidation_cost=round(liquidation_cost, 2),
            liquidation_time=round(float(liquidation_days), 2),
        )


# ══════════════════════════════════════════════════════════════════════
# RiskModels (Unified Interface — Backward Compatible)
# ══════════════════════════════════════════════════════════════════════


class RiskModels:
    """Advanced risk models for portfolio risk management.

    Unified interface providing VaR, CVaR, stress testing, copula-based
    joint risk, correlation breakdown detection, and liquidity-adjusted VaR.

    Delegates to the specialized classes: ValueAtRisk, ConditionalVaR,
    ComponentVaR, StressTestFramework, LiquidityAdjustedVaR.

    Usage:
        model = RiskModels(bars_per_year=252)
        var_result = model.calculate_var(returns, confidence_levels=[0.95, 0.99])
        stress = model.stress_test(returns, portfolio_value=1_000_000)
        breakdown = model.detect_correlation_breakdown(returns_df)
    """

    def __init__(
        self,
        bars_per_year: int = 252,
        default_confidence: float = 0.95,
        num_mc_simulations: int = 10000,
        random_seed: Optional[int] = None,
    ) -> None:
        """Initialize risk models.

        Args:
            bars_per_year: Bars per year for annualization.
            default_confidence: Default confidence level for VaR.
            num_mc_simulations: Number of Monte Carlo simulations.
            random_seed: Random seed for reproducibility.
        """
        self.bars_per_year = bars_per_year
        self.default_confidence = default_confidence
        self.num_mc_simulations = num_mc_simulations
        self.random_seed = random_seed

        # Initialize sub-models
        self.var_calc = ValueAtRisk()
        self.cvar_calc = ConditionalVaR()
        self.comp_var_calc = ComponentVaR()
        self.stress_framework = StressTestFramework(bars_per_year=bars_per_year)
        self.lvar_calc = LiquidityAdjustedVaR()

    # ══════════════════════════════════════════════════════════════════
    # Value-at-Risk Methods
    # ══════════════════════════════════════════════════════════════════

    def calculate_var(
        self,
        returns: np.ndarray,
        confidence_levels: Optional[List[float]] = None,
        method: VaRMethod = VaRMethod.HISTORICAL,
        portfolio_value: float = 1.0,
        num_simulations: Optional[int] = None,
    ) -> VaRResult:
        """Calculate VaR and CVaR at multiple confidence levels.

        Args:
            returns: Array of historical returns.
            confidence_levels: List of confidence levels (e.g. [0.90, 0.95, 0.99]).
            method: VaR calculation method.
            portfolio_value: Portfolio value for monetary VaR.
            num_simulations: Override number of MC simulations.

        Returns:
            VaRResult with VaR and CVaR at each confidence level.
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return VaRResult(
                method="insufficient_data",
                confidence_levels=confidence_levels or [],
                var_values={}, cvar_values={},
                portfolio_value=portfolio_value,
            )

        if confidence_levels is None:
            confidence_levels = [0.90, 0.95, 0.99]

        n_sims = num_simulations or self.num_mc_simulations

        var_values: Dict[float, float] = {}
        cvar_values: Dict[float, float] = {}

        for cl in confidence_levels:
            var_val, cvar_val = self._calculate_single_var(
                returns, cl, method, portfolio_value, n_sims
            )
            var_values[cl] = var_val
            cvar_values[cl] = cvar_val

        return VaRResult(
            method=method.value,
            confidence_levels=confidence_levels,
            var_values=var_values,
            cvar_values=cvar_values,
            portfolio_value=portfolio_value,
        )

    def _calculate_single_var(
        self,
        returns: np.ndarray,
        confidence: float,
        method: VaRMethod,
        portfolio_value: float,
        num_simulations: int,
    ) -> Tuple[float, float]:
        """Calculate VaR and CVaR for a single confidence level."""
        alpha = 1 - confidence

        if method == VaRMethod.PARAMETRIC:
            var_val = ValueAtRisk.parametric_var(returns, confidence) * portfolio_value
            cvar_val = ConditionalVaR.parametric_cvar(returns, confidence) * portfolio_value
        elif method == VaRMethod.HISTORICAL:
            var_val = ValueAtRisk.historical_var(returns, confidence) * portfolio_value
            cvar_val = ConditionalVaR.historical_cvar(returns, confidence) * portfolio_value
        elif method == VaRMethod.MONTE_CARLO:
            var_val = ValueAtRisk.monte_carlo_var(
                returns, confidence, n_sims=num_simulations,
                random_seed=self.random_seed,
            ) * portfolio_value
            cvar_val = var_val * 1.2  # Approximate CVaR from MC VaR
        elif method == VaRMethod.CORNISH_FISHER:
            var_val = ValueAtRisk.cornish_fisher_var(returns, confidence) * portfolio_value
            cvar_val = var_val * 1.2  # Conservative approximation
        else:
            var_val = ValueAtRisk.historical_var(returns, confidence) * portfolio_value
            cvar_val = ConditionalVaR.historical_cvar(returns, confidence) * portfolio_value

        return var_val, cvar_val

    # ══════════════════════════════════════════════════════════════════
    # Component and Marginal VaR
    # ══════════════════════════════════════════════════════════════════

    def component_var(
        self,
        returns_df: pd.DataFrame,
        weights: np.ndarray,
        confidence: float = 0.95,
        portfolio_value: float = 1.0,
    ) -> ComponentVaRResult:
        """Calculate Component VaR and Marginal VaR.

        Args:
            returns_df: DataFrame of asset returns (each column = asset).
            weights: Portfolio weights.
            confidence: Confidence level.
            portfolio_value: Total portfolio value.

        Returns:
            ComponentVaRResult with component, marginal, and percentage VaR.
        """
        cov_matrix = returns_df.cov().values
        symbols = list(returns_df.columns)

        result = ComponentVaR.component_var(
            weights, cov_matrix, confidence, symbols,
        )

        # Scale by portfolio value
        return ComponentVaRResult(
            component_var={k: v * portfolio_value for k, v in result.component_var.items()},
            marginal_var={k: v * portfolio_value for k, v in result.marginal_var.items()},
            percentage_contrib=result.percentage_contrib,
            total_var=result.total_var * portfolio_value,
        )

    # ══════════════════════════════════════════════════════════════════
    # Conditional Drawdown-at-Risk
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def conditional_drawdown_at_risk(
        equity_series: pd.Series,
        confidence: float = 0.95,
    ) -> float:
        """Calculate Conditional Drawdown-at-Risk (CDaR).

        CDaR is the average of the worst (1-confidence) fraction
        of drawdowns.

        Args:
            equity_series: Equity curve.
            confidence: Confidence level.

        Returns:
            CDaR value (negative, representing drawdown).
        """
        peak = equity_series.cummax()
        drawdowns = (equity_series - peak) / peak.replace(0, 1)
        dd_values = drawdowns[drawdowns < 0].values

        if len(dd_values) == 0:
            return 0.0

        alpha = 1 - confidence
        n_tail = max(1, int(len(dd_values) * alpha))
        sorted_dd = np.sort(dd_values)
        cdar = float(np.mean(sorted_dd[:n_tail]))

        return cdar

    # ══════════════════════════════════════════════════════════════════
    # Stress Testing
    # ══════════════════════════════════════════════════════════════════

    def stress_test(
        self,
        returns: pd.Series,
        portfolio_value: float = 1_000_000.0,
        scenarios: Optional[Dict[str, Tuple[str, float, float]]] = None,
    ) -> List[StressTestResult]:
        """Run stress tests on portfolio.

        Args:
            returns: Historical returns series.
            portfolio_value: Current portfolio value.
            scenarios: Dict of {name: (description, return_shock, vol_multiplier)}.

        Returns:
            List of StressTestResult for each scenario.
        """
        return self.stress_framework.scenario_analysis(returns, scenarios, portfolio_value)

    # ══════════════════════════════════════════════════════════════════
    # Copula-Based Joint Risk
    # ══════════════════════════════════════════════════════════════════

    def copula_var(
        self,
        returns_df: pd.DataFrame,
        weights: np.ndarray,
        confidence: float = 0.95,
        portfolio_value: float = 1.0,
        num_simulations: Optional[int] = None,
        copula_type: str = "gaussian",
    ) -> VaRResult:
        """Copula-based joint VaR estimation.

        Models the dependency structure between assets using a copula,
        preserving non-normal marginal distributions while capturing
        tail dependency.

        Args:
            returns_df: DataFrame of asset returns.
            weights: Portfolio weights.
            confidence: Confidence level.
            portfolio_value: Portfolio value.
            num_simulations: Number of simulations.
            copula_type: 'gaussian' or 'student_t'.

        Returns:
            VaRResult with copula-based VaR and CVaR.
        """
        n_sims = num_simulations or self.num_mc_simulations
        alpha = 1 - confidence
        symbols = list(returns_df.columns)
        n_assets = len(symbols)

        # Fit marginal distributions (Student-t for each asset)
        marginals = []
        for col in symbols:
            ret = returns_df[col].dropna().values
            df_t, loc_t, scale_t = sp_stats.t.fit(ret)
            marginals.append((df_t, loc_t, scale_t))

        # Estimate correlation matrix
        corr_matrix = returns_df.corr().values

        rng = np.random.default_rng(self.random_seed)

        # Generate correlated uniform samples via copula
        if copula_type == "gaussian":
            z = rng.multivariate_normal(np.zeros(n_assets), corr_matrix, size=n_sims)
            u = sp_stats.norm.cdf(z)
        elif copula_type == "student_t":
            df_copula = 5
            z = rng.multivariate_normal(np.zeros(n_assets), corr_matrix, size=n_sims)
            chi2 = rng.chisquare(df_copula, size=n_sims)
            t_samples = z / np.sqrt((chi2 / df_copula)[:, np.newaxis])
            u = sp_stats.t.cdf(t_samples, df=df_copula)
        else:
            z = rng.multivariate_normal(np.zeros(n_assets), corr_matrix, size=n_sims)
            u = sp_stats.norm.cdf(z)

        # Transform to returns via inverse marginal CDFs
        simulated_returns = np.empty((n_sims, n_assets))
        for j in range(n_assets):
            df_t, loc_t, scale_t = marginals[j]
            simulated_returns[:, j] = sp_stats.t.ppf(u[:, j], df_t, loc=loc_t, scale=scale_t)

        # Portfolio returns
        port_sim_returns = simulated_returns @ weights

        # Calculate VaR and CVaR
        var_threshold = np.percentile(port_sim_returns, alpha * 100)
        var_val = abs(var_threshold * portfolio_value)

        tail = port_sim_returns[port_sim_returns <= var_threshold]
        if len(tail) > 0:
            cvar_val = abs(np.mean(tail) * portfolio_value)
        else:
            cvar_val = var_val

        return VaRResult(
            method=f"copula_{copula_type}",
            confidence_levels=[confidence],
            var_values={confidence: round(var_val, 6)},
            cvar_values={confidence: round(cvar_val, 6)},
            portfolio_value=portfolio_value,
        )

    # ══════════════════════════════════════════════════════════════════
    # Correlation Breakdown Detection
    # ══════════════════════════════════════════════════════════════════

    def detect_correlation_breakdown(
        self,
        returns_df: pd.DataFrame,
        short_window: int = 30,
        long_window: int = 252,
        threshold_z: float = 2.0,
    ) -> CorrelationBreakdownResult:
        """Detect correlation breakdown between assets.

        Args:
            returns_df: DataFrame of asset returns.
            short_window: Short-term window.
            long_window: Long-term window.
            threshold_z: Z-score threshold.

        Returns:
            CorrelationBreakdownResult with detection status.
        """
        n_assets = returns_df.shape[1]
        if n_assets < 2 or len(returns_df) < long_window:
            return CorrelationBreakdownResult(
                is_breakdown_detected=False,
                current_correlation=0.0,
                long_term_correlation=0.0,
                correlation_ratio=1.0,
                z_score=0.0,
                p_value=1.0,
            )

        def avg_corr(df: pd.DataFrame) -> float:
            corr = df.corr().values
            mask = np.triu(np.ones(corr.shape), k=1).astype(bool)
            vals = corr[mask]
            finite_vals = vals[np.isfinite(vals)]
            return float(np.mean(finite_vals)) if len(finite_vals) > 0 else 0.0

        long_term_corr = avg_corr(returns_df.tail(long_window))
        current_corr = avg_corr(returns_df.tail(short_window))

        rolling_corrs = []
        for i in range(long_window, len(returns_df)):
            window_data = returns_df.iloc[i - short_window : i]
            rolling_corrs.append(avg_corr(window_data))

        if len(rolling_corrs) < 2:
            return CorrelationBreakdownResult(
                is_breakdown_detected=False,
                current_correlation=current_corr,
                long_term_correlation=long_term_corr,
                correlation_ratio=current_corr / long_term_corr if abs(long_term_corr) > 1e-10 else 1.0,
                z_score=0.0,
                p_value=1.0,
            )

        mean_rolling = np.mean(rolling_corrs)
        std_rolling = np.std(rolling_corrs)

        if std_rolling > 1e-10:
            z_score = float((current_corr - mean_rolling) / std_rolling)
        else:
            z_score = 0.0

        p_value = float(2 * (1 - sp_stats.norm.cdf(abs(z_score))))
        ratio = current_corr / long_term_corr if abs(long_term_corr) > 1e-10 else 1.0

        return CorrelationBreakdownResult(
            is_breakdown_detected=abs(z_score) > threshold_z,
            current_correlation=round(current_corr, 4),
            long_term_correlation=round(long_term_corr, 4),
            correlation_ratio=round(ratio, 4),
            z_score=round(z_score, 4),
            p_value=round(p_value, 6),
        )

    # ══════════════════════════════════════════════════════════════════
    # Liquidity-Adjusted VaR
    # ══════════════════════════════════════════════════════════════════

    def liquidity_adjusted_var(
        self,
        returns: np.ndarray,
        position_size: float,
        avg_daily_volume: float,
        confidence: float = 0.95,
        portfolio_value: float = 1.0,
        bid_ask_spread: float = 0.001,
        market_impact_coeff: float = 0.1,
    ) -> LiquidityAdjustedVaRResult:
        """Calculate Liquidity-adjusted VaR (L-VaR).

        Args:
            returns: Array of historical returns.
            position_size: Size of the position in units.
            avg_daily_volume: Average daily trading volume.
            confidence: Confidence level.
            portfolio_value: Portfolio value.
            bid_ask_spread: Bid-ask spread as fraction of price.
            market_impact_coeff: Market impact coefficient.

        Returns:
            LiquidityAdjustedVaRResult with adjusted VaR.
        """
        return LiquidityAdjustedVaR.lvav(
            returns,
            confidence=confidence,
            liquidation_days=max(1, int(np.ceil(position_size / avg_daily_volume))),
            position_size=position_size,
            avg_daily_volume=avg_daily_volume,
            bid_ask_spread=bid_ask_spread,
            market_impact_coeff=market_impact_coeff,
            portfolio_value=portfolio_value,
        )

    # ══════════════════════════════════════════════════════════════════
    # Entropic Value-at-Risk
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def entropic_var(
        returns: np.ndarray,
        confidence: float = 0.95,
    ) -> float:
        """Calculate Entropic Value-at-Risk (EVaR).

        EVaR is the tightest possible Chernoff upper bound for VaR:
            EVaR_alpha = inf_{z>0} { (1/z) * ln(E[exp(z*X)] / alpha) }

        where X = -returns (loss perspective), alpha = 1 - confidence.

        Reference: Ahmadi-Javid (2012), "Entropic Value-at-Risk"

        Args:
            returns: Array of returns.
            confidence: Confidence level.

        Returns:
            EVaR value.
        """
        from scipy.optimize import minimize_scalar

        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return 0.0

        alpha = 1 - confidence
        losses = -returns

        def objective(z: float) -> float:
            if z <= 0:
                return 1e10
            try:
                moment_gen = np.mean(np.exp(z * losses))
                return (1.0 / z) * (np.log(moment_gen) - np.log(alpha))
            except (OverflowError, ValueError):
                return 1e10

        try:
            res = minimize_scalar(objective, bounds=(1e-6, 50.0), method="bounded")
            return float(res.fun)
        except Exception:
            return float(np.percentile(losses, confidence * 100))
