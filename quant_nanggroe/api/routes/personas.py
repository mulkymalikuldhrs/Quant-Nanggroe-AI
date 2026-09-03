"""Trading persona definitions API routes — wired to real persona agents."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/personas", tags=["personas"])

# Real persona registry — maps display name → (module, class)
_PERSONA_REGISTRY = {
    "warren_buffett": ("warren_buffett", "WarrenBuffettAgent", "value"),
    "peter_lynch": ("peter_lynch", "PeterLynchAgent", "growth_at_reasonable_price"),
    "ray_dalio": ("ray_dalio", "RayDalioAgent", "macro_economic"),
    "michael_burry": ("michael_burry", "MichaelBurryAgent", "deep_value"),
    "cathie_wood": ("cathie_wood", "CathieWoodAgent", "disruptive_growth"),
    "stanley_druckenmiller": ("stanley_druckenmiller", "StanleyDruckenmillerAgent", "macro_momentum"),
}


def _load_persona(key: str) -> Any:
    """Load a persona agent by key."""
    if key not in _PERSONA_REGISTRY:
        return None
    module_name, class_name, _style = _PERSONA_REGISTRY[key]
    try:
        mod = __import__(f"quant_nanggroe.agents.personas.{module_name}", fromlist=[class_name])
        cls = getattr(mod, class_name)
        return cls()
    except Exception as exc:
        logger.warning("Failed to load persona %s: %s", key, exc)
        return None


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/list")
async def list_personas() -> dict[str, Any]:
    """List all available investor personas with their styles."""
    personas = []
    for key, (_mod, _cls, style) in _PERSONA_REGISTRY.items():
        personas.append({
            "id": key,
            "name": key.replace("_", " ").title(),
            "style": style,
            "available": True,
        })
    return {
        "personas": personas,
        "count": len(personas),
        "module": "personas",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/types")
async def get_persona_types() -> dict[str, Any]:
    """Return unique persona investment styles."""
    styles = sorted({style for _, _, style in _PERSONA_REGISTRY.values()})
    return {
        "types": styles,
        "count": len(styles),
        "module": "personas",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/{persona_id}")
async def get_persona(persona_id: str) -> dict[str, Any]:
    """Get persona details and optionally run analysis on a symbol."""
    key = persona_id.lower().replace(" ", "_").replace("-", "_")
    if key not in _PERSONA_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    _mod, _cls, style = _PERSONA_REGISTRY[key]
    return {
        "id": key,
        "name": key.replace("_", " ").title(),
        "style": style,
        "module": f"quant_nanggroe.agents.personas.{_mod}",
        "class": _cls,
        "available": True,
    }


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/{persona_id}/analyze")
async def analyze_with_persona(persona_id: str, symbol: str = "BTC-USD") -> dict[str, Any]:
    """Run a real analysis using the persona agent."""
    key = persona_id.lower().replace(" ", "_").replace("-", "_")
    agent = _load_persona(key)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' could not be loaded")

    try:
        result = agent.analyze(symbol)
        return {
            "persona": key,
            "symbol": symbol,
            "analysis": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Persona analysis failed for %s/%s: %s", key, symbol, exc)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")
