"""Feature engineering API routes (QuantScience QS12 / W-gap-3).

Exposes the feature_engine stack so the dashboard / external callers can compute
the 8 base features (rsi_14, macd_*, bbands_*, atr_14, returns, vol) from OHLCV.
Lazy-imports feature_engine so the route is safe even if pytimetk is absent.
"""

import logging
from typing import Any, Dict, List

import numpy as np
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class FeatureResponse:
    """Pydantic-free response wrapper (works with mount_router's add_route bypass)."""
    def __init__(self, symbol: str, features: List[str], rows: int, sample: Dict[str, Any]):
        self.symbol = symbol
        self.features = features
        self.rows = rows
        self.sample = sample

    def dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "features": self.features,
            "rows": self.rows,
            "sample": self.sample,
        }


async def compute_features(req: Request):
    """Compute the QNA base feature stack from OHLCV rows.

    Accepts raw Request (works with mount_router's add_route bypass).
    Lazy-imports feature_engine so route is safe even if pytimetk absent.
    """
    try:
        from quant_nanggroe.engine.factors.feature_engine import (
            generate_features,
            feature_names,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"feature_engine unavailable: {e}")

    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    symbol = body.get("symbol", "UNKNOWN")
    ohlcv = body.get("ohlcv", [])
    use_polars = body.get("use_polars", False)

    if not ohlcv:
        raise HTTPException(status_code=400, detail="ohlc empty")

    import pandas as pd
    df = pd.DataFrame(ohlcv)
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=400, detail=f"OHLCV requires columns {sorted(required)}"
        )
    try:
        out = generate_features(df, use_polars=use_polars)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"feature compute failed: {e}")

    names = feature_names()
    sample = {c: _jsonable(out[c].iloc[-1]) for c in names if c in out.columns}
    resp = FeatureResponse(
        symbol=symbol,
        features=names,
        rows=len(out),
        sample=sample,
    )
    return JSONResponse(content=resp.dict())


# Router kept for backwards-compat / OpenAPI schema generation.
# The actual mounting uses app.router.add_route directly — see app.py.
# mount_router bypasses FastAPI's Pydantic body parsing, so compute_features
# uses raw Request.json() for body parsing.
from fastapi import APIRouter
router = APIRouter()
router.add_api_route("", compute_features, methods=["POST"], tags=["Features"])


def _jsonable(v: Any) -> Any:
    try:
        if hasattr(v, "item"):  # numpy scalar
            return _jsonable(v.item())
        if isinstance(v, (np.floating,)):  # type: ignore[name-defined]
            f = float(v)
            return f if f == f and f not in (float("-inf"), float("inf")) else None  # NaN/Inf -> null
        if isinstance(v, (np.integer,)):  # type: ignore[name-defined]
            return int(v)
        if isinstance(v, float):
            return v if v == v and v not in (float("-inf"), float("inf")) else None  # NaN/Inf -> null
        return float(v)
    except Exception:
        return str(v)
