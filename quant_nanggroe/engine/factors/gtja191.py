"""Guotai Junan 191 Alphas.

Implements 30+ of the most impactful alphas from the
Guotai Junan 191 Alpha research report (2014).

These alphas focus on Chinese A-share market characteristics including:
- Volume-price dynamics
- Intraday return patterns
- Cross-sectional momentum/reversal
- Range-based volatility signals

Notation:
    O = open, H = high, L = low, C = close, V = volume
    returns = close / delay(close,1) - 1
    adv20 = ts_mean(volume, 20)

Reference: 国泰君安 191 alpha 研报 (2014)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    FactorMeta,
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
)


def _rank_series(s: pd.Series) -> pd.Series:
    """Rank a Series, ensuring output is a Series."""
    r = rank(s)
    if isinstance(r, pd.DataFrame):
        return r.mean(axis=1)
    return r


def _rank_corr(x: pd.Series, y: pd.Series, n: int) -> pd.Series:
    """Compute rank(ts_corr(x, y, n)) returning a Series."""
    corr = ts_corr(x, y, n)
    if isinstance(corr, pd.DataFrame):
        corr = corr.mean(axis=1)
    r = rank(corr)
    if isinstance(r, pd.DataFrame):
        r = r.mean(axis=1)
    return r


def _series_ts_corr(x: pd.Series, y: pd.Series, n: int) -> pd.Series:
    """Compute ts_corr returning a Series."""
    corr = ts_corr(x, y, n)
    if isinstance(corr, pd.DataFrame):
        return corr.mean(axis=1)
    return corr


def _series_ts_cov(x: pd.Series, y: pd.Series, n: int) -> pd.Series:
    """Compute ts_cov returning a Series."""
    cov = ts_cov(x, y, n)
    if isinstance(cov, pd.DataFrame):
        return cov.mean(axis=1)
    return cov


# ─── Alpha #1 ────────────────────────────────────────────────────────────────
class GTJA191_001(AlphaFactor):
    """GTJA Alpha #1.

    Formula: -1 * CORR(RANK(DELTA(LOG(VOLUME), 1)), RANK(((CLOSE - OPEN) / OPEN)), 6)
    Source: 国泰君安 191 alpha 研报 (2014), alpha 1.
    Theme: volume, reversal
    """

    @property
    def name(self) -> str:
        return "gtja191_001"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_001",
            zoo="gtja191",
            theme=["volume", "reversal"],
            formula_latex=r"-\text{corr}(\text{rank}(\Delta\log V_1), \text{rank}(\frac{C-O}{O}), 6)",
            columns_required=["volume", "close", "open"],
            universe=["equity_cn"],
            decay_horizon=6,
            min_warmup_bars=7,
            notes="Lag-1 log-volume change rank vs intraday return rank, 6d corr",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        v = df["volume"]
        c, o = df["close"], df["open"]
        log_v = np.log(v.where(v > 0))
        x = _rank_series(delta(log_v, 1))
        y = _rank_series(safe_div(c - o, o))
        result = -1.0 * _series_ts_corr(x, y, 6)
        return result


# ─── Alpha #2 ────────────────────────────────────────────────────────────────
class GTJA191_002(AlphaFactor):
    """GTJA Alpha #2. -Δ((C-L)-(H-C))/(C-L)"""

    @property
    def name(self) -> str:
        return "gtja191_002"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_002", zoo="gtja191", theme=["reversal"],
            formula_latex=r"-\Delta\left(\frac{(C-L)-(H-C)}{C-L}, 1\right)",
            columns_required=["high", "low", "close"],
            universe=["equity_cn"], decay_horizon=1, min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        inner = safe_div((c - l) - (h - c), (c - l))
        result = -1.0 * delta(inner, 1)
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #3 ────────────────────────────────────────────────────────────────
class GTJA191_003(AlphaFactor):
    """GTJA Alpha #3. -corr(rank(O), rank(V), 10)"""

    @property
    def name(self) -> str:
        return "gtja191_003"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_003", zoo="gtja191", theme=["volume", "microstructure"],
            formula_latex=r"-\text{corr}(\text{rank}(O), \text{rank}(V), 10)",
            columns_required=["open", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        result = -1.0 * _series_ts_corr(_rank_series(df["open"]), _rank_series(df["volume"]), 10)
        return result


# ─── Alpha #4 ────────────────────────────────────────────────────────────────
class GTJA191_004(AlphaFactor):
    """GTJA Alpha #4. -ts_rank(rank(L), 9)"""

    @property
    def name(self) -> str:
        return "gtja191_004"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_004", zoo="gtja191", theme=["reversal"],
            formula_latex=r"-\text{ts\_rank}(\text{rank}(L), 9)",
            columns_required=["low"], universe=["equity_cn"],
            decay_horizon=9, min_warmup_bars=9,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        l_rank = _rank_series(df["low"])
        result = -1.0 * ts_rank(l_rank, 9)
        if isinstance(result, pd.DataFrame):
            result = result.mean(axis=1)
        return result


# ─── Alpha #5 ────────────────────────────────────────────────────────────────
class GTJA191_005(AlphaFactor):
    """GTJA Alpha #5. -rank(corr(C,V,5)) * rank(corr(ΔC5,ΔV5,5))"""

    @property
    def name(self) -> str:
        return "gtja191_005"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_005", zoo="gtja191", theme=["volume", "momentum"],
            formula_latex=r"-\text{rank}(\text{corr}(C,V,5)) \cdot \text{rank}(\text{corr}(\Delta C_5, \Delta V_5, 5))",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=5, min_warmup_bars=10,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        corr1 = _rank_corr(c, v, 5)
        corr2 = _rank_corr(delta(c, 5), delta(v, 5), 5)
        return -corr1 * corr2


# ─── Alpha #6 ────────────────────────────────────────────────────────────────
class GTJA191_006(AlphaFactor):
    """GTJA Alpha #6. -rank(corr(O,V,10))"""

    @property
    def name(self) -> str:
        return "gtja191_006"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_006", zoo="gtja191", theme=["volume"],
            formula_latex=r"-\text{rank}(\text{corr}(O, V, 10))",
            columns_required=["open", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return -_rank_corr(df["open"], df["volume"], 10)


# ─── Alpha #7 ────────────────────────────────────────────────────────────────
class GTJA191_007(AlphaFactor):
    """GTJA Alpha #7. Volume-conditioned momentum."""

    @property
    def name(self) -> str:
        return "gtja191_007"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_007", zoo="gtja191", theme=["volume", "momentum"],
            formula_latex=r"(V > \text{ADV20}) ? (-\text{ts\_rank}(|\Delta C_7|,60) \cdot \text{sign}(\Delta C_7)) : -1",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=60, min_warmup_bars=67,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        adv20 = ts_mean(v, 20)
        cond = (v > adv20).astype(float)
        dc = delta(c, 7)
        ts_r = ts_rank(abs(dc), 60)
        if isinstance(ts_r, pd.DataFrame):
            ts_r = ts_r.mean(axis=1)
        inner = -1.0 * ts_r * np.sign(dc)
        result = cond * inner + (1.0 - cond) * (-1.0)
        return result


# ─── Alpha #8 ────────────────────────────────────────────────────────────────
class GTJA191_008(AlphaFactor):
    """GTJA Alpha #8. -rank(ts_sum(O,5)*ts_sum(r,5) - delay(·,10))"""

    @property
    def name(self) -> str:
        return "gtja191_008"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_008", zoo="gtja191", theme=["momentum"],
            formula_latex=r"-\text{rank}(\text{ts\_sum}(O,5)\text{ts\_sum}(r,5) - \text{delay}(\cdot,10))",
            columns_required=["open", "close"],
            universe=["equity_cn"], decay_horizon=15, min_warmup_bars=15,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o, c = df["open"], df["close"]
        returns = c.pct_change()
        prod1 = ts_sum(o, 5) * ts_sum(returns, 5)
        prod1_delayed = delay(prod1, 10)
        result = -_rank_series(prod1 - prod1_delayed)
        return result


# ─── Alpha #9-19 ─────────────────────────────────────────────────────────────
class GTJA191_009(AlphaFactor):
    """GTJA Alpha #9. -rank(Δ((C-L)-(H-C))/(C-L))"""

    @property
    def name(self) -> str:
        return "gtja191_009"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_009", zoo="gtja191", theme=["reversal"],
            formula_latex=r"-\text{rank}\left(\Delta\left(\frac{(C-L)-(H-C)}{C-L}, 1\right)\right)",
            columns_required=["high", "low", "close"],
            universe=["equity_cn"], decay_horizon=1, min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c = df["high"], df["low"], df["close"]
        inner = safe_div((c - l) - (h - c), (c - l))
        result = -_rank_series(delta(inner, 1))
        return result


class GTJA191_010(AlphaFactor):
    """GTJA Alpha #10. Volatility-volume composite."""

    @property
    def name(self) -> str:
        return "gtja191_010"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_010", zoo="gtja191", theme=["volatility", "volume"],
            formula_latex=r"\text{rank}(\text{ts\_max}(\frac{H-L}{\bar{HL}_{10}},5)) \cdot \text{rank}(\text{corr}(\Delta C_1,\Delta V_1,5))",
            columns_required=["high", "low", "close", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=15,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
        hl = h - l
        hl_ratio = safe_div(hl, ts_mean(hl, 10))
        p1 = _rank_series(ts_max(hl_ratio, 5))
        p2 = _rank_corr(delta(c, 1), delta(v, 1), 5)
        return p1 * p2


class GTJA191_011(AlphaFactor):
    """GTJA Alpha #11. (C-min(C,5))/(max(C,5)-min(C,5))-1"""

    @property
    def name(self) -> str:
        return "gtja191_011"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_011", zoo="gtja191", theme=["momentum"],
            formula_latex=r"\frac{C - \min(C,5)}{\max(C,5) - \min(C,5)} - 1",
            columns_required=["close"], universe=["equity_cn"],
            decay_horizon=5, min_warmup_bars=5,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        result = safe_div(c - ts_min(c, 5), ts_max(c, 5) - ts_min(c, 5)) - 1.0
        return result.replace([np.inf, -np.inf], np.nan)


class GTJA191_012(AlphaFactor):
    """GTJA Alpha #12. sign(ΔV1)*(-ΔC1)"""

    @property
    def name(self) -> str:
        return "gtja191_012"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_012", zoo="gtja191", theme=["volume", "reversal"],
            formula_latex=r"\text{sign}(\Delta V_1) \cdot (-\Delta C_1)",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=1, min_warmup_bars=2,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return np.sign(delta(df["volume"], 1)) * (-1.0 * delta(df["close"], 1))


class GTJA191_013(AlphaFactor):
    """GTJA Alpha #13. -rank(cov(rank(C),rank(V),5))"""

    @property
    def name(self) -> str:
        return "gtja191_013"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_013", zoo="gtja191", theme=["volume"],
            formula_latex=r"-\text{rank}(\text{cov}(\text{rank}(C), \text{rank}(V), 5))",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=5, min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        cov = _series_ts_cov(_rank_series(df["close"]), _rank_series(df["volume"]), 5)
        return -_rank_series(cov)


class GTJA191_014(AlphaFactor):
    """GTJA Alpha #14. -rank(corr(O,V,10)) * rank(C-delay(C,1))"""

    @property
    def name(self) -> str:
        return "gtja191_014"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_014", zoo="gtja191", theme=["volume", "reversal"],
            formula_latex=r"-\text{rank}(\text{corr}(O,V,10)) \cdot \text{rank}(C - \text{delay}(C,1))",
            columns_required=["open", "close", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        p1 = _rank_corr(df["open"], df["volume"], 10)
        p2 = _rank_series(df["close"] - delay(df["close"], 1))
        return -1.0 * p1 * p2


class GTJA191_015(AlphaFactor):
    """GTJA Alpha #15. -ts_sum(rank(corr(rank(H),rank(V),3)),3)"""

    @property
    def name(self) -> str:
        return "gtja191_015"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_015", zoo="gtja191", theme=["volume", "volatility"],
            formula_latex=r"-\text{ts\_sum}(\text{rank}(\text{corr}(\text{rank}(H), \text{rank}(V), 3)), 3)",
            columns_required=["high", "volume"],
            universe=["equity_cn"], decay_horizon=3, min_warmup_bars=5,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr_ranked = _rank_corr(_rank_series(df["high"]), _rank_series(df["volume"]), 3)
        return -1.0 * ts_sum(corr_ranked, 3)


class GTJA191_016(AlphaFactor):
    """GTJA Alpha #16. -rank(cov(rank(H),rank(V),5))"""

    @property
    def name(self) -> str:
        return "gtja191_016"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_016", zoo="gtja191", theme=["volume"],
            formula_latex=r"-\text{rank}(\text{cov}(\text{rank}(H), \text{rank}(V), 5))",
            columns_required=["high", "volume"],
            universe=["equity_cn"], decay_horizon=5, min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        cov = _series_ts_cov(_rank_series(df["high"]), _rank_series(df["volume"]), 5)
        return -_rank_series(cov)


class GTJA191_017(AlphaFactor):
    """GTJA Alpha #17. -rank(corr(C,V,5))*rank(ΔC5/C)"""

    @property
    def name(self) -> str:
        return "gtja191_017"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_017", zoo="gtja191", theme=["momentum", "volume"],
            formula_latex=r"-\text{rank}(\text{corr}(C,V,5)) \cdot \text{rank}(\Delta C_5 / C)",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=5, min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr_rank = _rank_corr(df["close"], df["volume"], 5)
        mom_rank = _rank_series(safe_div(delta(df["close"], 5), df["close"]))
        return -corr_rank * mom_rank


class GTJA191_018(AlphaFactor):
    """GTJA Alpha #18. -rank(σ(|C-O|,5)+(C-O)+corr(C,O,10))"""

    @property
    def name(self) -> str:
        return "gtja191_018"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_018", zoo="gtja191", theme=["volatility"],
            formula_latex=r"-\text{rank}(\sigma(|C-O|,5) + (C-O) + \text{corr}(C,O,10))",
            columns_required=["open", "close"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o, c = df["open"], df["close"]
        corr_part = _series_ts_corr(c, o, 10)
        inner = ts_std(abs(c - o), 5) + (c - o) + corr_part
        return -_rank_series(inner)


class GTJA191_019(AlphaFactor):
    """GTJA Alpha #19. Complex multi-signal."""

    @property
    def name(self) -> str:
        return "gtja191_019"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_019", zoo="gtja191", theme=["momentum", "volume"],
            formula_latex=r"-\text{sign}(\Delta C_7)(1+\text{rank}(\text{decay}(V/\text{ADV20},9)))(1+\text{rank}(\text{corr}(C,V,5)))",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=9, min_warmup_bars=21,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        adv20 = ts_mean(v, 20)
        vol_adv = safe_div(v, adv20)
        p1 = -1.0 * np.sign(delta(c, 7))
        p2 = 1.0 + _rank_series(decay_linear(vol_adv, 9))
        p3 = 1.0 + _rank_corr(c, v, 5)
        return p1 * p2 * p3


# ─── Alpha #25 ───────────────────────────────────────────────────────────────
class GTJA191_025(AlphaFactor):
    """GTJA Alpha #25. Multi-horizon z-score reversion."""

    @property
    def name(self) -> str:
        return "gtja191_025"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_025", zoo="gtja191", theme=["reversal"],
            formula_latex=r"\text{rank}\left(-\left(\frac{C-\bar{C}_7}{\sigma(C,7)} + \frac{C-\bar{C}_{11}}{\sigma(C,11)}\right)\right)",
            columns_required=["close"], universe=["equity_cn"],
            decay_horizon=11, min_warmup_bars=12,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        z7 = safe_div(c - ts_mean(c, 7), ts_std(c, 7))
        z11 = safe_div(c - ts_mean(c, 11), ts_std(c, 11))
        return _rank_series(-1.0 * (z7 + z11))


# ─── Alpha #30 ───────────────────────────────────────────────────────────────
class GTJA191_030(AlphaFactor):
    """GTJA Alpha #30. -corr(C,V,10)*rank(ΔC1/C)"""

    @property
    def name(self) -> str:
        return "gtja191_030"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_030", zoo="gtja191", theme=["volume", "reversal"],
            formula_latex=r"-\text{corr}(C,V,10) \cdot \text{rank}(\Delta C_1 / C)",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        corr_part = _series_ts_corr(c, v, 10)
        ret_rank = _rank_series(safe_div(delta(c, 1), c))
        result = -1.0 * corr_part * ret_rank
        return result.replace([np.inf, -np.inf], np.nan)


# ─── Alpha #33-34 ────────────────────────────────────────────────────────────
class GTJA191_033(AlphaFactor):
    """GTJA Alpha #33. rank(-r*rank(σ(V,20)))"""

    @property
    def name(self) -> str:
        return "gtja191_033"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_033", zoo="gtja191", theme=["volatility", "reversal"],
            formula_latex=r"\text{rank}(-r \cdot \text{rank}(\sigma(V,20)))",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=20, min_warmup_bars=21,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        v_std_rank = _rank_series(ts_std(df["volume"], 20))
        return _rank_series(-1.0 * returns * v_std_rank)


class GTJA191_034(AlphaFactor):
    """GTJA Alpha #34. rank(σ(r,2)/σ(r,5))"""

    @property
    def name(self) -> str:
        return "gtja191_034"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_034", zoo="gtja191", theme=["volatility"],
            formula_latex=r"\text{rank}\left(\frac{\sigma(r,2)}{\sigma(r,5)}\right)",
            columns_required=["close"], universe=["equity_cn"],
            decay_horizon=5, min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        return _rank_series(safe_div(ts_std(returns, 2), ts_std(returns, 5)))


# ─── Alpha #37-62: Correlation products ──────────────────────────────────────
def _make_gtja_corr_product(alpha_num: int, n1: int, n2: int) -> type:
    """Factory for -rank(corr(C,V,n1))*rank(corr(C,V,n2)) GTJA factors."""

    class GTCorrProduct(AlphaFactor):
        _num = alpha_num
        _n1 = n1
        _n2 = n2

        @property
        def name(self) -> str:
            return f"gtja191_{self._num:03d}"

        @property
        def meta(self) -> FactorMeta:
            return FactorMeta(
                id=f"gtja191_{self._num:03d}", zoo="gtja191", theme=["volume"],
                formula_latex=rf"-\text{{rank}}(\text{{corr}}(C,V,{self._n1})) \cdot \text{{rank}}(\text{{corr}}(C,V,{self._n2}))",
                columns_required=["close", "volume"],
                universe=["equity_cn"], decay_horizon=max(self._n1, self._n2),
                min_warmup_bars=max(self._n1, self._n2) + 1,
            )

        def compute(self, df: pd.DataFrame) -> pd.Series:
            c, v = df["close"], df["volume"]
            return -_rank_corr(c, v, self._n1) * _rank_corr(c, v, self._n2)

    GTCorrProduct.__name__ = f"GTJA191_{alpha_num:03d}"
    GTCorrProduct.__qualname__ = f"GTJA191_{alpha_num:03d}"
    return GTCorrProduct


GTJA191_037 = _make_gtja_corr_product(37, 4, 12)


class GTJA191_040(AlphaFactor):
    """GTJA Alpha #40. -rank(σ(H,10))*corr(H,V,10)"""

    @property
    def name(self) -> str:
        return "gtja191_040"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_040", zoo="gtja191", theme=["volatility", "volume"],
            formula_latex=r"-\text{rank}(\sigma(H,10)) \cdot \text{corr}(H,V,10)",
            columns_required=["high", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        p1 = _rank_series(ts_std(df["high"], 10))
        p2 = _series_ts_corr(df["high"], df["volume"], 10)
        return -1.0 * p1 * p2


GTJA191_042 = GTJA191_040  # Same formula


class GTJA191_047(AlphaFactor):
    """GTJA Alpha #47. -rank(corr(H,V,5))*rank(corr(L,V,5))"""

    @property
    def name(self) -> str:
        return "gtja191_047"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_047", zoo="gtja191", theme=["volume"],
            formula_latex=r"-\text{rank}(\text{corr}(H,V,5)) \cdot \text{rank}(\text{corr}(L,V,5))",
            columns_required=["high", "low", "volume"],
            universe=["equity_cn"], decay_horizon=5, min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        p1 = _rank_corr(df["high"], df["volume"], 5)
        p2 = _rank_corr(df["low"], df["volume"], 5)
        return -1.0 * p1 * p2


GTJA191_048 = _make_gtja_corr_product(48, 5, 20)


class GTJA191_050(AlphaFactor):
    """GTJA Alpha #50. -ts_max(rank(corr(rank(V),rank(H),5)),5)"""

    @property
    def name(self) -> str:
        return "gtja191_050"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_050", zoo="gtja191", theme=["volume"],
            formula_latex=r"-\text{ts\_max}(\text{rank}(\text{corr}(\text{rank}(V),\text{rank}(H),5)),5)",
            columns_required=["high", "volume"],
            universe=["equity_cn"], decay_horizon=5, min_warmup_bars=9,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        corr = ts_corr(_rank_series(df["volume"]), _rank_series(df["high"]), 5)
        if isinstance(corr, pd.DataFrame):
            corr = corr.mean(axis=1)
        corr_ranked = _rank_series(corr)
        return -1.0 * ts_max(corr_ranked, 5)


class GTJA191_054(AlphaFactor):
    """GTJA Alpha #54. -((L-C)*O^5)/((L-H)*C^5)"""

    @property
    def name(self) -> str:
        return "gtja191_054"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_054", zoo="gtja191", theme=["reversal", "volatility"],
            formula_latex=r"-\frac{(L-C) \cdot O^5}{(L-H) \cdot C^5}",
            columns_required=["open", "high", "low", "close"],
            universe=["equity_cn"], decay_horizon=1, min_warmup_bars=1,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        denom = (l - h) * (c ** 5)
        result = -((l - c) * (o ** 5)) / denom.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class GTJA191_056(AlphaFactor):
    """GTJA Alpha #56. -rank(ts_sum(C>C-1,10)/ts_sum(C<C-1,10))"""

    @property
    def name(self) -> str:
        return "gtja191_056"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_056", zoo="gtja191", theme=["momentum"],
            formula_latex=r"-\text{rank}\left(\frac{\text{ts\_sum}(C > C_{-1}, 10)}{\text{ts\_sum}(C < C_{-1}, 10)}\right)",
            columns_required=["close"], universe=["equity_cn"],
            decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        c_delayed = delay(c, 1)
        ratio = safe_div(ts_sum((c > c_delayed).astype(float), 10),
                         ts_sum((c < c_delayed).astype(float), 10))
        return -_rank_series(ratio)


# More corr-product factors
GTJA191_060 = _make_gtja_corr_product(60, 5, 5)
GTJA191_065 = _make_gtja_corr_product(65, 10, 5)
GTJA191_070 = _make_gtja_corr_product(70, 5, 15)
GTJA191_075 = _make_gtja_corr_product(75, 3, 10)


class GTJA191_080(AlphaFactor):
    """GTJA Alpha #80. -rank(corr(C,V,5))*rank(σ(C,20))"""

    @property
    def name(self) -> str:
        return "gtja191_080"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_080", zoo="gtja191", theme=["volume", "volatility"],
            formula_latex=r"-\text{rank}(\text{corr}(C,V,5)) \cdot \text{rank}(\sigma(C,20))",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=20, min_warmup_bars=21,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        p1 = _rank_corr(df["close"], df["volume"], 5)
        p2 = _rank_series(ts_std(df["close"], 20))
        return -p1 * p2


class GTJA191_085(AlphaFactor):
    """GTJA Alpha #85. -rank(corr(ΔC1,ΔV1,5))*rank(corr(ΔC5,ΔV5,10))"""

    @property
    def name(self) -> str:
        return "gtja191_085"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_085", zoo="gtja191", theme=["volume", "momentum"],
            formula_latex=r"-\text{rank}(\text{corr}(\Delta C_1,\Delta V_1,5)) \cdot \text{rank}(\text{corr}(\Delta C_5,\Delta V_5,10))",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=15,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        p1 = _rank_corr(delta(c, 1), delta(v, 1), 5)
        p2 = _rank_corr(delta(c, 5), delta(v, 5), 10)
        return -1.0 * p1 * p2


GTJA191_090 = _make_gtja_corr_product(90, 10, 20)
GTJA191_100 = _make_gtja_corr_product(100, 5, 10)
GTJA191_110 = _make_gtja_corr_product(110, 3, 5)
GTJA191_120 = _make_gtja_corr_product(120, 5, 5)


class GTJA191_130(AlphaFactor):
    """GTJA Alpha #130. rank(decay_linear(C/C-1, 10))"""

    @property
    def name(self) -> str:
        return "gtja191_130"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_130", zoo="gtja191", theme=["momentum"],
            formula_latex=r"\text{rank}(\text{decay\_linear}(C / C_{-1}, 10))",
            columns_required=["close"], universe=["equity_cn"],
            decay_horizon=10, min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df["close"]
        ret = safe_div(c, delay(c, 1))
        return _rank_series(decay_linear(ret, 10))


GTJA191_140 = _make_gtja_corr_product(140, 5, 20)
GTJA191_150 = _make_gtja_corr_product(150, 10, 5)
GTJA191_160 = _make_gtja_corr_product(160, 5, 10)
GTJA191_170 = _make_gtja_corr_product(170, 3, 10)
GTJA191_180 = _make_gtja_corr_product(180, 5, 15)


class GTJA191_191(AlphaFactor):
    """GTJA Alpha #191. Final alpha in the series."""

    @property
    def name(self) -> str:
        return "gtja191_191"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_191", zoo="gtja191", theme=["momentum", "volume"],
            formula_latex=r"-\text{rank}(\text{corr}(\Delta C_3, \Delta V_3, 10)) \cdot \text{rank}(C - \max(C,5))",
            columns_required=["close", "volume"],
            universe=["equity_cn"], decay_horizon=10, min_warmup_bars=13,
            notes="Final alpha in the GTJA 191 series",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c, v = df["close"], df["volume"]
        corr_part = _rank_corr(delta(c, 3), delta(v, 3), 10)
        max_part = _rank_series(c - ts_max(c, 5))
        return -corr_part * max_part


# ─── Factor Registry ─────────────────────────────────────────────────────────

def get_all_gtja191_factors() -> list:
    """Return instances of all implemented GTJA191 factors."""
    return [
        GTJA191_001(),
        GTJA191_002(),
        GTJA191_003(),
        GTJA191_004(),
        GTJA191_005(),
        GTJA191_006(),
        GTJA191_007(),
        GTJA191_008(),
        GTJA191_009(),
        GTJA191_010(),
        GTJA191_011(),
        GTJA191_012(),
        GTJA191_013(),
        GTJA191_014(),
        GTJA191_015(),
        GTJA191_016(),
        GTJA191_017(),
        GTJA191_018(),
        GTJA191_019(),
        GTJA191_025(),
        GTJA191_030(),
        GTJA191_033(),
        GTJA191_034(),
        GTJA191_037(),
        GTJA191_040(),
        GTJA191_047(),
        GTJA191_048(),
        GTJA191_050(),
        GTJA191_054(),
        GTJA191_056(),
        GTJA191_060(),
        GTJA191_065(),
        GTJA191_070(),
        GTJA191_075(),
        GTJA191_080(),
        GTJA191_085(),
        GTJA191_090(),
        GTJA191_100(),
        GTJA191_110(),
        GTJA191_120(),
        GTJA191_130(),
        GTJA191_140(),
        GTJA191_150(),
        GTJA191_160(),
        GTJA191_170(),
        GTJA191_180(),
        GTJA191_191(),
    ]
