"""Fundamental Factors — Valuation, Quality, Growth, and Dividend.

Implements fundamental analysis factors for equity markets. These factors
require fundamental data columns in the input DataFrame (earnings, book value, etc.).

Categories:
- Value: P/E, P/B, P/S, P/CF, EV/EBITDA
- Quality: ROE, ROA, Debt-to-Equity, Interest Coverage
- Growth: Earnings growth, Revenue growth
- Dividend: Dividend yield, Payout ratio
- Cash Flow: Free cash flow yield, Operating cash flow ratio

Note: If fundamental data is not available in the input DataFrame, these
factors will return NaN gracefully rather than raising errors.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import AlphaFactor, FactorMeta, delay, safe_div, ts_mean


# ─── VALUE FACTORS ───────────────────────────────────────────────────────────

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
        result = safe_div(close, eps)
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
        result = safe_div(close, bvps)
        return result.replace([np.inf, -np.inf], np.nan)


class PSFactor(AlphaFactor):
    """Price-to-Sales ratio factor.

    Formula: close / sales_per_share
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
        result = safe_div(close, sps)
        return result.replace([np.inf, -np.inf], np.nan)


class PCFFactor(AlphaFactor):
    """Price-to-Cash-Flow ratio factor.

    Formula: close / operating_cash_flow_per_share
    Lower P/CF suggests better value; cash flow is harder to manipulate than earnings.
    """

    @property
    def name(self) -> str:
        return "pcf_ratio"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_pcf_ratio",
            zoo="fundamental",
            theme=["value"],
            formula_latex=r"\frac{C_t}{\text{OCFPS}}",
            columns_required=["close", "operating_cash_flow_per_share"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Cash flow is harder to manipulate than earnings; robust value signal",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "operating_cash_flow_per_share" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="pcf_ratio")
        close = df["close"]
        ocfps = df["operating_cash_flow_per_share"]
        result = safe_div(close, ocfps)
        return result.replace([np.inf, -np.inf], np.nan)


class EVEBITDAFactor(AlphaFactor):
    """EV/EBITDA ratio factor.

    Formula: (market_cap + total_debt - cash) / ebitda
    Capital-structure-neutral valuation metric. Lower EV/EBITDA = cheaper.
    """

    @property
    def name(self) -> str:
        return "ev_ebitda"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_ev_ebitda",
            zoo="fundamental",
            theme=["value"],
            formula_latex=r"\frac{\text{MC} + \text{TD} - \text{Cash}}{\text{EBITDA}}",
            columns_required=["market_cap", "total_debt", "cash", "ebitda"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Capital-structure-neutral; more comparable across firms than P/E",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        required = ["market_cap", "total_debt", "cash", "ebitda"]
        if any(c not in df.columns for c in required):
            return pd.Series(np.nan, index=df.index, name="ev_ebitda")
        ev = df["market_cap"] + df["total_debt"] - df["cash"]
        result = safe_div(ev, df["ebitda"])
        return result.replace([np.inf, -np.inf], np.nan)


# ─── QUALITY FACTORS ─────────────────────────────────────────────────────────

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
        result = safe_div(ni, se)
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
        result = safe_div(ni, ta)
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
        result = safe_div(td, se)
        return result.replace([np.inf, -np.inf], np.nan)


class InterestCoverageFactor(AlphaFactor):
    """Interest Coverage Ratio factor.

    Formula: ebit / interest_expense
    Higher coverage = better ability to service debt.
    """

    @property
    def name(self) -> str:
        return "interest_coverage"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_interest_coverage",
            zoo="fundamental",
            theme=["quality", "leverage"],
            formula_latex=r"\frac{\text{EBIT}}{\text{Interest}}",
            columns_required=["ebit", "interest_expense"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Higher coverage = stronger debt serviceability",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "ebit" not in df.columns or "interest_expense" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="interest_coverage")
        result = safe_div(df["ebit"], df["interest_expense"])
        return result.replace([np.inf, -np.inf], np.nan)


class OperatingMarginFactor(AlphaFactor):
    """Operating Margin factor.

    Formula: operating_income / revenue
    Higher margin = better operational efficiency and competitive moat.
    """

    @property
    def name(self) -> str:
        return "operating_margin"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_operating_margin",
            zoo="fundamental",
            theme=["quality"],
            formula_latex=r"\frac{\text{OpIncome}}{\text{Revenue}}",
            columns_required=["operating_income", "revenue"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Higher margin indicates stronger competitive moat",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "operating_income" not in df.columns or "revenue" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="operating_margin")
        result = safe_div(df["operating_income"], df["revenue"])
        return result.replace([np.inf, -np.inf], np.nan)


# ─── GROWTH FACTORS ──────────────────────────────────────────────────────────

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
        prev_eps = delay(eps, 1)
        result = safe_div(eps - prev_eps, prev_eps.abs())
        return result.replace([np.inf, -np.inf], np.nan)


class RevenueGrowthFactor(AlphaFactor):
    """Revenue growth rate factor.

    Formula: (revenue_t - revenue_t-1) / |revenue_t-1|
    """

    @property
    def name(self) -> str:
        return "revenue_growth"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_revenue_growth",
            zoo="fundamental",
            theme=["growth"],
            formula_latex=r"\frac{\text{Rev}_t - \text{Rev}_{t-1}}{|\text{Rev}_{t-1}|}",
            columns_required=["revenue"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=2,
            notes="Top-line growth; less susceptible to accounting manipulation than earnings",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "revenue" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="revenue_growth")
        rev = df["revenue"]
        prev_rev = delay(rev, 1)
        result = safe_div(rev - prev_rev, prev_rev.abs())
        return result.replace([np.inf, -np.inf], np.nan)


# ─── DIVIDEND FACTORS ────────────────────────────────────────────────────────

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
        result = safe_div(dps, close)
        return result.replace([np.inf, -np.inf], np.nan)


class PayoutRatioFactor(AlphaFactor):
    """Dividend Payout Ratio factor.

    Formula: dividends_per_share / eps
    """

    @property
    def name(self) -> str:
        return "payout_ratio"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_payout_ratio",
            zoo="fundamental",
            theme=["value"],
            formula_latex=r"\frac{\text{DPS}}{\text{EPS}}",
            columns_required=["eps", "dividends_per_share"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="High payout may indicate limited growth opportunities",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "dividends_per_share" not in df.columns or "eps" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="payout_ratio")
        result = safe_div(df["dividends_per_share"], df["eps"])
        return result.replace([np.inf, -np.inf], np.nan)


# ─── CASH FLOW FACTORS ───────────────────────────────────────────────────────

class FreeCashFlowYieldFactor(AlphaFactor):
    """Free Cash Flow Yield factor.

    Formula: (operating_cash_flow - capex) / market_cap
    One of the most robust value signals; cash is real.
    """

    @property
    def name(self) -> str:
        return "fcf_yield"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_fcf_yield",
            zoo="fundamental",
            theme=["value", "quality"],
            formula_latex=r"\frac{\text{OCF} - \text{CapEx}}{\text{MC}}",
            columns_required=["operating_cash_flow", "capex", "market_cap"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Free cash flow yield; one of the most robust value signals",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        required = ["operating_cash_flow", "capex", "market_cap"]
        if any(c not in df.columns for c in required):
            return pd.Series(np.nan, index=df.index, name="fcf_yield")
        fcf = df["operating_cash_flow"] - df["capex"]
        result = safe_div(fcf, df["market_cap"])
        return result.replace([np.inf, -np.inf], np.nan)


class OCFRatioFactor(AlphaFactor):
    """Operating Cash Flow to Net Income ratio.

    Formula: operating_cash_flow / net_income
    Ratio > 1 suggests earnings quality is high (cash-backed).
    Ratio < 1 suggests potential earnings manipulation.
    """

    @property
    def name(self) -> str:
        return "ocf_to_ni"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="fundamental_ocf_to_ni",
            zoo="fundamental",
            theme=["quality"],
            formula_latex=r"\frac{\text{OCF}}{\text{NI}}",
            columns_required=["operating_cash_flow", "net_income"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=0,
            min_warmup_bars=1,
            notes="Ratio > 1 suggests high earnings quality; < 1 flags potential manipulation",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "operating_cash_flow" not in df.columns or "net_income" not in df.columns:
            return pd.Series(np.nan, index=df.index, name="ocf_to_ni")
        result = safe_div(df["operating_cash_flow"], df["net_income"])
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Factor Registry ─────────────────────────────────────────────────────────

def get_all_fundamental_factors() -> list:
    """Return instances of all implemented fundamental factors."""
    return [
        PEFactor(),
        PBFactor(),
        PSFactor(),
        PCFFactor(),
        EVEBITDAFactor(),
        ROEFactor(),
        ROAFactor(),
        DebtToEquityFactor(),
        InterestCoverageFactor(),
        OperatingMarginFactor(),
        EarningsGrowthFactor(),
        RevenueGrowthFactor(),
        DividendYieldFactor(),
        PayoutRatioFactor(),
        FreeCashFlowYieldFactor(),
        OCFRatioFactor(),
    ]
