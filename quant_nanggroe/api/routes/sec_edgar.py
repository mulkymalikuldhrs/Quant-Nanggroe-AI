"""SEC EDGAR filings API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sec/edgar", tags=["sec_edgar"])


@router.get("/filings")
async def list_filings() -> dict[str, Any]:
    """List recent SEC EDGAR filings."""
    return {"items": [], "count": 0}


@router.get("/company/{cik}")
async def company_filings(cik: str) -> dict[str, Any]:
    """List EDGAR filings for a company by CIK number."""
    return {"items": [], "count": 0, "cik": cik}


@router.get("/search")
async def search_filings(q: str = Query(..., description="Search query")) -> dict[str, Any]:
    """Search SEC EDGAR filings by keyword or phrase."""
    return {"items": [], "count": 0, "query": q}
