"""SEC EDGAR filings API routes — wired to real SECEdgarProvider."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sec/edgar", tags=["sec_edgar"])


def _get_sec_provider() -> Any:
    """Lazy-load the SECEdgarProvider."""
    try:
        from quant_nanggroe.data.providers.sec_edgar import SECEdgarProvider
        return SECEdgarProvider()
    except Exception as exc:
        logger.warning("SECEdgarProvider unavailable: %s", exc)
        return None


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/filings")
async def list_filings(
    ticker: str = Query("AAPL", description="Ticker symbol to look up"),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Fetch real SEC filings for a ticker via SECEdgarProvider."""
    sec = _get_sec_provider()
    if sec is None:
        return {
            "items": [],
            "count": 0,
            "ticker": ticker,
            "module": "sec_edgar",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "provider_unavailable",
        }
    try:
        filings = await sec.get_filings(ticker, limit=limit)
        return {
            "items": filings,
            "count": len(filings),
            "ticker": ticker,
            "module": "sec_edgar",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "live",
        }
    except Exception as exc:
        logger.warning("SEC EDGAR filings fetch failed for %s: %s", ticker, exc)
        return {
            "items": [],
            "count": 0,
            "ticker": ticker,
            "module": "sec_edgar",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(exc),
        }


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/company/{cik}")
async def company_filings(
    cik: str,
    filing_type: str | None = Query(None, description="Filter by form type (e.g. 10-K, 10-Q)"),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Fetch real SEC filings for a company by CIK or ticker."""
    sec = _get_sec_provider()
    if sec is None:
        return {"items": [], "count": 0, "cik": cik, "status": "provider_unavailable"}
    try:
        filings = await sec.get_filings(cik, filing_type=filing_type, limit=limit)
        return {"items": filings, "count": len(filings), "cik": cik, "status": "live"}
    except Exception as exc:
        logger.warning("SEC EDGAR company filings failed for %s: %s", cik, exc)
        return {"items": [], "count": 0, "cik": cik, "status": "error", "error": str(exc)}


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/search")
async def search_filings(
    q: str = Query(..., description="Ticker symbol to search"),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Search SEC filings by ticker symbol."""
    sec = _get_sec_provider()
    if sec is None:
        return {"items": [], "count": 0, "query": q, "status": "provider_unavailable"}
    try:
        filings = await sec.get_filings(q, limit=limit)
        return {"items": filings, "count": len(filings), "query": q, "status": "live"}
    except Exception as exc:
        logger.warning("SEC EDGAR search failed for %s: %s", q, exc)
        return {"items": [], "count": 0, "query": q, "status": "error", "error": str(exc)}


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/fundamentals/{cik}")
async def get_fundamentals(cik: str) -> dict[str, Any]:
    """Fetch real XBRL fundamentals for a company."""
    sec = _get_sec_provider()
    if sec is None:
        return {"fundamentals": {}, "cik": cik, "status": "provider_unavailable"}
    try:
        facts = await sec.get_fundamentals(cik)
        return {"fundamentals": facts, "cik": cik, "status": "live"}
    except Exception as exc:
        logger.warning("SEC EDGAR fundamentals failed for %s: %s", cik, exc)
        return {"fundamentals": {}, "cik": cik, "status": "error", "error": str(exc)}


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/financials/{cik}")
async def get_financials(
    cik: str,
    statement: str = Query("income_statement", description="income_statement|balance_sheet|cash_flow"),
    period: str = Query("annual", description="annual|quarterly"),
) -> dict[str, Any]:
    """Fetch real financial statements from XBRL data."""
    sec = _get_sec_provider()
    if sec is None:
        return {"statement": {}, "cik": cik, "status": "provider_unavailable"}
    try:
        result = await sec.get_financial_statements(cik, statement, period)
        return {"statement": result, "cik": cik, "statement_type": statement, "period": period, "status": "live"}
    except Exception as exc:
        logger.warning("SEC EDGAR financials failed for %s: %s", cik, exc)
        return {"statement": {}, "cik": cik, "status": "error", "error": str(exc)}


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/health")
async def sec_health() -> dict[str, Any]:
    """Check SEC EDGAR API health."""
    sec = _get_sec_provider()
    if sec is None:
        return {"healthy": False, "status": "provider_unavailable"}
    try:
        ok = await sec.health_check()
        return {"healthy": ok, "status": "live" if ok else "unreachable"}
    except Exception as exc:
        return {"healthy": False, "status": "error", "error": str(exc)}
