"""Thin feature-enrichment adapter for QNA live strategies (GAP M1-WIRE).

Wires QuantScience feature_engine into the live candle path WITHOUT changing the
strategy contract. Strategies receive the same `candles` list (list[dict] with
open/high/low/close/volume). Each candle gets an optional `features` dict
attached (last computed value of each feature) so strategies that want
QuantScience features can read `candle["features"]` — strategies that ignore it
are completely unaffected.

Design (ponytail):
- pandas-only core, no new hard dependency.
- Non-destructive: input list is copied, original dicts untouched.
- Fail-safe: if feature compute raises, returns candles unchanged (no signal loss).
"""
from __future__ import annotations

import pandas as pd

from quant_nanggroe.engine.factors.feature_engine import generate_features, feature_names


def _candles_to_df(candles: list[dict]) -> pd.DataFrame:
    """Convert list[dict] candles to a DataFrame with ohlcv columns."""
    rows = []
    for c in candles:
        rows.append({
            "open": float(c.get("open", c.get("close", 0.0))),
            "high": float(c.get("high", c.get("close", 0.0))),
            "low": float(c.get("low", c.get("close", 0.0))),
            "close": float(c.get("close", 0.0)),
            "volume": float(c.get("volume", 0.0)),
        })
    return pd.DataFrame(rows)


def enrich_candles(candles: list[dict]) -> list[dict]:
    """Attach QuantScience features to each candle. Non-destructive + fail-safe.

    Returns a NEW list of dicts (originals untouched). Each dict gains a
    ``features`` key = {feature_name: latest_value}. On any failure, returns a
    shallow copy of the original candles without ``features`` (signal path safe).
    """
    if not candles:
        return list(candles)
    try:
        df = _candles_to_df(candles)
        enriched = generate_features(df)
        feats = {col: float(enriched[col].iloc[-1]) for col in feature_names() if col in enriched}
        out = []
        for i, c in enumerate(candles):
            nc = dict(c)
            nc["features"] = feats
            out.append(nc)
        return out
    except Exception:
        # Fail-safe: never break the signal path over a feature glitch.
        return [dict(c) for c in candles]


def validate_factor_ic(candles: list[dict], feature: str = "rsi_14",
                       forward: int = 5) -> float | None:
    """G6-WIRE: run Alphalens IC on a historical candle window.

    The alphalens_adapter (engine/factors/alphalens_adapter.py) was implemented
    but never called. This wires it into the factor-validation path: given a
    window of candles we have forward returns, so we can compute the
    information coefficient of a feature vs forward return. Returns the mean IC
    (or None if insufficient data / compute fails). Fail-safe.
    """
    if not candles or len(candles) < 30:
        return None
    try:
        from quant_nanggroe.engine.factors.alphalens_adapter import (
            FactorData,
            factor_information_coefficient,
        )
        df = _candles_to_df(candles)
        enriched = generate_features(df)
        if feature not in enriched.columns:
            return None
        fwd_ret = df["close"].pct_change(forward).shift(-forward)
        fd = FactorData(
            factor=enriched[feature],
            forward_returns=fwd_ret,
            datetime=df.index if hasattr(df, "index") else None,
        )
        ic = factor_information_coefficient(fd)
        return float(ic) if ic is not None else None
    except Exception:
        return None


__all__ = ["enrich_candles", "feature_names", "validate_factor_ic"]
