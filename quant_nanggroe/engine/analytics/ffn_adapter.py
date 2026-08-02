"""ffn analytics adapter (QS020 research distilled from quant-research-kb).

Research basis:
- ffn is the reference tool for quick tear-sheets (Sharpe/Sortino/Calmar,
  monthly returns heatmap, max drawdown) in quant newsletters.
- QNA reporting wants a *stable dict contract* regardless of whether
  ffn is installed (heavy dep). So: use ffn when available, fall back
  to direct numpy/pandas math otherwise. Same keys, same semantics.

Design (ponytail):
- Lazy import of ffn inside functions (keeps import time low).
- Fallback math is 10 lines, not a reimplementation of ffn.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _try_ffn():
    try:
        import ffn  # type: ignore

        return ffn
    except ImportError:
        return None


def _fallback_stats(returns: pd.Series) -> dict[str, float]:
    """Minimal stats when ffn is unavailable (identical keys)."""
    # Resample to annual frequency factors on daily data
    periods = 252
    total_return = float((1 + returns).prod() - 1)
    years = len(returns) / periods
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 and (1 + total_return) > 0 else 0.0
    excess = returns - returns.mean()
    vol = float(returns.std(ddof=1))
    sharpe = float(returns.mean() / vol * np.sqrt(periods)) if vol > 0 else 0.0

    downside = returns[returns < 0]
    downside_vol = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sortino = float(returns.mean() / downside_vol * np.sqrt(periods)) if downside_vol > 0 else 0.0

    cum = (1 + returns).cumprod()
    running_max = cum.cummax()
    drawdown = cum / running_max - 1.0
    max_drawdown = float(drawdown.min())

    peak_idx = int(running_max.idxmax()) if len(running_max) else 0
    recovery = (cum.iloc[-1] / running_max.iloc[0]) if len(cum) else 1.0
    calmar = float(cagr / abs(max_drawdown)) if max_drawdown < 0 else 0.0
    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_drawdown,
        "volatility": vol,
    }


def compute_stats(returns: pd.Series) -> dict[str, Any]:
    """Compute risk/return stats with ffn when available, else fallback.

    Returns dict with keys: total_return, cagr, sharpe, sortino, calmar,
    max_drawdown, volatility (+ any extra ffn fields when ffn present).
    """
    ffn = _try_ffn()
    if ffn is None:
        return _fallback_stats(returns)
    stats = ffn.calc_stats(returns)
    return {
        "total_return": float(stats.total_return),
        "cagr": float(stats.cagr),
        "sharpe": float(stats.sharpe),
        "sortino": float(stats.sortino),
        "calmar": float(stats.calmar),
        "max_drawdown": float(stats.max_drawdown),
        "volatility": float(stats.volatility),
    }


def monthly_returns_table(returns: pd.Series) -> pd.DataFrame:
    """Year x Month returns heatmap (ffn-style)."""
    ffn = _try_ffn()
    if ffn is not None and hasattr(ffn, "to_returns"):
        try:
            table = ffn.utils.to_returns(returns.to_frame("close"))
        except Exception:
            table = None
        if table is not None and not table.empty:
            return table
    # Fallback: pivot daily returns to year x month
    df = pd.DataFrame({"returns": returns})
    df["year"] = df.index.year
    df["month"] = df.index.month_name().str[:3]
    return df.pivot_table(index="year", columns="month", values="returns", aggfunc="prod")
