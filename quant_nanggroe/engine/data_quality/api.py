"""FastAPI router for data quality monitoring endpoints.

Endpoints follow the pipeline_status.py pattern: never returns 500,
graceful fallback, structured dict responses.

GET /api/data-quality          → health summary for all providers
GET /api/data-quality/{provider} → detailed health for one provider
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from quant_nanggroe.engine.data_quality import DataQualityMonitor, get_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-quality", tags=["Data Quality"])


@router.get("")
async def data_quality_health() -> dict[str, Any]:
    """Health summary for all tracked data providers."""
    try:
        monitor = get_monitor()
        return monitor.get_health()
    except Exception as exc:
        logger.warning("data_quality_health_failed: %s", exc)
        return {
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "overall_status": "offline",
            "error": str(exc),
            "total_providers": 0,
            "healthy_count": 0,
            "stale_count": 0,
            "degraded_count": 0,
            "failed_count": 0,
            "providers": {},
        }


@router.get("/{provider}")
async def provider_detail(provider: str) -> dict[str, Any]:
    """Detailed health for a single provider.

    Returns 404 if provider is not registered — callers should use the
    health summary to discover valid provider names.
    """
    try:
        monitor = get_monitor()
        state = monitor.get_provider_state(provider)
        if state is None:
            # List known providers for discoverability
            all_providers = list(monitor.get_health()["providers"].keys())
            return {
                "found": False,
                "error": f"Provider '{provider}' not registered",
                "registered_providers": all_providers,
            }
        return {
            "found": True,
            "provider": state.to_dict(),
        }
    except Exception as exc:
        logger.warning("provider_detail_failed [%s]: %s", provider, exc)
        return {
            "found": False,
            "error": str(exc),
            "provider": provider,
        }


@router.get("/{provider}/stale")
async def provider_stale_check(provider: str) -> dict[str, Any]:
    """Check staleness for a specific provider — lightweight probe."""
    try:
        monitor = get_monitor()
        state = monitor.get_provider_state(provider)
        if state is None:
            return {"found": False, "error": f"Provider '{provider}' not registered"}
        return {
            "provider": provider,
            "status": state.status,
            "is_stale": state.is_stale,
            "staleness_seconds": round(state.age_seconds, 1) if state.age_seconds else None,
            "threshold_seconds": state.stale_threshold,
        }
    except Exception as exc:
        logger.warning("stale_check_failed [%s]: %s", provider, exc)
        return {"provider": provider, "error": str(exc)}
