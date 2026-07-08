"""Trading persona definitions API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("/list")
async def list_personas() -> dict[str, Any]:
    """Return available trading persona definitions."""
    return {"personas": [], "module": "personas"}


@router.get("/types")
async def get_persona_types() -> dict[str, Any]:
    """Return persona type taxonomy."""
    return {"types": [], "module": "personas"}


@router.get("/{name}")
async def get_persona(name: str) -> dict[str, Any]:
    """Return a single persona definition by name.

    Args:
        name: Persona identifier.

    Returns:
        Persona definition or empty stub.
    """
    return {"name": name, "module": "personas", "definition": {}}
