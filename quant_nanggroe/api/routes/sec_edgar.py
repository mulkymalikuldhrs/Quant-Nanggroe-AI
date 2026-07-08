"""SEC EDGAR filings API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

from ._data import sec_filings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sec/edgar", tags=["sec_edgar"])


@router.get("/filings")
async def list_filings() -> dict[str, Any]:
    return {
        "items": sec_filings(),
        "count": 5,
        "module": "sec_edgar",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/company/{cik}")
async def company_filings(cik: str) -> dict[str, Any]:
    ticker = cik.upper()
    results = [f for f in sec_filings() if f["ticker"] == ticker]
    return {"items": results, "count": len(results), "cik": cik}


@router.get("/search")
async def search_filings(q: str = Query(..., description="Search query")) -> dict[str, Any]:
    results = [f for f in sec_filings() if q.upper() in f["ticker"]]
    return {"items": results, "count": len(results), "query": q}
