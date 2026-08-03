"""Data quality framework (QuantScience roadmap C8: staleness/gap/sanity).

Provides cheap, dependency-free checks on OHLCV frames so the pipeline can refuse
garbage-in before it reaches scoring. Designed to be called from the fallback chain
or a scheduled audit endpoint (GET /api/data/quality).

Design (ponytail):
- Pure pandas/numpy. No network, no heavy deps.
- Each check returns a structured DataQualityReport, not a boolean, so the
  dashboard can render per-symbol status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class DataQualityReport:
    symbol: str
    ok: bool
    checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    last_update: Optional[float] = None
    stale_seconds: Optional[float] = None


def _require_columns(df: pd.DataFrame) -> None:
    needed = {"open", "high", "low", "close"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"OHLCV frame missing columns: {sorted(missing)}")


def check_staleness(
    df: pd.DataFrame,
    symbol: str,
    now_ts: Optional[float] = None,
    max_age_seconds: float = 86_400,
) -> DataQualityReport:
    """Flag if latest bar is older than max_age_seconds (default 1 day)."""
    rep = DataQualityReport(symbol=symbol, ok=True)
    if "timestamp" in df.columns:
        last = float(pd.to_numeric(df["timestamp"]).iloc[-1])
        rep.last_update = last
        now = now_ts if now_ts is not None else float(pd.Timestamp.now("UTC").timestamp())
        age = now - last
        rep.stale_seconds = age
        if age > max_age_seconds:
            rep.ok = False
            rep.warnings.append(f"stale: {age:.0f}s old (> {max_age_seconds:.0f}s)")
        else:
            rep.checks.append("fresh")
    else:
        rep.warnings.append("no timestamp column; staleness unchecked")
    return rep


def check_ohlc_sanity(df: pd.DataFrame, symbol: str) -> DataQualityReport:
    """Price sanity: non-negative, high>=max(o,c), low<=min(o,c), volume>=0."""
    rep = DataQualityReport(symbol=symbol, ok=True)
    _require_columns(df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    if (c <= 0).any() or (o <= 0).any():
        rep.ok = False
        rep.warnings.append("non-positive price detected")
    if (h < c).any() or (h < o).any() or (l > c).any() or (l > o).any():
        rep.ok = False
        rep.warnings.append("OHLC inconsistency (high<close or low>close)")
    if "volume" in df.columns and (df["volume"] < 0).any():
        rep.ok = False
        rep.warnings.append("negative volume")
    if rep.ok:
        rep.checks.append("ohlc_sane")
    return rep


def check_gaps(df: pd.DataFrame, symbol: str, max_gap: int = 5) -> DataQualityReport:
    """Detect missing bars via timestamp delta exceeding expected cadence."""
    rep = DataQualityReport(symbol=symbol, ok=True)
    if "timestamp" not in df.columns:
        rep.warnings.append("no timestamp; gap check skipped")
        return rep
    ts = pd.to_numeric(df["timestamp"]).sort_values()
    deltas = ts.diff().dropna()
    if len(deltas) == 0:
        rep.warnings.append("insufficient rows for gap check")
        return rep
    median_delta = float(deltas.median())
    big = int((deltas > median_delta * max_gap).sum())
    if big > 0:
        rep.ok = False
        rep.warnings.append(f"{big} gap(s) > {max_gap}x median cadence")
    else:
        rep.checks.append("no_gaps")
    return rep


def assess(
    df: pd.DataFrame,
    symbol: str,
    now_ts: Optional[float] = None,
    max_age_seconds: float = 86_400,
) -> DataQualityReport:
    """Run all checks; combine into one report. ok=False if any check fails."""
    rep = DataQualityReport(symbol=symbol, ok=True)
    rep.checks.extend(check_staleness(df, symbol, now_ts=now_ts, max_age_seconds=max_age_seconds).checks)
    rep.warnings.extend(check_staleness(df, symbol, now_ts=now_ts, max_age_seconds=max_age_seconds).warnings)
    if not check_staleness(df, symbol, now_ts=now_ts, max_age_seconds=max_age_seconds).ok:
        rep.ok = False
    sub = check_ohlc_sanity(df, symbol)
    rep.checks.extend(sub.checks)
    if sub.warnings:
        rep.warnings.extend(sub.warnings)
        rep.ok = False
    sub = check_gaps(df, symbol)
    rep.checks.extend(sub.checks)
    if sub.warnings:
        rep.warnings.extend(sub.warnings)
        rep.ok = False
    return rep
