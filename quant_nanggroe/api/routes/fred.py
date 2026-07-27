"""FRED economic data API routes — wired to real FRED API via MacroSurpriseIndex."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter()

# Default FRED series tracked by the system
_TRACKED_SERIES = [
    ("GDP", "Gross Domestic Product", "B"),
    ("CPIAUCSL", "Consumer Price Index", "%"),
    ("UNRATE", "Unemployment Rate", "%"),
    ("FEDFUNDS", "Federal Funds Rate", "%"),
    ("T10YIE", "10-Year Breakeven Inflation", "%"),
    ("DSPIC96", "Real Disposable Personal Income", "%"),
    ("INDPRO", "Industrial Production Index", "%"),
    ("PAYEMS", "Total Nonfarm Payrolls", "K"),
]


def _get_fred_client() -> Any:
    """Lazy-load FRED API client."""
    try:
        from quant_nanggroe.engine.causal.macro_surprise import MacroSurpriseIndex
        api_key = os.environ.get("FRED_API_KEY") or os.environ.get("QNAI_FRED_API_KEY")
        msi = MacroSurpriseIndex(fred_api_key=api_key)
        if msi.is_connected:
            return msi
    except Exception as exc:
        logger.debug("FRED client unavailable: %s", exc)
    return None


@router.get("/series")
async def list_series() -> dict[str, Any]:
    """List tracked FRED series with latest values from real API."""
    fred = _get_fred_client()
    items = []
    for series_id, title, unit in _TRACKED_SERIES:
        item = {
            "id": series_id,
            "title": title,
            "unit": unit,
            "latest_value": None,
            "source": "fred_api" if fred else "static_registry",
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        # Try to fetch real value from FRED
        if fred is not None:
            try:
                data = fred._client.get_series(series_id)
                if data is not None and len(data) > 0:
                    item["latest_value"] = str(data.iloc[-1])
                    item["updated"] = str(data.index[-1])
            except Exception:
                pass
        items.append(item)

    return {
        "items": items,
        "count": len(items),
        "module": "fred",
        "fred_connected": fred is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/series/{series_id}")
async def get_series(series_id: str) -> dict[str, Any]:
    """Get a specific FRED series with real data."""
    fred = _get_fred_client()
    if fred is not None:
        try:
            data = fred._client.get_series(series_id)
            if data is not None and len(data) > 0:
                values = [
                    {"date": str(d.date()), "value": float(v)}
                    for d, v in data.tail(30).items()
                ]
                return {
                    "id": series_id,
                    "values": values,
                    "latest": float(data.iloc[-1]),
                    "fred_connected": True,
                }
        except Exception as exc:
            logger.debug("FRED series fetch failed for %s: %s", series_id, exc)

    # Fallback: return registry info
    for sid, title, unit in _TRACKED_SERIES:
        if sid.lower() == series_id.lower():
            return {
                "id": series_id,
                "title": title,
                "unit": unit,
                "fred_connected": False,
                "hint": "Set FRED_API_KEY env var for live data",
            }
    return {"error": "not_found", "id": series_id, "fred_connected": fred is not None}


@router.get("/search")
async def search_series(q: str = Query("", description="Search keyword")) -> dict[str, Any]:
    """Search tracked FRED series."""
    results = [
        {"id": sid, "title": title, "unit": unit}
        for sid, title, unit in _TRACKED_SERIES
        if q.lower() in title.lower() or q.lower() in sid.lower()
    ] if q else []
    return {"query": q, "items": results, "count": len(results)}
