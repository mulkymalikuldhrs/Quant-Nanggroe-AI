"""Barra Risk Model Factors.

Implements the MSCI Barra risk model factor exposures used in
institutional portfolio risk management. These factors capture
systematic risk exposures across multiple dimensions.

Factor categories:
- SIZE: Market capitalization exposure (large vs small)
- VALUE: Book-to-market / earnings yield exposure
- MOMENTUM: Price momentum exposure (intermediate horizon)
- VOLATILITY: Residual volatility exposure (high vs low beta)
- LIQUIDITY: Trading volume / turnover exposure
- QUALITY: Profitability and earnings stability
- GROWTH: Earnings and revenue growth exposure
- LEVERAGE: Financial leverage exposure

Industry neutralization is supported via GICS sector dummy variables.

Reference: MSCI Barra USE4 Risk Model (2013)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    FactorMeta,
    delay,
    delta,
    rank,
    safe_div,
    ts_corr,
    ts_mean,
    ts_std,
    ts_sum,
)


def _s(df: pd.DataFrame | pd.Series) -> pd.Series:
    """Extract Series from DataFrame (mean across columns) or pass through."""
    if isinstance(df, pd.DataFrame):
        return df.mean(axis=1)
    return df


# ─── SIZE Factor ─────────────────────────────────────────────────────────────
class BarraSIZE(AlphaFactor):
    """Barra SIZE factor — log market capitalization.

    Formula: log(market_cap)
    Captures large-cap vs small-cap exposure. Standard Barra risk factor.
    Typically industry-neutralized in production use.
    """

    @property
    def name(self) -> str:
        return "barra_size"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_size",
            zoo="barra",
            theme=["risk", "size"],
            formula_latex=r"\log(\text{MC})",
            columns_required=["market_cap"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Log market cap; industry-neutralize for pure size exposure",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "market_cap" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="barra_size")
        mc = df["market_cap"]
        result = np.log(mc.where(mc > 0))
        return result


# ─── SIZE_NL Factor ──────────────────────────────────────────────────────────
class BarraSIZE_NL(AlphaFactor):
    """Barra SIZE non-linearity factor — cubic deviation from log market cap.

    Formula: (log(market_cap) - mean(log(market_cap)))^3
    Captures the non-linear (cubic) relationship of size with returns.
    Small caps and mega caps have higher exposure; mid-caps lower.
    """

    @property
    def name(self) -> str:
        return "barra_size_nl"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_size_nl",
            zoo="barra",
            theme=["risk", "size"],
            formula_latex=r"(\log(\text{MC}) - \overline{\log(\text{MC})})^3",
            columns_required=["market_cap"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Non-linear size (cubic); captures small-cap and mega-cap effects",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "market_cap" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="barra_size_nl")
        log_mc = np.log(df["market_cap"].where(df["market_cap"] > 0))
        result = (log_mc - log_mc.mean()) ** 3
        return result


# ─── VALUE Factor ────────────────────────────────────────────────────────────
class BarraVALUE(AlphaFactor):
    """Barra VALUE factor — book-to-market ratio.

    Formula: log(book_value / market_cap)
    Captures value vs growth exposure. Higher B/M = value orientation.
    Often combined with earnings yield for a composite value signal.
    """

    @property
    def name(self) -> str:
        return "barra_value"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_value",
            zoo="barra",
            theme=["risk", "value"],
            formula_latex=r"\log(\text{BV} / \text{MC})",
            columns_required=["market_cap", "book_value"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Log book-to-market; core value factor in Barra USE4",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "market_cap" not in df.columns or "book_value" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="barra_value")
        bv = df["book_value"]
        mc = df["market_cap"]
        ratio = safe_div(bv, mc)
        result = np.log(ratio.where(ratio > 0))
        return result


# ─── MOMENTUM Factor ─────────────────────────────────────────────────────────
class BarraMOMENTUM(AlphaFactor):
    """Barra MOMENTUM factor — intermediate-horizon price momentum.

    Formula: log(close / delay(close, T)) where T=252 (1y) with
             recent 1-month returns excluded to avoid reversal effects.
    Captures trend-following exposure over 12-month horizon.
    """

    @property
    def name(self) -> str:
        return "barra_momentum"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_momentum",
            zoo="barra",
            theme=["risk", "momentum"],
            formula_latex=r"\log(C_t / C_{t-252+21})",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=252,
            min_warmup_bars=252,
            notes="12-month momentum excluding most recent 21 days (reversal window)",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        # 12-month momentum excluding last 1 month (21 trading days)
        past = delay(c, 252)
        recent = delay(c, 21)
        result = np.log(safe_div(recent, past))
        return result.replace([np.inf, -np.inf], np.nan)


# ─── VOLATILITY Factor ───────────────────────────────────────────────────────
class BarraVOLATILITY(AlphaFactor):
    """Barra VOLATILITY factor — residual volatility.

    Formula: ts_std(returns - beta * market_returns, 252)
    Captures idiosyncratic volatility exposure. High residual vol
    tends to earn negative risk premium.
    When market returns unavailable, uses total return volatility.
    """

    @property
    def name(self) -> str:
        return "barra_volatility"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_volatility",
            zoo="barra",
            theme=["risk", "volatility"],
            formula_latex=r"\sigma(r - \beta r_m, 252)",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=252,
            min_warmup_bars=252,
            notes="Residual volatility; falls back to total vol if market data absent",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        returns = c.pct_change()
        if "market_returns" in df.columns:
            # Compute residual volatility
            mr = df["market_returns"]
            # Rolling beta estimate
            cov_rm = returns.rolling(252, min_periods=252).cov(mr)
            var_m = mr.rolling(252, min_periods=252).var(ddof=1)
            beta = cov_rm / var_m.replace(0, np.nan)
            residual = returns - beta * mr
            result = residual.rolling(252, min_periods=252).std(ddof=1)
        else:
            # Fallback to total volatility
            result = ts_std(returns, 252)
        return result


# ─── LIQUIDITY Factor ────────────────────────────────────────────────────────
class BarraLIQUIDITY(AlphaFactor):
    """Barra LIQUIDITY factor — trading volume / turnover.

    Formula: log(ts_mean(volume * close, 20))
    Captures exposure to trading liquidity. Low-liquidity stocks
    tend to earn a liquidity premium.
    """

    @property
    def name(self) -> str:
        return "barra_liquidity"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_liquidity",
            zoo="barra",
            theme=["risk", "liquidity"],
            formula_latex=r"\log(\text{ts\_mean}(V \cdot C, 20))",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=20,
            min_warmup_bars=21,
            notes="Log average dollar volume; low liquidity earns premium",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        dollar_vol = v * c
        avg_dv = ts_mean(dollar_vol, 20)
        result = np.log(avg_dv.where(avg_dv > 0))
        return result


# ─── QUALITY Factor ──────────────────────────────────────────────────────────
class BarraQUALITY(AlphaFactor):
    """Barra QUALITY (Earnings Yield) factor.

    Formula: log(eps / close) = -log(P/E)
    Captures profitability / earnings yield exposure. Higher E/P
    = higher quality / value orientation.
    """

    @property
    def name(self) -> str:
        return "barra_quality"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_quality",
            zoo="barra",
            theme=["risk", "quality"],
            formula_latex=r"\log(\text{EPS} / C) = -\log(P/E)",
            columns_required=["close", "eps"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Earnings yield; inverse of P/E ratio in log space",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "eps" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="barra_quality")
        c = df["close"]
        eps = df["eps"]
        ep = safe_div(eps, c)
        result = np.log(ep.where(ep > 0))
        return result


# ─── GROWTH Factor ───────────────────────────────────────────────────────────
class BarraGROWTH(AlphaFactor):
    """Barra GROWTH factor — earnings growth rate.

    Formula: (eps_t - eps_t-1) / |eps_t-1|
    Captures exposure to earnings growth. Growth stocks have
    higher growth factor exposure.
    """

    @property
    def name(self) -> str:
        return "barra_growth"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_growth",
            zoo="barra",
            theme=["risk", "growth"],
            formula_latex=r"\frac{\text{EPS}_t - \text{EPS}_{t-1}}{|\text{EPS}_{t-1}|}",
            columns_required=["eps"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=2,
            notes="YoY earnings growth rate",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "eps" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="barra_growth")
        eps = df["eps"]
        prev_eps = delay(eps, 1)
        result = safe_div(eps - prev_eps, prev_eps.abs())
        return result.replace([np.inf, -np.inf], np.nan)


# ─── LEVERAGE Factor ─────────────────────────────────────────────────────────
class BarraLEVERAGE(AlphaFactor):
    """Barra LEVERAGE factor — financial leverage.

    Formula: total_debt / (total_debt + shareholders_equity)
    Captures exposure to financial leverage. Higher leverage
    implies higher financial risk and potential distress.
    """

    @property
    def name(self) -> str:
        return "barra_leverage"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_leverage",
            zoo="barra",
            theme=["risk", "leverage"],
            formula_latex=r"\frac{\text{TD}}{\text{TD} + \text{SE}}",
            columns_required=["total_debt", "shareholders_equity"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Debt ratio; captures financial leverage exposure",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "total_debt" not in df.columns or "shareholders_equity" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="barra_leverage")
        td = df["total_debt"]
        se = df["shareholders_equity"]
        result = safe_div(td, td + se)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── BETA Factor ─────────────────────────────────────────────────────────────
class BarraBETA(AlphaFactor):
    """Barra BETA factor — market beta.

    Formula: ts_cov(returns, market_returns, 252) / ts_var(market_returns, 252)
    Captures systematic market risk exposure. Higher beta = higher
    sensitivity to market movements.
    Falls back to 1.0 if market data unavailable.
    """

    @property
    def name(self) -> str:
        return "barra_beta"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_beta",
            zoo="barra",
            theme=["risk", "beta"],
            formula_latex=r"\beta = \frac{\text{cov}(r, r_m)}{\text{var}(r_m)}",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=252,
            min_warmup_bars=252,
            notes="Rolling 252-day market beta; falls back to 1.0 if no market data",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        returns = c.pct_change()
        if "market_returns" in df.columns:
            mr = df["market_returns"]
            cov_rm = returns.rolling(252, min_periods=252).cov(mr)
            var_m = mr.rolling(252, min_periods=252).var(ddof=1)
            result = cov_rm / var_m.replace(0, np.nan)
        else:
            # Fallback: use close / market_cap as proxy or return 1.0
            result = pd.Series(np.nan, index=df.index, name="barra_beta")
        return result.replace([np.inf, -np.inf], np.nan)


# ─── DIVIDEND YIELD Factor ───────────────────────────────────────────────────
class BarraDIVYIELD(AlphaFactor):
    """Barra Dividend Yield factor.

    Formula: dividends_per_share / close
    Captures exposure to dividend income. High dividend yield
    stocks tend to be value-oriented.
    """

    @property
    def name(self) -> str:
        return "barra_divyield"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="barra_divyield",
            zoo="barra",
            theme=["risk", "value"],
            formula_latex=r"\frac{\text{DPS}}{C}",
            columns_required=["close", "dividends_per_share"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Dividend yield; value-oriented risk factor",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "dividends_per_share" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="barra_divyield")
        c = df["close"]
        dps = df["dividends_per_share"]
        result = safe_div(dps, c)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── INDUSTRY NEUTRALIZATION ─────────────────────────────────────────────────

def industry_neutralize(
    factor_values: pd.Series,
    industry_dummies: pd.DataFrame,
) -> pd.Series:
    """Neutralize factor exposures against industry dummies.

    Regresses factor values on industry dummy variables and returns
    the residual (industry-orthogonalized) factor values.

    Args:
        factor_values: Cross-sectional factor values (index = instruments).
        industry_dummies: One-hot industry dummy matrix (index = instruments,
            columns = industry codes).

    Returns:
        Industry-neutralized factor values (same index as input).
    """
    # Align indices
    common_idx = factor_values.index.intersection(industry_dummies.index)
    if common_idx.empty:
        return factor_values

    y = factor_values.loc[common_idx]
    X = industry_dummies.loc[common_idx]

    # Drop rows with NaN in y or X
    valid = y.notna() & X.notna().all(axis=1)
    if valid.sum() < X.shape[1] + 1:
        return factor_values

    y_valid = y[valid]
    X_valid = X[valid]

    # Add intercept
    X_with_const = np.column_stack([np.ones(len(X_valid)), X_valid.values])

    # OLS regression: y = X @ beta + epsilon
    try:
        beta, _, _, _ = np.linalg.lstsq(X_with_const, y_valid.values, rcond=None)
        predicted = X_with_const @ beta
        residual = y_valid.values - predicted
        result = factor_values.copy()
        result.loc[valid] = residual
        return result
    except np.linalg.LinAlgError:
        return factor_values


def compute_factor_exposure(
    factor_values: pd.DataFrame,
    industry_dummies: pd.DataFrame,
    neutralize: bool = True,
) -> pd.DataFrame:
    """Compute factor exposures for a cross-section of instruments.

    Optionally neutralizes against industry dummies.

    Args:
        factor_values: DataFrame where each column is a factor, index = instruments.
        industry_dummies: One-hot industry dummy matrix (index = instruments).
        neutralize: Whether to industry-neutralize each factor.

    Returns:
        DataFrame of factor exposures (neutralized if requested).
    """
    result = factor_values.copy()

    if neutralize and not industry_dummies.empty:
        for col in result.columns:
            result[col] = industry_neutralize(result[col], industry_dummies)

    return result


def risk_decomposition(
    factor_exposures: pd.DataFrame,
    factor_covariance: pd.DataFrame,
    specific_risk: pd.Series,
) -> dict:
    """Decompose total risk into factor risk and specific risk.

    Args:
        factor_exposures: Factor exposure matrix (instruments x factors).
        factor_covariance: Factor covariance matrix (factors x factors).
        specific_risk: Instrument-specific risk (idiosyncratic vol).

    Returns:
        Dict with total_risk, factor_risk, specific_risk, factor_contribution.
    """
    # Factor risk: B @ Sigma_f @ B^T
    factor_risk_var = factor_exposures.values @ factor_covariance.values @ factor_exposures.values.T
    factor_risk = pd.DataFrame(
        np.diag(factor_risk_var) ** 0.5,
        index=factor_exposures.index,
        columns=["factor_risk"],
    )

    # Specific risk
    spec_risk = specific_risk.reindex(factor_exposures.index).fillna(0)

    # Total risk
    total_var = np.diag(factor_risk_var) + spec_risk.values ** 2
    total_risk = pd.Series(total_var ** 0.5, index=factor_exposures.index, name="total_risk")

    # Factor contribution (marginal contribution to risk)
    factor_contrib = pd.DataFrame(
        factor_exposures.values * (factor_covariance.values @ factor_exposures.values.T).T,
        index=factor_exposures.index,
        columns=factor_exposures.columns,
    )

    return {
        "total_risk": total_risk,
        "factor_risk": factor_risk,
        "specific_risk": spec_risk,
        "factor_contribution": factor_contrib,
    }


# ─── Factor Registry ─────────────────────────────────────────────────────────

def get_all_barra_factors() -> list:
    """Return instances of all implemented Barra risk factors."""
    return [
        BarraSIZE(),
        BarraSIZE_NL(),
        BarraVALUE(),
        BarraMOMENTUM(),
        BarraVOLATILITY(),
        BarraLIQUIDITY(),
        BarraQUALITY(),
        BarraGROWTH(),
        BarraLEVERAGE(),
        BarraBETA(),
        BarraDIVYIELD(),
    ]
