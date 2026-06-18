"""
Crucix OSINT Intelligence Client — Async HTTP bridge to the Crucix service.

Connects to Crucix's REST API and SSE stream to provide real-time
OSINT intelligence data to the AI MultiColony Ecosystem.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class SweepData(BaseModel):
    """Current OSINT sweep data from Crucix."""
    regime: str = Field(default="unknown", description="Market regime: risk-off, risk-on, mixed")
    sources_active: int = Field(default=0)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    news: List[Dict[str, Any]] = Field(default_factory=list)
    market_indices: Dict[str, Any] = Field(default_factory=dict)
    commodities: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None


class HealthStatus(BaseModel):
    """Crucix service health status."""
    status: str = "unknown"
    uptime: float = 0.0
    sources_ok: int = 0
    sources_total: int = 0
    llm_ok: bool = False


class DeltaSignal(BaseModel):
    """A single delta signal from the Crucix delta engine."""
    signal_id: str = ""
    source: str = ""
    direction: str = ""
    magnitude: float = 0.0
    category: str = ""
    summary: str = ""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class CrucixClient:
    """Async HTTP client for the Crucix OSINT intelligence service.

    Usage::

        client = CrucixClient(base_url="http://localhost:3117")
        data = await client.get_sweep_data()
        health = await client.get_health()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3117",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request_with_retry(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        client = await self._get_client()
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = await client.request(method, path, **kwargs)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "Crucix request failed (attempt %d/%d): %s %s — %s",
                    attempt + 1,
                    self.max_retries,
                    method,
                    path,
                    exc,
                )
        raise ConnectionError(
            f"Crucix {method} {path} failed after {self.max_retries} retries: {last_error}"
        ) from last_error

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def get_sweep_data(self) -> SweepData:
        """Fetch the current synthesized sweep data."""
        resp = await self._request_with_retry("GET", "/api/data")
        return SweepData(**resp.json())

    async def get_health(self) -> HealthStatus:
        """Fetch Crucix service health."""
        resp = await self._request_with_retry("GET", "/api/health")
        return HealthStatus(**resp.json())

    async def get_locales(self) -> List[str]:
        """List available locales."""
        resp = await self._request_with_retry("GET", "/api/locales")
        return resp.json().get("locales", ["en"])

    async def get_delta_signals(self) -> List[DeltaSignal]:
        """Parse delta signals from the latest sweep data.

        Note: Crucix doesn't have a dedicated delta API yet, so we
        extract delta info from the sweep data if present.
        """
        data = await self.get_sweep_data()
        signals: List[DeltaSignal] = []
        for raw in data.signals:
            if "delta" in raw:
                signals.append(
                    DeltaSignal(
                        signal_id=raw.get("id", ""),
                        source=raw.get("source", ""),
                        direction=raw.get("delta", {}).get("direction", ""),
                        magnitude=raw.get("delta", {}).get("magnitude", 0.0),
                        category=raw.get("category", ""),
                        summary=raw.get("summary", ""),
                    )
                )
        return signals

    async def is_healthy(self) -> bool:
        """Quick health check — returns True if Crucix responds."""
        try:
            health = await self.get_health()
            return health.status == "ok"
        except Exception:
            return False
