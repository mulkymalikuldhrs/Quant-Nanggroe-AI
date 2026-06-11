"""Fundamental Factors — P/E, P/B, ROE, etc.

Implements fundamental analysis factors for equity markets. These factors
require fundamental data columns in the input DataFrame (earnings, book value, etc.).

Categories:
- Value: P/E, P/B, P/S, EV/EBITDA
- Quality: ROE, ROA, debt-to-equity
- Growth: earnings growth, revenue growth
- Dividend: dividend yield, payout ratio

Note: If fundamental data is not available in the input DataFrame, these
factors will return NaN gracefully rather than raising errors.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import AlphaFactor, FactorMeta


class PEFactor(AlphaFactor):
    """Price-to-Earnings ratio factor.

    Formula: close / eps
    Lower P/E may indicate value; negative earnings produce negative P/E.
    """

    @property
    def name(self) -> str:
        return "pe_ratio"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_pe_ratio",
            zoo="fundamental",
            theme=["value"],
            formula_latex=r"\frac{C_t}{\text{EPS}}",
            columns_required=["close", "eps"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Requires 'eps' column in input DataFrame",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "eps" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="pe_ratio")
        close = df["close"]
        eps = df["eps"]
        result = close / eps.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class PBFactor(AlphaFactor):
    """Price-to-Book ratio factor.

    Formula: close / book_value_per_share
    """

    @property
    def name(self) -> str:
        return "pb_ratio"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_pb_ratio",
            zoo="fundamental",
            theme=["value"],
            formula_latex=r"\frac{C_t}{\text{BVPS}}",
            columns_required=["close", "book_value_per_share"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "book_value_per_share" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="pb_ratio")
        close = df["close"]
        bvps = df["book_value_per_share"]
        result = close / bvps.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class PSFactor(AlphaFactor):
    """Price-to-Sales ratio factor.

    Formula: market_cap / revenue (or close / sales_per_share)
    """

    @property
    def name(self) -> str:
        return "ps_ratio"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_ps_ratio",
            zoo="fundamental",
            theme=["value"],
            formula_latex=r"\frac{C_t}{\text{SPS}}",
            columns_required=["close", "sales_per_share"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "sales_per_share" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="ps_ratio")
        close = df["close"]
        sps = df["sales_per_share"]
        result = close / sps.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class ROEFactor(AlphaFactor):
    """Return on Equity factor.

    Formula: net_income / shareholders_equity
    """

    @property
    def name(self) -> str:
        return "roe"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_roe",
            zoo="fundamental",
            theme=["quality"],
            formula_latex=r"\frac{\text{NI}}{\text{SE}}",
            columns_required=["net_income", "shareholders_equity"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Higher ROE indicates better capital efficiency",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "net_income" not in df.columns or "shareholders_equity" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="roe")
        ni = df["net_income"]
        se = df["shareholders_equity"]
        result = ni / se.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class ROAFactor(AlphaFactor):
    """Return on Assets factor.

    Formula: net_income / total_assets
    """

    @property
    def name(self) -> str:
        return "roa"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_roa",
            zoo="fundamental",
            theme=["quality"],
            formula_latex=r"\frac{\text{NI}}{\text{TA}}",
            columns_required=["net_income", "total_assets"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "net_income" not in df.columns or "total_assets" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="roa")
        ni = df["net_income"]
        ta = df["total_assets"]
        result = ni / ta.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class DebtToEquityFactor(AlphaFactor):
    """Debt-to-Equity ratio factor.

    Formula: total_debt / shareholders_equity
    """

    @property
    def name(self) -> str:
        return "debt_to_equity"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_debt_to_equity",
            zoo="fundamental",
            theme=["quality", "leverage"],
            formula_latex=r"\frac{\text{TD}}{\text{SE}}",
            columns_required=["total_debt", "shareholders_equity"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Lower D/E generally indicates less financial risk",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "total_debt" not in df.columns or "shareholders_equity" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="debt_to_equity")
        td = df["total_debt"]
        se = df["shareholders_equity"]
        result = td / se.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class EarningsGrowthFactor(AlphaFactor):
    """Earnings growth rate factor.

    Formula: (eps_t - eps_t-1) / |eps_t-1|
    """

    @property
    def name(self) -> str:
        return "earnings_growth"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_earnings_growth",
            zoo="fundamental",
            theme=["growth"],
            formula_latex=r"\frac{\text{EPS}_t - \text{EPS}_{t-1}}{|\text{EPS}_{t-1}|}",
            columns_required=["eps"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "eps" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="earnings_growth")
        eps = df["eps"]
        prev_eps = eps.shift(1)
        result = (eps - prev_eps) / prev_eps.abs().replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class DividendYieldFactor(AlphaFactor):
    """Dividend yield factor.

    Formula: dividends_per_share / close
    """

    @property
    def name(self) -> str:
        return "dividend_yield"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_dividend_yield",
            zoo="fundamental",
            theme=["value"],
            formula_latex=r"\frac{\text{DPS}}{C_t}",
            columns_required=["close", "dividends_per_share"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "dividends_per_share" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="dividend_yield")
        close = df["close"]
        dps = df["dividends_per_share"]
        result = dps / close.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


def get_all_fundamental_factors() -> list:
    """Return instances of all implemented fundamental factors."""
    return [
        PEFactor(),
        PBFactor(),
        PSFactor(),
        ROEFactor(),
        ROAFactor(),
        DebtToEquityFactor(),
        EarningsGrowthFactor(),
        DividendYieldFactor(),
    ]
