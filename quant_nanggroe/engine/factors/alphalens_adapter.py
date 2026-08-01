"""
Alphalens Adapter — factor evaluation tear sheets.

This module provides a lightweight, pure-NumPy/Pandas/SciPy implementation of the
three core Alphalens tear sheets so the engine can evaluate alpha factors without
depending on the (unmaintained, pandas-version-locked) ``alphalens`` package:

    1. Information Coefficient (IC) tear sheet
       - per-period, per-date Spearman & Pearson IC, IC p-values, ICIR.
    2. Quantile Spread tear sheet
       - bucket the factor into quantiles, compute mean forward return per
         quantile and the top-minus-bottom spread, with summary statistics.
    3. Turnover tear sheet
       - daily factor turnover (fraction of names changing quantile bucket) and
         factor autocorrelation, per forward-return period.

It also exposes :func:`to_alphalens_factor_data`, which reshapes an engine factor
panel (``date x asset``) and a price panel into the canonical Alphalens
``(date, asset)`` MultiIndex long format that all tear sheets consume.

The 469 engine factors are exposed via :func:`get_factor_panel` so any of them can
be fed straight into the tear sheets.

Methodology references
-----------------------
- Alphalens: https://github.com/quantopian/alphalens
- IC: information coefficient = rank correlation of factor vs. forward return.
- ICIR (information ratio): mean(IC) / std(IC).
- Turnover: fraction of assets whose quantile bucket changed day-over-day.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

logger = logging.getLogger(__name__)

# Forward-return horizons (in periods) recognised by the engine's factor library.
DEFAULT_PERIODS: Tuple[int, ...] = (1, 5, 10)


# ══════════════════════════════════════════════════════════════════════════
# Data shaping — the Alphalens contract
# ══════════════════════════════════════════════════════════════════════════


@dataclass
class FactorData:
    """Canonical Alphalens factor_data container.

    ``data`` is a long-format DataFrame with a ``(date, asset)`` MultiIndex and
    columns: ``factor`` plus one forward-return column per horizon ``{p}D``.
    """

    data: pd.DataFrame
    periods: Tuple[int, ...]

    @property
    def factor_data(self) -> pd.DataFrame:
        """Alias used by downstream callers expecting the Alphalens variable name."""
        return self.data


def to_alphalens_factor_data(
    factor: pd.DataFrame,
    prices: pd.DataFrame,
    periods: Sequence[int] = DEFAULT_PERIODS,
    quantiles: Optional[int] = None,
    drop_na: bool = True,
) -> FactorData:
    """Reshape engine factor/price panels into Alphalens ``factor_data``.

    Args:
        factor: ``date x asset`` DataFrame of factor scores.
        prices: ``date x asset`` DataFrame of asset prices (used to build forward
            returns via pct_change).
        periods: forward-return horizons, in periods.
        quantiles: if given, also attach a ``factor_quantile`` column labelling
            each asset's quantile bucket for the given number of buckets.
        drop_na: drop rows with missing factor or missing *all* forward returns.

    Returns:
        A :class:`FactorData` whose ``.data`` has a ``(date, asset)`` MultiIndex.
    """
    if not factor.index.equals(prices.index):
        # Align on the intersection of dates to avoid mis-indexed forward returns.
        common = factor.index.intersection(prices.index)
        factor = factor.loc[common]
        prices = prices.loc[common]

    # Forward returns for every requested horizon.
    fwd: Dict[int, pd.DataFrame] = {}
    for p in periods:
        fwd[p] = prices.pct_change(p, fill_method=None).shift(-p)

    factor_long = factor.stack(dropna=False, future_stack=True).rename("factor")
    cols = {"factor": factor_long}
    for p in periods:
        cols[f"{p}D"] = fwd[p].stack(dropna=False, future_stack=True)
    factor_data = pd.concat(cols, axis=1)
    factor_data.index = factor_data.index.rename(["date", "asset"])

    if quantiles is not None:
        factor_data["factor_quantile"] = _quantile_groups(
            factor_data["factor"], quantiles
        )

    if drop_na:
        fwd_cols = [f"{p}D" for p in periods]
        # Keep a row if it has a factor value and at least one usable fwd return.
        valid = factor_data["factor"].notna() & factor_data[fwd_cols].notna().any(axis=1)
        factor_data = factor_data.loc[valid]

    factor_data = factor_data.sort_index()
    return FactorData(data=factor_data, periods=tuple(periods))


def _quantile_groups(factor_series: pd.Series, quantiles: int) -> pd.Series:
    """Label each asset's factor quantile, computed cross-sectionally per date."""

    def _bucket(x: pd.Series) -> pd.Series:
        try:
            return pd.qcut(x.rank(method="first"), quantiles, labels=False) + 1
        except ValueError:
            # Fewer unique values than quantiles — fall back to rank-based bins.
            return pd.cut(x.rank(method="first"), quantiles, labels=False) + 1

    if isinstance(factor_series.index, pd.MultiIndex):
        return factor_series.groupby(level="date", group_keys=False).apply(_bucket)
    return _bucket(factor_series)


# ══════════════════════════════════════════════════════════════════════════
# 1) Information Coefficient (IC) tear sheet
# ══════════════════════════════════════════════════════════════════════════


def factor_information_coefficient(
    factor_data: Union[FactorData, pd.DataFrame],
    periods: Optional[Sequence[int]] = None,
) -> pd.DataFrame:
    """Per-date, per-horizon Information Coefficient.

    Computes, for each date and each forward-return horizon, the Spearman (rank)
    and Pearson (linear) correlation between the factor and the forward return.

    Returns:
        DataFrame indexed by date with columns ``<p>D_IC`` and ``<p>D_RankIC``
        plus their p-values (``<p>D_IC_p`` and ``<p>D_RankIC_p``).
    """
    fd = _unwrap(factor_data)
    periods = list(periods) if periods else list(fd.periods)
    out_frames = []
    for p in periods:
        col = f"{p}D"
        if col not in fd.data.columns:
            continue
        sub = fd.data[[ "factor", col]].dropna()
        grouped = sub.groupby(level="date", group_keys=False)
        ic = grouped.apply(
            lambda g: g["factor"].corr(g[col], method="pearson"), include_groups=False
        )
        rank_ic = grouped.apply(
            lambda g: g["factor"].corr(g[col], method="spearman"), include_groups=False
        )
        n = grouped.size()
        # p-value for Spearman (the canonical IC test).
        rank_p = rank_ic.apply(
            lambda r: _spearman_pvalue(r, n.get(r.name, 0)) if pd.notna(r) else np.nan
        )
        out_frames.append(
            pd.DataFrame(
                {
                    f"{p}D_IC": ic,
                    f"{p}D_IC_p": rank_ic.apply(
                        lambda r: _spearman_pvalue(r, n.get(r.name, 0))
                        if pd.notna(r)
                        else np.nan
                    ),
                    f"{p}D_RankIC": rank_ic,
                    f"{p}D_RankIC_p": rank_p,
                }
            )
        )
    if not out_frames:
        return pd.DataFrame()
    return pd.concat(out_frames, axis=1).sort_index()


def mean_information_coefficient(
    factor_data: Union[FactorData, pd.DataFrame],
    periods: Optional[Sequence[int]] = None,
) -> pd.DataFrame:
    """Summary IC statistics per horizon (Alphalens ``mean_information_coefficient``).

    Returns a DataFrame with one row per horizon and columns:
        IC_mean, IC_std, ICIR (IC mean / IC std), IC_t_stat, rank_IC_mean,
        rank_IC_std, rank_ICIR, IC>0.5%_pct (fraction of positive IC dates).
    """
    ic_df = factor_information_coefficient(factor_data, periods)
    rows = []
    periods = list(periods) if periods else list(_unwrap(factor_data).periods)
    for p in periods:
        col = f"{p}D_RankIC"
        if col not in ic_df.columns:
            continue
        s = ic_df[col].dropna()
        if len(s) == 0:
            continue
        ic_mean = s.mean()
        ic_std = s.std()
        rows.append(
            {
                "period": f"{p}D",
                "IC_mean": ic_mean,
                "IC_std": ic_std,
                "ICIR": ic_mean / ic_std if ic_std and ic_std > 0 else np.nan,
                "IC_t_stat": ic_mean / (ic_std / np.sqrt(len(s))) if ic_std and ic_std > 0 else np.nan,
                "rank_IC_mean": ic_mean,
                "rank_IC_std": ic_std,
                "rank_ICIR": ic_mean / ic_std if ic_std and ic_std > 0 else np.nan,
                "IC_positive_pct": float((s > 0).mean()),
                "n_days": len(s),
            }
        )
    return pd.DataFrame(rows).set_index("period")


# ══════════════════════════════════════════════════════════════════════════
# 2) Quantile Spread (returns) tear sheet
# ══════════════════════════════════════════════════════════════════════════


def quantile_spread(
    factor_data: Union[FactorData, pd.DataFrame],
    quantiles: int = 5,
    periods: Optional[Sequence[int]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Quantile-return and top-minus-bottom spread tear sheet.

    Args:
        factor_data: a :class:`FactorData` (or its ``.data``). If it does not yet
            carry a ``factor_quantile`` column it is computed with ``quantiles``.
        quantiles: number of quantile buckets (default 5).
        periods: forward-return horizons to evaluate.

    Returns:
        ``(mean_ret_by_quantile, spread_summary)``.

        ``mean_ret_by_quantile`` is a DataFrame indexed by date with a block of
        columns per horizon: ``<p>D_q1`` ... ``<p>D_q{quantiles}`` giving the mean
        forward return of each quantile, plus ``<p>D_spread`` (top minus bottom).
        ``spread_summary`` is one row per horizon with the mean spread, std,
        t-stat, and annualised Sharpe proxy (mean/std * sqrt(252)).
    """
    fd = _unwrap(factor_data)
    data = fd.data
    periods = list(periods) if periods else list(fd.periods)

    if "factor_quantile" not in data.columns:
        data = data.copy()
        data["factor_quantile"] = _quantile_groups(data["factor"], quantiles)
        fd = FactorData(data=data, periods=fd.periods)

    spread_frames = []
    summary_rows = []
    for p in periods:
        col = f"{p}D"
        if col not in fd.data.columns:
            continue
        sub = fd.data[[col, "factor_quantile"]].dropna()
        grp = sub.groupby(["date", "factor_quantile"])[col].mean().unstack()
        rename = {q: f"{p}D_q{q}" for q in grp.columns}
        grp = grp.rename(columns=rename)
        if grp.shape[1] >= 2:
            lo, hi = grp.columns[0], grp.columns[-1]
            grp[f"{p}D_spread"] = grp[hi] - grp[lo]
            spread = grp[f"{p}D_spread"].dropna()
            if len(spread) > 0:
                sd = spread.std()
                summary_rows.append(
                    {
                        "period": f"{p}D",
                        "spread_mean": spread.mean(),
                        "spread_std": sd,
                        "spread_t_stat": spread.mean() / (sd / np.sqrt(len(spread)))
                        if sd and sd > 0
                        else np.nan,
                        "spread_sharpe_ann": spread.mean() / sd * np.sqrt(252)
                        if sd and sd > 0
                        else np.nan,
                        "n_days": len(spread),
                    }
                )
        spread_frames.append(grp)

    mean_ret = (
        pd.concat(spread_frames, axis=1).sort_index()
        if spread_frames
        else pd.DataFrame()
    )
    spread_summary = pd.DataFrame(summary_rows).set_index("period")
    return mean_ret, spread_summary


# ══════════════════════════════════════════════════════════════════════════
# 3) Turnover tear sheet
# ══════════════════════════════════════════════════════════════════════════


def factor_turnover(
    factor_data: Union[FactorData, pd.DataFrame],
    quantiles: int = 5,
    periods: Optional[Sequence[int]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Daily factor turnover + autocorrelation tear sheet.

    Turnover for horizon ``p`` on date ``t`` is the fraction of assets whose
    factor_quantile bucket differs between ``t`` and ``t + p`` (Alphalens
    convention: compare bucket at ``t`` with bucket at ``t + p`` so turnover is
    expressed in forward-return-period units).

    Returns:
        ``(daily_turnover, summary)``.

        ``daily_turnover`` is a DataFrame indexed by date with one column per
        horizon ``turnover_<p>D``. ``summary`` has one row per horizon with the
        mean turnover and the factor (Spearman) autocorrelation at that horizon.
    """
    fd = _unwrap(factor_data)
    data = fd.data
    periods = list(periods) if periods else list(fd.periods)

    if "factor_quantile" not in data.columns:
        data = data.copy()
        data["factor_quantile"] = _quantile_groups(data["factor"], quantiles)
        fd = FactorData(data=data, periods=fd.periods)

    wide = fd.data["factor_quantile"].unstack()
    turnover_frames = []
    summary_rows = []
    for p in periods:
        shifted = wide.shift(p)
        changed = (wide != shifted).fillna(False)
        # Turnover = mean fraction of names that changed bucket, per date.
        turnover = changed.mean(axis=1).dropna()
        turnover.name = f"turnover_{p}D"
        turnover_frames.append(turnover.to_frame())

        # Spearman autocorrelation of the factor score itself at horizon p.
        fwide = fd.data["factor"].unstack()
        a = fwide
        b = fwide.shift(p)
        auto_vals = []
        for d in a.columns:
            pair = pd.concat([a[d], b[d]], axis=1).dropna()
            if len(pair) > 2:
                auto_vals.append(pair.iloc[:, 0].corr(pair.iloc[:, 1], method="spearman"))
        autocorr = float(np.nanmean(auto_vals)) if auto_vals else np.nan
        summary_rows.append(
            {
                "period": f"{p}D",
                "turnover_mean": float(turnover.mean()) if len(turnover) else np.nan,
                "autocorrelation": autocorr,
            }
        )

    daily_turnover = (
        pd.concat(turnover_frames, axis=1).sort_index()
        if turnover_frames
        else pd.DataFrame()
    )
    summary = pd.DataFrame(summary_rows).set_index("period")
    return daily_turnover, summary


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════


def _unwrap(factor_data: Union[FactorData, pd.DataFrame]) -> FactorData:
    """Accept either a FactorData or a raw DataFrame (treat as FactorData.data)."""
    if isinstance(factor_data, FactorData):
        return factor_data
    if isinstance(factor_data, pd.DataFrame):
        # Infer periods from forward-return columns named "<p>D".
        periods = tuple(
            int(c[:-1]) for c in factor_data.columns if c.endswith("D") and c[:-1].isdigit()
        )
        return FactorData(data=factor_data, periods=periods or DEFAULT_PERIODS)
    raise TypeError(f"Expected FactorData or DataFrame, got {type(factor_data)!r}")


def _spearman_pvalue(rho: float, n: int) -> float:
    """Two-sided p-value for a Spearman correlation given sample size ``n``.

    Uses the t-approximation valid for n > 2 (Alphalens uses the same formula).
    """
    if not isinstance(rho, (int, float)) or pd.isna(rho):
        return np.nan
    if n < 3:
        return np.nan
    t = rho * np.sqrt((n - 2) / max(1e-12, 1.0 - rho * rho))
    p = 2 * (1.0 - sp_stats.t.cdf(abs(t), df=n - 2))
    return float(p)


def get_factor_panel(factor_names: Optional[Sequence[str]] = None) -> Dict[str, pd.DataFrame]:
    """Return factor panels keyed by name for the engine's wired factors.

    The engine exposes 469 alpha factors through its factor library. This helper
    is the integration point: callers pass the names they want evaluated and
    receive ``date x asset`` panels suitable for :func:`to_alphalens_factor_data`.

    The concrete wiring lives in ``engine.factors.registry``; this adapter only
    depends on the panel shape, keeping it decoupled from the factor source.

    Returns:
        Dict mapping factor name -> ``date x asset`` factor-value DataFrame.
        When no registry is importable an empty dict is returned (the tear-sheet
        functions still work on panels supplied directly by the caller).
    """
    try:  # pragma: no cover - integration glue, optional at import time
        from quant_nanggroe.engine.factors.registry import get_factor_panels

        return get_factor_panels(factor_names)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Factor registry not available for panel export: %s", exc)
        return {}


def run_tear_sheets(
    factor: pd.DataFrame,
    prices: pd.DataFrame,
    quantiles: int = 5,
    periods: Sequence[int] = DEFAULT_PERIODS,
) -> Dict[str, pd.DataFrame]:
    """Convenience: build factor_data and compute all three tear sheets at once.

    Returns a dict with keys ``ic`` (per-date IC), ``ic_summary``, ``spread``
    (mean return by quantile), ``spread_summary``, ``turnover`` (daily) and
    ``turnover_summary``.
    """
    fd = to_alphalens_factor_data(factor, prices, periods=periods, quantiles=quantiles)
    ic = factor_information_coefficient(fd)
    ic_summary = mean_information_coefficient(fd)
    spread, spread_summary = quantile_spread(fd, quantiles=quantiles, periods=periods)
    turnover, turnover_summary = factor_turnover(fd, quantiles=quantiles, periods=periods)
    return {
        "factor_data": fd.data,
        "ic": ic,
        "ic_summary": ic_summary,
        "spread": spread,
        "spread_summary": spread_summary,
        "turnover": turnover,
        "turnover_summary": turnover_summary,
    }
