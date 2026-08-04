"""Geopolitics routes — honest 501 (not implemented, no synthetic data).

Test contract (tests/test_stub_routes_fix.py::test_geopolitics_is_honest_501):
these endpoints must return 501 so callers know the feature is NOT wired,
instead of silently getting synthetic/reference data. Wire real provider here
when a data source lands (see agents/tools/geopolitical_tool.py).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/geopolitics", tags=["geopolitics"])


def _not_implemented():
    return JSONResponse(
        status_code=501,
        content={
            "status": "not_implemented",
            "detail": "Geopolitics data source not wired. No synthetic fallback.",
        },
    )


@router.get("/list")
async def geopolitics_list():
    return _not_implemented()


@router.get("/sanctions")
async def geopolitics_sanctions():
    return _not_implemented()


@router.get("/regions")
async def geopolitics_regions():
    return _not_implemented()
