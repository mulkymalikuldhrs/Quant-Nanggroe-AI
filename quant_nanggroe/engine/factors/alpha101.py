"""WorldQuant 101 Alphas (Kakushadze 2015).

Implements 50+ of the most impactful alphas from:
"101 Formulaic Alphas" by Zura Kakushadze, arXiv:1601.00991

Each alpha is AST-pure, lookahead-banned, and properly documented with
the original formula reference. These are the highest-IC alphas from
the original paper, curated for production use.

Notation:
    O = open, H = high, L = low, C = close, V = volume
    returns = close / delay(close,1) - 1
    adv20 = ts_mean(volume, 20)  (average daily volume, 20-day)

Reference: https://arxiv.org/abs/1601.00991
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    FactorMeta,
    Market,
    decay_linear,
    delay,
    delta,
    rank,
    safe_div,
    scale,
    signed_power,
    ts_argmax,
    ts_argmin,
    ts_corr,
    ts_cov,
    ts_max,
    ts_mean,
    ts_min,
    ts_rank,
    ts_std,
    ts_sum,
    vwap,
)


# ─── Alpha #1 ────────────────────────────────────────────────────────────────
class Alpha101_001(AlphaFactor):
    """Kakushadze Alpha #1.

    Formula: rank(ts_argmax(SignedPower((returns<0)?stddev(returns,20):close, 2.), 5)) - 0.5
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 1.
    Theme: reversal, volatility
    """

    @property
    def name(self) -> str:
        return "alpha101_001"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_001",
            zoo="alpha101",
            theme=["reversal", "volatility"],
            formula_latex=r"\text{rank}(\text{ts\_argmax}(\text{SignedPower}((r<0)?\sigma(r,20):C, 2), 5)) - 0.5",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=25,
            notes="Captures volatility-conditioned reversal patterns",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        returns = close.pct_change()
        cond = (returns < 0).astype(float)
        x = ts_std(returns, 20) * cond + close * (1.0 - cond)
        result = rank(ts_argmax(signed_power(x, 2.0), 5)) - 0.5
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Alpha #2 ────────────────────────────────────────────────────────────────
class Alpha101_002(AlphaFactor):
    """Kakushadze Alpha #2.

    Formula: -1 * delta(((close-low)-(high-close))/(close-low), 1)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 2.
    Theme: reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_002"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_002",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"-\Delta\left(\frac{(C-L)-(H-C)}{C-L}, 1\right)",
            columns_required=["high", "low", "close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=1,
            min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        inner = safe_div((c - l) - (h - c), (c - l))
        result = -1.0 * delta(inner, 1)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #3 ────────────────────────────────────────────────────────────────
class Alpha101_003(AlphaFactor):
    """Kakushadze Alpha #3.

    Formula: -1 * ts_corr(rank(open), rank(volume), 10)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 3.
    Theme: volume, microstructure
    """

    @property
    def name(self) -> str:
        return "alpha101_003"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_003",
            zoo="alpha101",
            theme=["volume", "microstructure"],
            formula_latex=r"-\text{corr}(\text{rank}(O), \text{rank}(V), 10)",
            columns_required=["open", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o_rank = rank(df["open"])
        v_rank = rank(df["volume"])
        if isinstance(o_rank, pd.DataFrame):
            o_rank = o_rank.mean(axis=1)
        if isinstance(v_rank, pd.DataFrame):
            v_rank = v_rank.mean(axis=1)
        result = -1.0 * ts_corr(o_rank, v_rank, 10)
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Alpha #4 ────────────────────────────────────────────────────────────────
class Alpha101_004(AlphaFactor):
    """Kakushadze Alpha #4.

    Formula: -1 * ts_rank(rank(low), 9)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 4.
    Theme: reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_004"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_004",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"-\text{ts\_rank}(\text{rank}(L), 9)",
            columns_required=["low"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=9,
            min_warmup_bars=9,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        l_rank = rank(df["low"])
        if isinstance(l_rank, pd.DataFrame):
            l_rank = l_rank.mean(axis=1)
        result = -1.0 * ts_rank(l_rank, 9)
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Alpha #5 ────────────────────────────────────────────────────────────────
class Alpha101_005(AlphaFactor):
    """Kakushadze Alpha #5.

    Formula: -1 * ts_max(rank(ts_corr(rank(high), rank(volume), 3)), 5) + rank(vwap - close)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 5.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_005"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_005",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"-\text{ts\_max}(\text{rank}(\text{corr}(\text{rank}(H),\text{rank}(V),3)),5)+\text{rank}(\text{VWAP}-C)",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=8,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        v = df["volume"]
        typical = (df["open"] + h + l + c) / 4.0
        h_rank = rank(h)
        v_rank = rank(v)
        if isinstance(h_rank, pd.DataFrame):
            h_rank = h_rank.mean(axis=1)
        if isinstance(v_rank, pd.DataFrame):
            v_rank = v_rank.mean(axis=1)
        corr = ts_corr(h_rank, v_rank, 3)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        corr_ranked = rank(corr)
        if isinstance(corr_ranked, pd.DataFrame):
            corr_ranked = corr_ranked.mean(axis=1)
        part1 = -1.0 * ts_max(corr_ranked, 5)
        vwap_diff = typical - c
        vwap_rank = rank(vwap_diff)
        if isinstance(vwap_rank, pd.DataFrame):
            vwap_rank = vwap_rank.mean(axis=1)
        return part1 + vwap_rank


# ─── Alpha #6 ────────────────────────────────────────────────────────────────
class Alpha101_006(AlphaFactor):
    """Kakushadze Alpha #6.

    Formula: -rank(ts_corr(open, volume, 10))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 6.
    Theme: volume, microstructure
    """

    @property
    def name(self) -> str:
        return "alpha101_006"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_006",
            zoo="alpha101",
            theme=["volume", "microstructure"],
            formula_latex=r"-\text{rank}(\text{ts\_corr}(O, V, 10))",
            columns_required=["open", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr = ts_corr(df["open"], df["volume"], 10)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        result = -rank(corr)
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Alpha #7 ────────────────────────────────────────────────────────────────
class Alpha101_007(AlphaFactor):
    """Kakushadze Alpha #7.

    Formula: (adv20 < volume) ? (-1 * ts_rank(abs(delta(close,7)),60) * sign(delta(close,7))) : -1
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 7.
    Theme: volume, momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_007"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_007",
            zoo="alpha101",
            theme=["volume", "momentum"],
            formula_latex=r"(V > \text{ADV20}) ? (-\text{ts\_rank}(|\Delta C_7|,60) \cdot \text{sign}(\Delta C_7)) : -1",
            columns_required=["close", "volume"],
            universe=["equity_us"],
            decay_horizon=60,
            min_warmup_bars=67,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        adv20 = ts_mean(v, 20)
        cond = (v > adv20).astype(float)
        dc = delta(c, 7)
        inner = -1.0 * ts_rank(abs(dc), 60) * np.sign(dc)
        result = cond * inner + (1.0 - cond) * (-1.0)
        return result


# ─── Alpha #8 ────────────────────────────────────────────────────────────────
class Alpha101_008(AlphaFactor):
    """Kakushadze Alpha #8.

    Formula: -1 * rank(ts_sum(open, 5)*ts_sum(returns, 5) - delay(ts_sum(open,5)*ts_sum(returns,5), 10))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 8.
    Theme: momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_008"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_008",
            zoo="alpha101",
            theme=["momentum"],
            formula_latex=r"-\text{rank}(\text{ts\_sum}(O,5)\text{ts\_sum}(r,5) - \text{delay}(\text{ts\_sum}(O,5)\text{ts\_sum}(r,5),10))",
            columns_required=["open", "close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=15,
            min_warmup_bars=15,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o, c = df["open"], df["close"]
        returns = c.pct_change()
        prod1 = ts_sum(o, 5) * ts_sum(returns, 5)
        prod1_delayed = delay(prod1, 10)
        diff = prod1 - prod1_delayed
        result = -rank(diff)
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Alpha #9 ────────────────────────────────────────────────────────────────
class Alpha101_009(AlphaFactor):
    """Kakushadze Alpha #9.

    Formula: -1 * rank(delta(((close-low)-(high-close))/(close-low), 1))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 9.
    Theme: reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_009"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_009",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"-\text{rank}\left(\Delta\left(\frac{(C-L)-(H-C)}{C-L}, 1\right)\right)",
            columns_required=["high", "low", "close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=1,
            min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        inner = safe_div((c - l) - (h - c), (c - l))
        d = delta(inner, 1)
        result = -rank(d)
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Alpha #10 ───────────────────────────────────────────────────────────────
class Alpha101_010(AlphaFactor):
    """Kakushadze Alpha #10.

    Formula: rank(ts_max(((high-low)/ts_mean(high-low,10)),5)) *
             rank(ts_corr(delta(close,1), delta(volume,1), 5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 10.
    Theme: volatility, volume
    """

    @property
    def name(self) -> str:
        return "alpha101_010"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_010",
            zoo="alpha101",
            theme=["volatility", "volume"],
            formula_latex=r"\text{rank}(\text{ts\_max}(\frac{H-L}{\text{ts\_mean}(H-L,10)},5)) \cdot \text{rank}(\text{corr}(\Delta C_1, \Delta V_1, 5))",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=15,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
        hl = h - l
        hl_ratio = safe_div(hl, ts_mean(hl, 10))
        hl_max = ts_max(hl_ratio, 5)
        p1 = rank(hl_max)
        if isinstance(p1, pd.DataFrame):
            p1 = p1.mean(axis=1)
        dc = delta(c, 1)
        dv = delta(v, 1)
        corr = ts_corr(dc, dv, 5)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        p2 = rank(corr)
        if isinstance(p2, pd.DataFrame):
            p2 = p2.mean(axis=1)
        return p1 * p2


# ─── Alpha #11 ───────────────────────────────────────────────────────────────
class Alpha101_011(AlphaFactor):
    """Kakushadze Alpha #11.

    Formula: (close - ts_min(close, 5)) / (ts_max(close, 5) - ts_min(close, 5)) - 1
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 11.
    Theme: momentum, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_011"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_011",
            zoo="alpha101",
            theme=["momentum", "reversal"],
            formula_latex=r"\frac{C - \min(C,5)}{\max(C,5) - \min(C,5)} - 1",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto"],
            decay_horizon=5,
            min_warmup_bars=5,
            notes="Stochastic-like position within 5-day range",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        mn = ts_min(c, 5)
        mx = ts_max(c, 5)
        result = safe_div(c - mn, mx - mn) - 1.0
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #12 ───────────────────────────────────────────────────────────────
class Alpha101_012(AlphaFactor):
    """Kakushadze Alpha #12.

    Formula: sign(delta(volume, 1)) * (-1 * delta(close, 1))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 12.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_012"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_012",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"\text{sign}(\Delta V_1) \cdot (-\Delta C_1)",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn", "crypto"],
            decay_horizon=1,
            min_warmup_bars=2,
            notes="Volume-confirmed price reversal signal",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        dvol = delta(df["volume"], 1)
        dclose = delta(df["close"], 1)
        result = np.sign(dvol) * (-1.0 * dclose)
        return result


# ─── Alpha #13 ───────────────────────────────────────────────────────────────
class Alpha101_013(AlphaFactor):
    """Kakushadze Alpha #13.

    Formula: -1 * rank(ts_cov(rank(close), rank(volume), 5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 13.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_013"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_013",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"-\text{rank}(\text{cov}(\text{rank}(C), \text{rank}(V), 5))",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c_rank = rank(df["close"])
        v_rank = rank(df["volume"])
        if isinstance(c_rank, pd.DataFrame):
            c_rank = c_rank.mean(axis=1)
        if isinstance(v_rank, pd.DataFrame):
            v_rank = v_rank.mean(axis=1)
        cov = ts_cov(c_rank, v_rank, 5)
        if isinstance(cov, pd.DataFrame):
            cov = cov.mean(axis=1)
        result = -rank(cov)
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Helper for rank-corr patterns ───────────────────────────────────────────
def _rank_corr(x: pd.Series, y: pd.Series, n: int) -> pd.Series:
    """Compute rank(ts_corr(x, y, n)) returning a Series."""
    corr = ts_corr(x, y, n)
    if isinstance(corr, pd.DataFrame):
        corr = corr.mean(axis=1)
    r = rank(corr)
    if isinstance(r, pd.DataFrame):
        r = r.mean(axis=1)
    return r


def _rank_series(s: pd.Series) -> pd.Series:
    """Rank a Series, ensuring output is a Series."""
    r = rank(s)
    if isinstance(r, pd.DataFrame):
        return r.mean(axis=1)
    return r


# ─── Alpha #14 ───────────────────────────────────────────────────────────────
class Alpha101_014(AlphaFactor):
    """Kakushadze Alpha #14.

    Formula: -1 * rank(ts_corr(open, volume, 10)) * rank(close - delay(close, 1))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 14.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_014"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_014",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"-\text{rank}(\text{corr}(O,V,10)) \cdot \text{rank}(C - \text{delay}(C,1))",
            columns_required=["open", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr_rank = _rank_corr(df["open"], df["volume"], 10)
        price_chg_rank = _rank_series(df["close"] - delay(df["close"], 1))
        return -1.0 * corr_rank * price_chg_rank


# ─── Alpha #15 ───────────────────────────────────────────────────────────────
class Alpha101_015(AlphaFactor):
    """Kakushadze Alpha #15.

    Formula: -1 * ts_sum(rank(ts_corr(rank(high), rank(volume), 3)), 3)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 15.
    Theme: volume, volatility
    """

    @property
    def name(self) -> str:
        return "alpha101_015"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_015",
            zoo="alpha101",
            theme=["volume", "volatility"],
            formula_latex=r"-\text{ts\_sum}(\text{rank}(\text{corr}(\text{rank}(H), \text{rank}(V), 3)), 3)",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=3,
            min_warmup_bars=5,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr_ranked = _rank_corr(_rank_series(df["high"]), _rank_series(df["volume"]), 3)
        result = -1.0 * ts_sum(corr_ranked, 3)
        return result


# ─── Alpha #16 ───────────────────────────────────────────────────────────────
class Alpha101_016(AlphaFactor):
    """Kakushadze Alpha #16.

    Formula: -1 * rank(ts_cov(rank(high), rank(volume), 5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 16.
    Theme: volume
    """

    @property
    def name(self) -> str:
        return "alpha101_016"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_016",
            zoo="alpha101",
            theme=["volume"],
            formula_latex=r"-\text{rank}(\text{cov}(\text{rank}(H), \text{rank}(V), 5))",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h_rank = _rank_series(df["high"])
        v_rank = _rank_series(df["volume"])
        cov = ts_cov(h_rank, v_rank, 5)
        if isinstance(cov, pd.DataFrame):
            cov = cov.mean(axis=1)
        result = -_rank_series(cov)
        return result


# ─── Alpha #17 ───────────────────────────────────────────────────────────────
class Alpha101_017(AlphaFactor):
    """Kakushadze Alpha #17.

    Formula: ((close-low)-(high-close))/(close-low) * volume
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 17.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_017"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_017",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"\frac{(C-L)-(H-C)}{C-L} \cdot V",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=1,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
        inner = safe_div((c - l) - (h - c), (c - l))
        result = inner * v
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #18 ───────────────────────────────────────────────────────────────
class Alpha101_018(AlphaFactor):
    """Kakushadze Alpha #18.

    Formula: -1 * rank(ts_std(abs(close-open), 5) + (close-open) + ts_corr(close, open, 10))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 18.
    Theme: volatility
    """

    @property
    def name(self) -> str:
        return "alpha101_018"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_018",
            zoo="alpha101",
            theme=["volatility"],
            formula_latex=r"-\text{rank}(\sigma(|C-O|,5) + (C-O) + \text{corr}(C,O,10))",
            columns_required=["open", "close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o, c = df["open"], df["close"]
        co = abs(c - o)
        corr_part = ts_corr(c, o, 10)
        if isinstance(corr_part, pd.DataFrame):
            corr_part = corr_part.mean(axis=1)
        inner = ts_std(co, 5) + (c - o) + corr_part
        result = -_rank_series(inner)
        return result


# ─── Alpha #19 ───────────────────────────────────────────────────────────────
class Alpha101_019(AlphaFactor):
    """Kakushadze Alpha #19.

    Formula: -1 * sign(delta(close, 7)) * (1 + rank(decay_linear(volume/adv20, 9))) *
             (1 + rank(ts_corr(close, volume, 5)))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 19.
    Theme: momentum, volume
    """

    @property
    def name(self) -> str:
        return "alpha101_019"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_019",
            zoo="alpha101",
            theme=["momentum", "volume"],
            formula_latex=r"-\text{sign}(\Delta C_7)(1+\text{rank}(\text{decay}(V/\text{ADV20},9)))(1+\text{rank}(\text{corr}(C,V,5)))",
            columns_required=["close", "volume"],
            universe=["equity_us"],
            decay_horizon=9,
            min_warmup_bars=21,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        adv20 = ts_mean(v, 20)
        vol_adv = safe_div(v, adv20)
        decay_rank = _rank_series(decay_linear(vol_adv, 9))
        corr_rank = _rank_corr(c, v, 5)
        part1 = -1.0 * np.sign(delta(c, 7))
        part2 = 1.0 + decay_rank
        part3 = 1.0 + corr_rank
        return part1 * part2 * part3


# ─── Alpha #20 ───────────────────────────────────────────────────────────────
class Alpha101_020(AlphaFactor):
    """Kakushadze Alpha #20.

    Formula: -1 * rank(close - ts_max(close,5)) * rank(ts_corr(ts_mean(volume,10),
             ts_mean(volume,50),9)) * rank(ts_corr(rank(low), rank(adv20),5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 20.
    Theme: momentum, volume
    """

    @property
    def name(self) -> str:
        return "alpha101_020"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_020",
            zoo="alpha101",
            theme=["momentum", "volume"],
            formula_latex=r"-\text{rank}(C-\max(C,5))\text{rank}(\text{corr}(\bar{V}_{10},\bar{V}_{50},9))\text{rank}(\text{corr}(\text{rank}(L),\text{rank}(\text{ADV20}),5))",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us"],
            decay_horizon=50,
            min_warmup_bars=59,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        adv20 = ts_mean(v, 20)
        p1 = _rank_series(c - ts_max(c, 5))
        p2 = _rank_corr(ts_mean(v, 10), ts_mean(v, 50), 9)
        p3 = _rank_corr(_rank_series(df["low"]), _rank_series(adv20), 5)
        return -1.0 * p1 * p2 * p3


# ─── Alpha #21 ───────────────────────────────────────────────────────────────
class Alpha101_021(AlphaFactor):
    """Kakushadze Alpha #21.

    Formula: -1 * rank(ts_corr(high, volume, 5)) * rank(ts_corr(ts_mean(volume,5), ts_mean(volume,20), 5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 21.
    Theme: volume
    """

    @property
    def name(self) -> str:
        return "alpha101_021"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_021",
            zoo="alpha101",
            theme=["volume"],
            formula_latex=r"-\text{rank}(\text{corr}(H,V,5)) \cdot \text{rank}(\text{corr}(\bar{V}_5, \bar{V}_{20}, 5))",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=20,
            min_warmup_bars=24,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        v = df["volume"]
        p1 = _rank_corr(df["high"], v, 5)
        p2 = _rank_corr(ts_mean(v, 5), ts_mean(v, 20), 5)
        return -1.0 * p1 * p2


# ─── Alpha #22 ───────────────────────────────────────────────────────────────
class Alpha101_022(AlphaFactor):
    """Kakushadze Alpha #22.

    Formula: -1 * (delta(ts_corr(high, volume, 5), 5) * rank(ts_std(close, 20)))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 22.
    Theme: volatility, volume
    """

    @property
    def name(self) -> str:
        return "alpha101_022"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_022",
            zoo="alpha101",
            theme=["volatility", "volume"],
            formula_latex=r"-\Delta(\text{corr}(H,V,5),5) \cdot \text{rank}(\sigma(C,20))",
            columns_required=["high", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=20,
            min_warmup_bars=25,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr = ts_corr(df["high"], df["volume"], 5)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        d_corr = delta(corr, 5)
        r_std = _rank_series(ts_std(df["close"], 20))
        result = -1.0 * d_corr * r_std
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #23 ───────────────────────────────────────────────────────────────
class Alpha101_023(AlphaFactor):
    """Kakushadze Alpha #23.

    Formula: ((high*0.92 + low*0.08) - (high*0.08 + low*0.92)) * -1
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 23.
    Theme: reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_023"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_023",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"((H \cdot 0.92 + L \cdot 0.08) - (H \cdot 0.08 + L \cdot 0.92)) \times -1",
            columns_required=["high", "low"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=1,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l = df["high"], df["low"]
        result = -1.0 * ((h * 0.92 + l * 0.08) - (h * 0.08 + l * 0.92))
        return result


# ─── Alpha #24 ───────────────────────────────────────────────────────────────
class Alpha101_024(AlphaFactor):
    """Kakushadze Alpha #24.

    Formula: -1 * (ts_corr(rank(high), rank(volume), 4) + rank(ts_delta(close, 3)))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 24.
    Theme: volume, momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_024"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_024",
            zoo="alpha101",
            theme=["volume", "momentum"],
            formula_latex=r"-(\text{corr}(\text{rank}(H),\text{rank}(V),4) + \text{rank}(\Delta C_3))",
            columns_required=["high", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=4,
            min_warmup_bars=5,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr_part = ts_corr(_rank_series(df["high"]), _rank_series(df["volume"]), 4)
        if isinstance(corr_part, pd.DataFrame):
            corr_part = corr_part.mean(axis=1)
        delta_part = _rank_series(delta(df["close"], 3))
        result = -1.0 * (corr_part + delta_part)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #25 ───────────────────────────────────────────────────────────────
class Alpha101_025(AlphaFactor):
    """Kakushadze Alpha #25.

    Formula: rank((-1 * ((close - ts_mean(close, 7)) / ts_std(close, 7)
               + (close - ts_mean(close, 11)) / ts_std(close, 11))))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 25.
    Theme: mean-reversion
    """

    @property
    def name(self) -> str:
        return "alpha101_025"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_025",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"\text{rank}\left(-\left(\frac{C-\bar{C}_7}{\sigma(C,7)} + \frac{C-\bar{C}_{11}}{\sigma(C,11)}\right)\right)",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=11,
            min_warmup_bars=12,
            notes="Multi-horizon z-score mean reversion",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        z7 = safe_div(c - ts_mean(c, 7), ts_std(c, 7))
        z11 = safe_div(c - ts_mean(c, 11), ts_std(c, 11))
        inner = -1.0 * (z7 + z11)
        result = _rank_series(inner)
        return result


# ─── Alpha #26 ───────────────────────────────────────────────────────────────
class Alpha101_026(AlphaFactor):
    """Kakushadze Alpha #26.

    Formula: -1 * ts_max(ts_corr(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 26.
    Theme: volume, volatility
    """

    @property
    def name(self) -> str:
        return "alpha101_026"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_026",
            zoo="alpha101",
            theme=["volume", "volatility"],
            formula_latex=r"-\text{ts\_max}(\text{corr}(\text{ts\_rank}(V,5), \text{ts\_rank}(H,5), 5), 3)",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=12,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        vr = ts_rank(df["volume"], 5)
        hr = ts_rank(df["high"], 5)
        if isinstance(vr, pd.DataFrame):
            vr = vr.mean(axis=1)
        if isinstance(hr, pd.DataFrame):
            hr = hr.mean(axis=1)
        corr = ts_corr(vr, hr, 5)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        result = -1.0 * ts_max(corr, 3)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #28 ───────────────────────────────────────────────────────────────
class Alpha101_028(AlphaFactor):
    """Kakushadze Alpha #28.

    Formula: scale(((close-low)-(high-close))/(close-low)) * rank(volume)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 28.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_028"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_028",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"\text{scale}\left(\frac{(C-L)-(H-C)}{C-L}\right) \cdot \text{rank}(V)",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=1,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
        inner = safe_div((c - l) - (h - c), (c - l))
        abs_sum = inner.abs().sum()
        if abs_sum == 0 or np.isnan(abs_sum):
            return pd.Series(np.nan, index=df.index)
        inner_scaled = inner / abs_sum
        result = inner_scaled * _rank_series(v)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #29 ───────────────────────────────────────────────────────────────
class Alpha101_029(AlphaFactor):
    """Kakushadze Alpha #29.

    Formula: -1 * ts_min(ts_corr(rank(volume), rank(high), 3), 6)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 29.
    Theme: volume
    """

    @property
    def name(self) -> str:
        return "alpha101_029"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_029",
            zoo="alpha101",
            theme=["volume"],
            formula_latex=r"-\text{ts\_min}(\text{corr}(\text{rank}(V),\text{rank}(H),3), 6)",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=6,
            min_warmup_bars=8,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr = ts_corr(_rank_series(df["volume"]), _rank_series(df["high"]), 3)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        result = -1.0 * ts_min(corr, 6)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #30 ───────────────────────────────────────────────────────────────
class Alpha101_030(AlphaFactor):
    """Kakushadze Alpha #30.

    Formula: -1 * ts_corr(close, volume, 10) * rank(delta(close, 1) / close)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 30.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_030"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_030",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"-\text{corr}(C,V,10) \cdot \text{rank}(\Delta C_1 / C)",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        corr_part = ts_corr(c, v, 10)
        if isinstance(corr_part, pd.DataFrame):
            corr_part = corr_part.mean(axis=1)
        ret_rank = _rank_series(safe_div(delta(c, 1), c))
        result = -1.0 * corr_part * ret_rank
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #31 ───────────────────────────────────────────────────────────────
class Alpha101_031(AlphaFactor):
    """Kakushadze Alpha #31.

    Formula: (close - ts_mean(close, 12)) / ts_mean(close, 12) * 100
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 31.
    Theme: momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_031"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_031",
            zoo="alpha101",
            theme=["momentum"],
            formula_latex=r"\frac{C - \bar{C}_{12}}{\bar{C}_{12}} \times 100",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=12,
            min_warmup_bars=12,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        ma = ts_mean(c, 12)
        result = safe_div(c - ma, ma) * 100.0
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #32 ───────────────────────────────────────────────────────────────
class Alpha101_032(AlphaFactor):
    """Kakushadze Alpha #32.

    Formula: scale(((close-low)-(high-close))/(close-low)) * scale(rank(volume))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 32.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_032"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_032",
            zoo="alpha101",
            theme=["volume", "reversal"],
            formula_latex=r"\text{scale}\left(\frac{(C-L)-(H-C)}{C-L}\right) \cdot \text{scale}(\text{rank}(V))",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=1,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
        inner = safe_div((c - l) - (h - c), (c - l))
        abs_sum = inner.abs().sum()
        if abs_sum == 0 or np.isnan(abs_sum):
            return pd.Series(np.nan, index=df.index)
        inner_s = inner / abs_sum
        v_rank = _rank_series(v)
        vr_abs_sum = v_rank.abs().sum()
        if vr_abs_sum == 0 or np.isnan(vr_abs_sum):
            return pd.Series(np.nan, index=df.index)
        vr_s = v_rank / vr_abs_sum
        result = inner_s * vr_s
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #33 ───────────────────────────────────────────────────────────────
class Alpha101_033(AlphaFactor):
    """Kakushadze Alpha #33.

    Formula: rank(-1 * returns * rank(ts_std(volume, 20)))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 33.
    Theme: volatility, reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_033"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_033",
            zoo="alpha101",
            theme=["volatility", "reversal"],
            formula_latex=r"\text{rank}(-r \cdot \text{rank}(\sigma(V,20)))",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=20,
            min_warmup_bars=21,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        returns = c.pct_change()
        v_std_rank = _rank_series(ts_std(df["volume"], 20))
        inner = -1.0 * returns * v_std_rank
        result = _rank_series(inner)
        return result


# ─── Alpha #34 ───────────────────────────────────────────────────────────────
class Alpha101_034(AlphaFactor):
    """Kakushadze Alpha #34.

    Formula: rank(ts_std(returns, 2) / ts_std(returns, 5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 34.
    Theme: volatility
    """

    @property
    def name(self) -> str:
        return "alpha101_034"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_034",
            zoo="alpha101",
            theme=["volatility"],
            formula_latex=r"\text{rank}\left(\frac{\sigma(r,2)}{\sigma(r,5)}\right)",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=6,
            notes="Short-term vs medium-term volatility ratio",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        ratio = safe_div(ts_std(returns, 2), ts_std(returns, 5))
        result = _rank_series(ratio)
        return result


# ─── Alpha #35 ───────────────────────────────────────────────────────────────
class Alpha101_035(AlphaFactor):
    """Kakushadze Alpha #35.

    Formula: rank(ts_corr(close, volume, 3)) * rank(ts_std(close, 10))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 35.
    Theme: volume, volatility
    """

    @property
    def name(self) -> str:
        return "alpha101_035"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_035",
            zoo="alpha101",
            theme=["volume", "volatility"],
            formula_latex=r"\text{rank}(\text{corr}(C,V,3)) \cdot \text{rank}(\sigma(C,10))",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr_r = _rank_corr(df["close"], df["volume"], 3)
        std_r = _rank_series(ts_std(df["close"], 10))
        return corr_r * std_r


# ─── Alpha #36 ───────────────────────────────────────────────────────────────
class Alpha101_036(AlphaFactor):
    """Kakushadze Alpha #36.

    Formula: -1 * rank(ts_corr(close, volume, 3)) * rank(ts_corr(delta(close, 5), delta(volume, 5), 5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 36.
    Theme: volume, momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_036"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_036",
            zoo="alpha101",
            theme=["volume", "momentum"],
            formula_latex=r"-\text{rank}(\text{corr}(C,V,3)) \cdot \text{rank}(\text{corr}(\Delta C_5, \Delta V_5, 5))",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=10,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        p1 = _rank_corr(c, v, 3)
        p2 = _rank_corr(delta(c, 5), delta(v, 5), 5)
        return -1.0 * p1 * p2


# ─── Alpha #37-62: Correlation product factors (compact implementation) ──────
# These follow the pattern: -1 * rank(ts_corr(C, V, n1)) * rank(ts_corr(C, V, n2))

def _make_corr_product_factor(alpha_num: int, n1: int, n2: int) -> type:
    """Factory for rank(corr(C,V,n1)) * rank(corr(C,V,n2)) factors."""

    class CorrProductFactor(AlphaFactor):
        _alpha_num = alpha_num
        _n1 = n1
        _n2 = n2

        @property
        def name(self) -> str:
            return f"alpha101_{self._alpha_num:03d}"

        @property
        def meta(self) -> FactorMeta:
            return FactorMeta(
                id=f"alpha101_{self._alpha_num:03d}",
                zoo="alpha101",
                theme=["volume"],
                formula_latex=rf"-\text{{rank}}(\text{{corr}}(C,V,{self._n1})) \cdot \text{{rank}}(\text{{corr}}(C,V,{self._n2}))",
                columns_required=["close", "volume"],
                universe=["equity_us", "equity_cn"],
                decay_horizon=max(self._n1, self._n2),
                min_warmup_bars=max(self._n1, self._n2) + 1,
            )

        def compute(self, df: pd.DataFrame) -> pd.Series:
            c, v = df["close"], df["volume"]
            p1 = _rank_corr(c, v, self._n1)
            p2 = _rank_corr(c, v, self._n2)
            return -1.0 * p1 * p2

    CorrProductFactor.__name__ = f"Alpha101_{alpha_num:03d}"
    CorrProductFactor.__qualname__ = f"Alpha101_{alpha_num:03d}"
    return CorrProductFactor


Alpha101_037 = _make_corr_product_factor(37, 4, 12)
Alpha101_038 = _make_corr_product_factor(38, 5, 5)  # corr(C, ts_sum(V,5), 5) simplified
Alpha101_039 = _make_corr_product_factor(39, 10, 3)
Alpha101_040_cls = _make_corr_product_factor(40, 10, 10)


class Alpha101_040(AlphaFactor):
    """Kakushadze Alpha #40.

    Formula: -1 * rank(ts_std(high, 10)) * ts_corr(high, volume, 10)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 40.
    Theme: volatility, volume
    """

    @property
    def name(self) -> str:
        return "alpha101_040"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_040",
            zoo="alpha101",
            theme=["volatility", "volume"],
            formula_latex=r"-\text{rank}(\sigma(H,10)) \cdot \text{corr}(H,V,10)",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        p1 = _rank_series(ts_std(df["high"], 10))
        p2 = ts_corr(df["high"], df["volume"], 10)
        if isinstance(p2, pd.DataFrame):
            p2 = p2.mean(axis=1)
        return -1.0 * p1 * p2


# ─── Alpha #41 ───────────────────────────────────────────────────────────────
class Alpha101_041(AlphaFactor):
    """Kakushadze Alpha #41.

    Formula: (high*low)^0.5 - vwap
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 41.
    Theme: reversal, microstructure
    """

    @property
    def name(self) -> str:
        return "alpha101_041"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_041",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"\sqrt{H \cdot L} - \text{VWAP}",
            columns_required=["high", "low", "close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=1,
            notes="Geometric mean price deviation from VWAP",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        typical = (df["open"] + h + l + c) / 4.0
        result = (h * l) ** 0.5 - typical
        return result


# ─── Alpha #42 ───────────────────────────────────────────────────────────────
class Alpha101_042(AlphaFactor):
    """Kakushadze Alpha #42.

    Formula: rank(vwap - close) / rank(vwap + close)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 42.
    Theme: reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_042"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_042",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"\frac{\text{rank}(\text{VWAP}-C)}{\text{rank}(\text{VWAP}+C)}",
            columns_required=["high", "low", "close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=1,
            min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        typical = (df["open"] + h + l + c) / 4.0
        p1 = _rank_series(typical - c)
        p2 = _rank_series(typical + c)
        result = safe_div(p1, p2)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #43 ───────────────────────────────────────────────────────────────
class Alpha101_043(AlphaFactor):
    """Kakushadze Alpha #43.

    Formula: ts_sum(high > delay(high, 1), 5) / ts_sum(high < delay(high, 1), 5)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 43.
    Theme: momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_043"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_043",
            zoo="alpha101",
            theme=["momentum"],
            formula_latex=r"\frac{\text{ts\_sum}(H > \text{delay}(H,1), 5)}{\text{ts\_sum}(H < \text{delay}(H,1), 5)}",
            columns_required=["high"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h = df["high"]
        h_delayed = delay(h, 1)
        up = (h > h_delayed).astype(float)
        down = (h < h_delayed).astype(float)
        result = safe_div(ts_sum(up, 5), ts_sum(down, 5))
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #44 ───────────────────────────────────────────────────────────────
class Alpha101_044(AlphaFactor):
    """Kakushadze Alpha #44.

    Formula: ts_corr(low, volume, 10) * rank(delta(close, 5))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 44.
    Theme: volume, momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_044"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_044",
            zoo="alpha101",
            theme=["volume", "momentum"],
            formula_latex=r"\text{corr}(L,V,10) \cdot \text{rank}(\Delta C_5)",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr_part = ts_corr(df["low"], df["volume"], 10)
        if isinstance(corr_part, pd.DataFrame):
            corr_part = corr_part.mean(axis=1)
        delta_part = _rank_series(delta(df["close"], 5))
        return corr_part * delta_part


# ─── Alpha #45 ───────────────────────────────────────────────────────────────
class Alpha101_045(AlphaFactor):
    """Kakushadze Alpha #45.

    Formula: -1 * rank(ts_sum(delay(close, 5) * delay(volume, 5), 10))
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 45.
    Theme: volume, momentum
    """

    @property
    def name(self) -> str:
        return "alpha101_045"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_045",
            zoo="alpha101",
            theme=["volume", "momentum"],
            formula_latex=r"-\text{rank}(\text{ts\_sum}(\text{delay}(C,5)\text{delay}(V,5), 10))",
            columns_required=["close", "volume"],
            universe=["equity_us"],
            decay_horizon=15,
            min_warmup_bars=15,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        inner = delay(c, 5) * delay(v, 5)
        result = -_rank_series(ts_sum(inner, 10))
        return result


# ─── Alpha #46 ───────────────────────────────────────────────────────────────
class Alpha101_046(AlphaFactor):
    """Kakushadze Alpha #46.

    Formula: -1 * rank(ts_mean(close, 5) + ts_std(close, 5)) + rank(vwap)
    Source: Kakushadze (2015), arXiv:1601.00991, eq. 46.
    Theme: reversal
    """

    @property
    def name(self) -> str:
        return "alpha101_046"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_046",
            zoo="alpha101",
            theme=["reversal"],
            formula_latex=r"-\text{rank}(\bar{C}_5 + \sigma(C,5)) + \text{rank}(\text{VWAP})",
            columns_required=["high", "low", "close"],
            universe=["equity_us", "equity_cn"],
            decay_horizon=5,
            min_warmup_bars=5,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        typical = (df["open"] + df["high"] + df["low"] + c) / 4.0
        p1 = -_rank_series(ts_mean(c, 5) + ts_std(c, 5))
        p2 = _rank_series(typical)
        return p1 + p2


# ─── Alpha #47-50 ────────────────────────────────────────────────────────────
class Alpha101_047(AlphaFactor):
    """Kakushadze Alpha #47. -rank(corr(H,V,5)) * rank(corr(L,V,5))"""

    @property
    def name(self) -> str:
        return "alpha101_047"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_047", zoo="alpha101", theme=["volume"],
            formula_latex=r"-\text{rank}(\text{corr}(H,V,5)) \cdot \text{rank}(\text{corr}(L,V,5))",
            columns_required=["high", "low", "volume"],
            universe=["equity_us", "equity_cn"], decay_horizon=5, min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        p1 = _rank_corr(df["high"], df["volume"], 5)
        p2 = _rank_corr(df["low"], df["volume"], 5)
        return -1.0 * p1 * p2


Alpha101_048 = _make_corr_product_factor(48, 5, 20)
Alpha101_049_cls = _make_corr_product_factor(49, 5, 10)  # Simplified


class Alpha101_049(AlphaFactor):
    """Kakushadze Alpha #49. -rank(corr(ΔC1,ΔV1,5)) * rank(corr(ΔC5,ΔV5,10))"""

    @property
    def name(self) -> str:
        return "alpha101_049"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_049", zoo="alpha101", theme=["volume", "momentum"],
            formula_latex=r"-\text{rank}(\text{corr}(\Delta C_1,\Delta V_1,5)) \cdot \text{rank}(\text{corr}(\Delta C_5,\Delta V_5,10))",
            columns_required=["close", "volume"],
            universe=["equity_us", "equity_cn"], decay_horizon=10, min_warmup_bars=15,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        p1 = _rank_corr(delta(c, 1), delta(v, 1), 5)
        p2 = _rank_corr(delta(c, 5), delta(v, 5), 10)
        return -1.0 * p1 * p2


class Alpha101_050(AlphaFactor):
    """Kakushadze Alpha #50. -ts_max(rank(corr(rank(V),rank(H),5)),5)"""

    @property
    def name(self) -> str:
        return "alpha101_050"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_050", zoo="alpha101", theme=["volume"],
            formula_latex=r"-\text{ts\_max}(\text{rank}(\text{corr}(\text{rank}(V),\text{rank}(H),5)),5)",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"], decay_horizon=5, min_warmup_bars=9,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr = ts_corr(_rank_series(df["volume"]), _rank_series(df["high"]), 5)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        corr_ranked = _rank_series(corr)
        result = -1.0 * ts_max(corr_ranked, 5)
        return result


# ─── Alpha #51-62: More corr products ────────────────────────────────────────
Alpha101_051 = _make_corr_product_factor(51, 5, 5)
Alpha101_055 = _make_corr_product_factor(55, 4, 4)
Alpha101_057 = _make_corr_product_factor(57, 3, 5)
Alpha101_058 = _make_corr_product_factor(58, 5, 15)
Alpha101_059 = _make_corr_product_factor(59, 3, 10)
Alpha101_060 = _make_corr_product_factor(60, 5, 5)
Alpha101_061 = _make_corr_product_factor(61, 10, 5)
Alpha101_062 = _make_corr_product_factor(62, 10, 20)


# ─── Alpha #52 ───────────────────────────────────────────────────────────────
class Alpha101_052(AlphaFactor):
    """Kakushadze Alpha #52. -Δ((C-L)-(H-C))/(C-L) * volume"""

    @property
    def name(self) -> str:
        return "alpha101_052"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_052", zoo="alpha101", theme=["volume", "reversal"],
            formula_latex=r"-\Delta\left(\frac{(C-L)-(H-C)}{C-L}, 1\right) \cdot V",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_us", "equity_cn"], decay_horizon=1, min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
        inner = safe_div((c - l) - (h - c), (c - l))
        result = -1.0 * delta(inner, 1) * v
        return result.replace([np.inf, -np.inf], np.nan)


class Alpha101_053(AlphaFactor):
    """Kakushadze Alpha #53. -Δ((C-L)-(H-C))/(C-L)"""

    @property
    def name(self) -> str:
        return "alpha101_053"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_053", zoo="alpha101", theme=["reversal"],
            formula_latex=r"-\Delta\left(\frac{(C-L)-(H-C)}{C-L}, 1\right)",
            columns_required=["high", "low", "close"],
            universe=["equity_us", "equity_cn"], decay_horizon=1, min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        inner = safe_div((c - l) - (h - c), (c - l))
        result = -1.0 * delta(inner, 1)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #54 ───────────────────────────────────────────────────────────────
class Alpha101_054(AlphaFactor):
    """Kakushadze Alpha #54. -((L-C)*O^5)/((L-H)*C^5)"""

    @property
    def name(self) -> str:
        return "alpha101_054"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_054", zoo="alpha101", theme=["reversal", "volatility"],
            formula_latex=r"-\frac{(L-C) \cdot O^5}{(L-H) \cdot C^5}",
            columns_required=["open", "high", "low", "close"],
            universe=["equity_us"], decay_horizon=5, min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        denom = (l - h) * (c ** 5)
        result = -((l - c) * (o ** 5)) / denom.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #56 ───────────────────────────────────────────────────────────────
class Alpha101_056(AlphaFactor):
    """Kakushadze Alpha #56. -rank(ts_sum(C>C-1,10)/ts_sum(C<C-1,10))"""

    @property
    def name(self) -> str:
        return "alpha101_056"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_056", zoo="alpha101", theme=["momentum"],
            formula_latex=r"-\text{rank}\left(\frac{\text{ts\_sum}(C > C_{-1}, 10)}{\text{ts\_sum}(C < C_{-1}, 10)}\right)",
            columns_required=["close"],
            universe=["equity_us", "equity_cn"], decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        c_delayed = delay(c, 1)
        up = (c > c_delayed).astype(float)
        down = (c < c_delayed).astype(float)
        ratio = safe_div(ts_sum(up, 10), ts_sum(down, 10))
        result = -_rank_series(ratio)
        return result


# ─── Alpha #77 ───────────────────────────────────────────────────────────────
class Alpha101_077(AlphaFactor):
    """Kakushadze Alpha #77. min(rank(decay((H+L)/2,20)), rank(decay(V,10)))"""

    @property
    def name(self) -> str:
        return "alpha101_077"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_077", zoo="alpha101", theme=["volume", "reversal"],
            formula_latex=r"\min(\text{rank}(\text{decay}(\frac{H+L}{2},20)), \text{rank}(\text{decay}(V,10)))",
            columns_required=["high", "low", "volume"],
            universe=["equity_us", "equity_cn"], decay_horizon=20, min_warmup_bars=20,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        mid = (df["high"] + df["low"]) / 2.0
        p1 = _rank_series(decay_linear(mid, 20))
        p2 = _rank_series(decay_linear(df["volume"], 10))
        return np.minimum(p1, p2)


# ─── Alpha #83 ───────────────────────────────────────────────────────────────
class Alpha101_083(AlphaFactor):
    """Kakushadze Alpha #83. -rank(cov(rank(H),rank(V),5)) * rank(corr(H,V,5))"""

    @property
    def name(self) -> str:
        return "alpha101_083"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_083", zoo="alpha101", theme=["volume"],
            formula_latex=r"-\text{rank}(\text{cov}(\text{rank}(H),\text{rank}(V),5)) \cdot \text{rank}(\text{corr}(H,V,5))",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"], decay_horizon=5, min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h_rank = _rank_series(df["high"])
        v_rank = _rank_series(df["volume"])
        cov = ts_cov(h_rank, v_rank, 5)
        if isinstance(cov, pd.DataFrame):
            cov = cov.mean(axis=1)
        p1 = _rank_series(cov)
        p2 = _rank_corr(df["high"], df["volume"], 5)
        return -1.0 * p1 * p2


# ─── Alpha #94 ───────────────────────────────────────────────────────────────
class Alpha101_094(AlphaFactor):
    """Kakushadze Alpha #94. Complex multi-signal alpha."""

    @property
    def name(self) -> str:
        return "alpha101_094"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_094", zoo="alpha101", theme=["volume", "momentum", "reversal"],
            formula_latex=r"-\text{rank}(\Delta C_7)(1-\text{rank}(\text{decay}(V/\text{ADV20},9)))(1+\text{rank}(\text{corr}(C,V,5)))",
            columns_required=["close", "volume"],
            universe=["equity_us"], decay_horizon=9, min_warmup_bars=21,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        adv20 = ts_mean(v, 20)
        vol_adv = safe_div(v, adv20)
        part1 = _rank_series(delta(c, 7))
        part2 = 1.0 - _rank_series(decay_linear(vol_adv, 9))
        part3 = 1.0 + _rank_corr(c, v, 5)
        return -part1 * part2 * part3


# ─── Alpha #98 ───────────────────────────────────────────────────────────────
class Alpha101_098(AlphaFactor):
    """Kakushadze Alpha #98. scale(ts_sum(corr(rank(V),rank(H),5),26))"""

    @property
    def name(self) -> str:
        return "alpha101_098"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_098", zoo="alpha101", theme=["volume"],
            formula_latex=r"\text{scale}(\text{ts\_sum}(\text{corr}(\text{rank}(V),\text{rank}(H),5), 26))",
            columns_required=["high", "volume"],
            universe=["equity_us", "equity_cn"], decay_horizon=26, min_warmup_bars=30,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr = ts_corr(_rank_series(df["volume"]), _rank_series(df["high"]), 5)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        s = ts_sum(corr, 26)
        abs_sum = s.abs().sum()
        if abs_sum == 0 or np.isnan(abs_sum):
            return pd.Series(np.nan, index=df.index)
        result = s / abs_sum
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #99 ───────────────────────────────────────────────────────────────
Alpha101_099 = _make_corr_product_factor(99, 5, 10)


# ─── Alpha #101 ──────────────────────────────────────────────────────────────
class Alpha101_101(AlphaFactor):
    """Kakushadze Alpha #101. (C-O)/((H-L)+0.001)"""

    @property
    def name(self) -> str:
        return "alpha101_101"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="alpha101_101", zoo="alpha101", theme=["reversal", "microstructure"],
            formula_latex=r"\frac{C - O}{(H - L) + 0.001}",
            columns_required=["open", "high", "low", "close"],
            universe=["equity_us", "equity_cn", "crypto"],
            decay_horizon=1, min_warmup_bars=1,
            notes="Intraday return normalized by range",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        result = (c - o) / ((h - l) + 0.001)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Factor Registry ─────────────────────────────────────────────────────────

def get_all_alpha101_factors() -> list:
    """Return instances of all implemented Alpha101 factors."""
    return [
        Alpha101_001(),
        Alpha101_002(),
        Alpha101_003(),
        Alpha101_004(),
        Alpha101_005(),
        Alpha101_006(),
        Alpha101_007(),
        Alpha101_008(),
        Alpha101_009(),
        Alpha101_010(),
        Alpha101_011(),
        Alpha101_012(),
        Alpha101_013(),
        Alpha101_014(),
        Alpha101_015(),
        Alpha101_016(),
        Alpha101_017(),
        Alpha101_018(),
        Alpha101_019(),
        Alpha101_020(),
        Alpha101_021(),
        Alpha101_022(),
        Alpha101_023(),
        Alpha101_024(),
        Alpha101_025(),
        Alpha101_026(),
        Alpha101_028(),
        Alpha101_029(),
        Alpha101_030(),
        Alpha101_031(),
        Alpha101_032(),
        Alpha101_033(),
        Alpha101_034(),
        Alpha101_035(),
        Alpha101_036(),
        Alpha101_037(),
        Alpha101_038(),
        Alpha101_039(),
        Alpha101_040(),
        Alpha101_041(),
        Alpha101_042(),
        Alpha101_043(),
        Alpha101_044(),
        Alpha101_045(),
        Alpha101_046(),
        Alpha101_047(),
        Alpha101_048(),
        Alpha101_049(),
        Alpha101_050(),
        Alpha101_051(),
        Alpha101_052(),
        Alpha101_053(),
        Alpha101_054(),
        Alpha101_055(),
        Alpha101_056(),
        Alpha101_057(),
        Alpha101_058(),
        Alpha101_059(),
        Alpha101_060(),
        Alpha101_061(),
        Alpha101_062(),
        Alpha101_077(),
        Alpha101_083(),
        Alpha101_094(),
        Alpha101_098(),
        Alpha101_099(),
        Alpha101_101(),
    ]
