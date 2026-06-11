"""Guotai Junan 191 Alphas.

Implements a selection of the most impactful alphas from the
Guotai Junan 191 Alpha research report (2014).

These alphas focus on Chinese A-share market characteristics including:
- Volume-price dynamics
- Intraday return patterns
- Cross-sectional momentum/reversal

Reference: 国泰君安 191 alpha 研报 (2014)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    FactorMeta,
    decay_linear,
    delta,
    rank,
    safe_div,
    ts_corr,
    ts_cov,
    ts_max,
    ts_mean,
    ts_min,
    ts_rank,
    ts_std,
)


class GTJA191_001(AlphaFactor):
    """GTJA Alpha #1.

    Formula: (-1 * CORR(RANK(DELTA(LOG(VOLUME), 1)), RANK(((CLOSE - OPEN) / OPEN)), 6))
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
        v = df[["volume"]] if isinstance(df["volume"], pd.Series) else df["volume"]
        c = df[["close"]] if isinstance(df["close"], pd.Series) else df["close"]
        o = df[["open"]] if isinstance(df["open"], pd.Series) else df["open"]

        x = rank(delta(np.log(v.where(v > 0)), 1))
        y = rank(safe_div(c - o, o))
        result = -1.0 * ts_corr(x, y, 6)
        return result.mean(axis=1) if isinstance(result, pd.DataFrame) else result


class GTJA191_005(AlphaFactor):
    """GTJA Alpha #5.

    Formula: -rank(ts_corr(close, volume, 5)) * rank(ts_corr(delta(close, 5), delta(volume, 5), 5))
    Source: 国泰君安 191 alpha 研报 (2014), alpha 5.
    Theme: volume, momentum
    """

    @property
    def name(self) -> str:
        return "gtja191_005"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_005",
            zoo="gtja191",
            theme=["volume", "momentum"],
            formula_latex=r"-\text{rank}(\text{corr}(C,V,5)) \cdot \text{rank}(\text{corr}(\Delta C_5, \Delta V_5, 5))",
            columns_required=["close", "volume"],
            universe=["equity_cn"],
            decay_horizon=5,
            min_warmup_bars=10,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df[["close"]] if isinstance(df["close"], pd.Series) else df["close"]
        v = df[["volume"]] if isinstance(df["volume"], pd.Series) else df["volume"]

        corr1 = rank(ts_corr(c, v, 5))
        corr2 = rank(ts_corr(delta(c, 5), delta(v, 5), 5))
        result = -corr1 * corr2
        return result.mean(axis=1) if isinstance(result, pd.DataFrame) else result


class GTJA191_017(AlphaFactor):
    """GTJA Alpha #17.

    Formula: -rank(ts_corr(close, volume, 5)) * rank(delta(close, 5) / close)
    Source: 国泰君安 191 alpha 研报 (2014), alpha 17.
    Theme: momentum, volume
    """

    @property
    def name(self) -> str:
        return "gtja191_017"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_017",
            zoo="gtja191",
            theme=["momentum", "volume"],
            formula_latex=r"-\text{rank}(\text{corr}(C,V,5)) \cdot \text{rank}(\Delta C_5 / C)",
            columns_required=["close", "volume"],
            universe=["equity_cn"],
            decay_horizon=5,
            min_warmup_bars=6,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df[["close"]] if isinstance(df["close"], pd.Series) else df["close"]
        v = df[["volume"]] if isinstance(df["volume"], pd.Series) else df["volume"]

        corr_rank = rank(ts_corr(c, v, 5))
        mom_rank = rank(safe_div(delta(c, 5), c))
        result = -corr_rank * mom_rank
        return result.mean(axis=1) if isinstance(result, pd.DataFrame) else result


class GTJA191_042(AlphaFactor):
    """GTJA Alpha #42.

    Formula: -rank(ts_std(high, 10)) * ts_corr(high, volume, 10)
    Source: 国泰君安 191 alpha 研报 (2014), alpha 42.
    Theme: volatility, volume
    """

    @property
    def name(self) -> str:
        return "gtja191_042"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_042",
            zoo="gtja191",
            theme=["volatility", "volume"],
            formula_latex=r"-\text{rank}(\sigma(H,10)) \cdot \text{corr}(H,V,10)",
            columns_required=["high", "volume"],
            universe=["equity_cn"],
            decay_horizon=10,
            min_warmup_bars=11,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        h = df[["high"]] if isinstance(df["high"], pd.Series) else df["high"]
        v = df[["volume"]] if isinstance(df["volume"], pd.Series) else df["volume"]

        result = -rank(ts_std(h, 10)) * ts_corr(h, v, 10)
        return result.mean(axis=1) if isinstance(result, pd.DataFrame) else result


class GTJA191_080(AlphaFactor):
    """GTJA Alpha #80.

    Formula: -rank(ts_corr(close, volume, 5)) * rank(ts_std(close, 20))
    Source: 国泰君安 191 alpha 研报 (2014), alpha 80.
    Theme: volume, volatility
    """

    @property
    def name(self) -> str:
        return "gtja191_080"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_080",
            zoo="gtja191",
            theme=["volume", "volatility"],
            formula_latex=r"-\text{rank}(\text{corr}(C,V,5)) \cdot \text{rank}(\sigma(C,20))",
            columns_required=["close", "volume"],
            universe=["equity_cn"],
            decay_horizon=20,
            min_warmup_bars=21,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df[["close"]] if isinstance(df["close"], pd.Series) else df["close"]
        v = df[["volume"]] if isinstance(df["volume"], pd.Series) else df["volume"]

        result = -rank(ts_corr(c, v, 5)) * rank(ts_std(c, 20))
        return result.mean(axis=1) if isinstance(result, pd.DataFrame) else result


class GTJA191_191(AlphaFactor):
    """GTJA Alpha #191.

    Formula: -rank(ts_corr(delta(close, 3), delta(volume, 3), 10)) * rank(close - ts_max(close, 5))
    Source: 国泰君安 191 alpha 研报 (2014), alpha 191.
    Theme: momentum, volume
    """

    @property
    def name(self) -> str:
        return "gtja191_191"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="gtja191_191",
            zoo="gtja191",
            theme=["momentum", "volume"],
            formula_latex=r"-\text{rank}(\text{corr}(\Delta C_3, \Delta V_3, 10)) \cdot \text{rank}(C - \max(C,5))",
            columns_required=["close", "volume"],
            universe=["equity_cn"],
            decay_horizon=10,
            min_warmup_bars=13,
            notes="Final alpha in the GTJA 191 series",
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        c = df[["close"]] if isinstance(df["close"], pd.Series) else df["close"]
        v = df[["volume"]] if isinstance(df["volume"], pd.Series) else df["volume"]

        corr_part = rank(ts_corr(delta(c, 3), delta(v, 3), 10))
        max_part = rank(c - ts_max(c, 5))
        result = -corr_part * max_part
        return result.mean(axis=1) if isinstance(result, pd.DataFrame) else result


def get_all_gtja191_factors() -> list:
    """Return instances of all implemented GTJA191 factors."""
    return [
        GTJA191_001(),
        GTJA191_005(),
        GTJA191_017(),
        GTJA191_042(),
        GTJA191_080(),
        GTJA191_191(),
    ]
