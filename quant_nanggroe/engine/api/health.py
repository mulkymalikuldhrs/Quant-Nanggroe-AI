"""Health & Readiness Probes — Monitoring Stubs.

Endpoints:
    GET /health   — System health (DB, data providers, LLM providers, engine modules)
    GET /metrics  — Prometheus-format metrics
    GET /ready    — Kubernetes readiness probe
    GET /live     — Kubernetes liveness probe

Intended to be mounted into the FastAPI app via include_router.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

_start_time = time.time()


# ── Models ────────────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str = "1.0.0"
    uptime_seconds: float
    timestamp: str
    components: list[ComponentHealth] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    ready: bool
    status: HealthStatus
    timestamp: str
    checks: dict[str, str] = Field(default_factory=dict)


class LivenessResponse(BaseModel):
    alive: bool
    uptime_seconds: float
    timestamp: str


# ── Health Checks ─────────────────────────────────────────────────────────────

def _check_database() -> ComponentHealth:
    """Check database connectivity."""
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "quant_nanggroe.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path), timeout=2)
            conn.execute("SELECT 1")
            conn.close()
            return ComponentHealth(name="database", status=HealthStatus.HEALTHY, message="SQLite OK")
        return ComponentHealth(name="database", status=HealthStatus.DEGRADED, message="Database file not found")
    except Exception as e:
        return ComponentHealth(name="database", status=HealthStatus.UNHEALTHY, message=str(e))


def _check_data_providers() -> ComponentHealth:
    """Check data provider availability."""
    providers = {
        "yfinance": "yfinance",
        "ccxt": "ccxt",
        "httpx": "httpx",
    }
    available = []
    unavailable = []
    for name, module in providers.items():
        try:
            __import__(module)
            available.append(name)
        except ImportError:
            unavailable.append(name)

    if not unavailable:
        return ComponentHealth(
            name="data_providers",
            status=HealthStatus.HEALTHY,
            message=f"{len(available)} providers available",
            details={"available": available},
        )
    if available:
        return ComponentHealth(
            name="data_providers",
            status=HealthStatus.DEGRADED,
            message=f"{len(available)}/{len(providers)} available",
            details={"available": available, "unavailable": unavailable},
        )
    return ComponentHealth(name="data_providers", status=HealthStatus.UNHEALTHY, message="No providers available")


def _check_llm_providers() -> ComponentHealth:
    """Check LLM provider configuration."""
    import os
    configured = []
    keys_to_check = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "Google": "GOOGLE_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY",
    }
    for provider, env_var in keys_to_check.items():
        if os.environ.get(env_var):
            configured.append(provider)

    if configured:
        return ComponentHealth(
            name="llm_providers",
            status=HealthStatus.HEALTHY,
            message=f"{len(configured)} providers configured",
            details={"configured": configured},
        )
    return ComponentHealth(
        name="llm_providers",
        status=HealthStatus.DEGRADED,
        message="No LLM API keys configured",
    )


def _check_engine_modules() -> ComponentHealth:
    """Check engine module availability."""
    modules = {
        "kelly": "quant_nanggroe.engine.kelly",
        "regime": "quant_nanggroe.engine.regime",
        "stress_testing": "quant_nanggroe.engine.stress_testing",
        "backtest": "quant_nanggroe.engine.backtest",
        "risk": "quant_nanggroe.engine.risk",
        "data": "quant_nanggroe.engine.data",
        "decision": "quant_nanggroe.engine.decision",
    }
    available = []
    failed = []
    for name, mod_path in modules.items():
        try:
            __import__(mod_path)
            available.append(name)
        except Exception:
            failed.append(name)

    if not failed:
        return ComponentHealth(
            name="engine_modules",
            status=HealthStatus.HEALTHY,
            message=f"{len(available)} modules loaded",
            details={"loaded": available},
        )
    return ComponentHealth(
        name="engine_modules",
        status=HealthStatus.DEGRADED if available else HealthStatus.UNHEALTHY,
        message=f"{len(available)}/{len(modules)} loaded",
        details={"loaded": available, "failed": failed},
    )


def _check_security() -> ComponentHealth:
    """Check security subsystem."""
    try:
        from quant_nanggroe.security import KeyVault
        vault = KeyVault()
        return ComponentHealth(name="security", status=HealthStatus.HEALTHY, message="KeyVault available")
    except ImportError:
        return ComponentHealth(name="security", status=HealthStatus.DEGRADED, message="Security module not installed")
    except Exception as e:
        return ComponentHealth(name="security", status=HealthStatus.UNHEALTHY, message=str(e))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_endpoint() -> HealthResponse:
    """Full system health check."""
    components = [
        _check_database(),
        _check_data_providers(),
        _check_llm_providers(),
        _check_engine_modules(),
        _check_security(),
    ]

    statuses = [c.status for c in components]
    if all(s == HealthStatus.HEALTHY for s in statuses):
        overall = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in statuses):
        overall = HealthStatus.UNHEALTHY
    else:
        overall = HealthStatus.DEGRADED

    return HealthResponse(
        status=overall,
        uptime_seconds=round(time.time() - _start_time, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Prometheus-format metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_endpoint() -> ReadinessResponse:
    """Kubernetes readiness probe — are we ready to accept traffic?"""
    checks: dict[str, str] = {}
    ready = True

    # Database must be accessible
    db_health = _check_database()
    checks["database"] = db_health.status.value
    if db_health.status == HealthStatus.UNHEALTHY:
        ready = False

    # At least one data provider must be available
    dp_health = _check_data_providers()
    checks["data_providers"] = dp_health.status.value
    if dp_health.status == HealthStatus.UNHEALTHY:
        ready = False

    # Engine modules must be loaded
    em_health = _check_engine_modules()
    checks["engine_modules"] = em_health.status.value
    if em_health.status == HealthStatus.UNHEALTHY:
        ready = False

    return ReadinessResponse(
        ready=ready,
        status=HealthStatus.HEALTHY if ready else HealthStatus.UNHEALTHY,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks,
    )


@router.get("/live", response_model=LivenessResponse)
async def liveness_endpoint() -> LivenessResponse:
    """Kubernetes liveness probe — is the process alive?"""
    return LivenessResponse(
        alive=True,
        uptime_seconds=round(time.time() - _start_time, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
