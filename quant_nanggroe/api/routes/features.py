"""Feature engineering API routes (QuantScience QS12 / W-gap-3).

Exposes the feature_engine stack so the dashboard / external callers can compute
the 8 base features (rsi_14, macd_*, bbands_*, atr_14, returns, vol) from OHLCV.
Lazy-imports feature_engine so the route is safe even if pytimetk is absent.
"""

import logging
from typing import Any, Dict, List

import numpy as np

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class FeatureRequest(BaseModel):
    symbol: str = Field(..., description="Symbol label for the returned frame")
    ohlcv: List[Dict[str, Any]] = Field(
        ..., description="List of OHLCV rows with open/high/low/close[/volume/timestamp]"
    )
    use_polars: bool = Field(False, description="Reserved for future Polars backend")


class FeatureResponse(BaseModel):
    symbol: str
    features: List[str]
    rows: int
    sample: Dict[str, Any] = Field(default_factory=dict)


@router.post("", tags=["Features"])
def compute_features(req: FeatureRequest) -> FeatureResponse:
    """Compute the QNA base feature stack from OHLCV rows."""
    try:
        from quant_nanggroe.engine.factors.feature_engine import (
            generate_features,
            feature_names,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"feature_engine unavailable: {e}")

    if not req.ohlcv:
        raise HTTPException(status_code=400, detail="ohlc empty")
    import pandas as pd

    df = pd.DataFrame(req.ohlcv)
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=400, detail=f"OHLCV requires columns {sorted(required)}"
        )
    try:
        out = generate_features(df, use_polars=req.use_polars)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"feature compute failed: {e}")

    names = feature_names()
    sample = {c: _jsonable(out[c].iloc[-1]) for c in names if c in out.columns}
    return FeatureResponse(
        symbol=req.symbol,
        features=names,
        rows=len(out),
        sample=sample,
    )


def _jsonable(v: Any) -> Any:
    try:
        if hasattr(v, "item"):  # numpy scalar
            return v.item()
        if isinstance(v, (np.floating,)):  # type: ignore[name-defined]
            return float(v)
        if isinstance(v, (np.integer,)):  # type: ignore[name-defined]
            return int(v)
        return float(v)
    except Exception:
        return str(v)
