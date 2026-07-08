"""Trading persona definitions API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ._data import personas_list

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("/list")
async def list_personas() -> dict[str, Any]:
    return {
        "personas": personas_list(),
        "module": "personas",
        "endpoint": "list",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic",
    }


@router.get("/types")
async def get_persona_types() -> dict[str, Any]:
    return {
        "types": ["institutional", "retail", "hedge_fund", "defi", "proprietary"],
        "module": "personas",
        "endpoint": "types",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{name}")
async def get_persona(name: str) -> dict[str, Any]:
    personas = {p["name"].lower().replace(" ", "_"): p for p in personas_list()}
    return personas.get(name, {"error": "not_found", "name": name})
