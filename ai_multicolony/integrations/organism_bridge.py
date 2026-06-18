"""
Organism Bridge — Client for the Autonomous Organism service.

Communicates with the Autonomous Organism via Supabase Edge Functions
to trigger organ engine cycles and retrieve status data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class OrganismStatus(BaseModel):
    """Status of an autonomous organism."""
    org_id: str = ""
    name: str = ""
    generation: int = 0
    status: str = "unknown"
    sense_count: int = 0
    decision_count: int = 0
    factory_count: int = 0
    growth_count: int = 0
    revenue: float = 0.0


class EngineRunResult(BaseModel):
    """Result from triggering an organ engine."""
    success: bool = False
    engine: str = ""
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class OrganismBridge:
    """Async client for the Autonomous Organism service via Supabase.

    Usage::

        bridge = OrganismBridge(
            supabase_url="https://xxx.supabase.co",
            supabase_key="eyJ..."
        )
        status = await bridge.get_organism_status(org_id="...")
        result = await bridge.trigger_sense(org_id="...")
    """

    def __init__(
        self,
        supabase_url: str = "",
        supabase_anon_key: str = "",
        timeout: float = 30.0,
    ) -> None:
        self.supabase_url = supabase_url or ""
        self.supabase_anon_key = supabase_anon_key or ""
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.supabase_anon_key:
                headers["apikey"] = self.supabase_anon_key
                headers["Authorization"] = f"Bearer {self.supabase_anon_key}"
            self._client = httpx.AsyncClient(
                base_url=self.supabase_url,
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _functions_url(self, function_name: str) -> str:
        return f"/functions/v1/{function_name}"

    # -----------------------------------------------------------------------
    # Trigger organ engines
    # -----------------------------------------------------------------------

    async def trigger_sense(self, org_id: str) -> EngineRunResult:
        """Trigger the Sense Engine to ingest problems from sources."""
        try:
            client = await self._get_client()
            resp = await client.post(
                self._functions_url("ingest-sense"),
                json={"org_id": org_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return EngineRunResult(success=True, engine="sense", output=data)
        except Exception as exc:
            logger.error("Organism trigger_sense error: %s", exc)
            return EngineRunResult(success=False, engine="sense", error=str(exc))

    async def trigger_decision(self, org_id: str) -> EngineRunResult:
        """Trigger the Decision Core to score and rank problems."""
        try:
            client = await self._get_client()
            resp = await client.post(
                self._functions_url("run-decision"),
                json={"org_id": org_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return EngineRunResult(success=True, engine="decision", output=data)
        except Exception as exc:
            logger.error("Organism trigger_decision error: %s", exc)
            return EngineRunResult(success=False, engine="decision", error=str(exc))

    async def trigger_factory(self, org_id: str) -> EngineRunResult:
        """Trigger the SaaS Factory to generate project templates."""
        try:
            client = await self._get_client()
            resp = await client.post(
                self._functions_url("run-factory"),
                json={"org_id": org_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return EngineRunResult(success=True, engine="factory", output=data)
        except Exception as exc:
            logger.error("Organism trigger_factory error: %s", exc)
            return EngineRunResult(success=False, engine="factory", error=str(exc))

    async def trigger_growth(self, org_id: str) -> EngineRunResult:
        """Trigger the Growth Engine to generate marketing campaigns."""
        try:
            client = await self._get_client()
            resp = await client.post(
                self._functions_url("run-growth"),
                json={"org_id": org_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return EngineRunResult(success=True, engine="growth", output=data)
        except Exception as exc:
            logger.error("Organism trigger_growth error: %s", exc)
            return EngineRunResult(success=False, engine="growth", error=str(exc))

    # -----------------------------------------------------------------------
    # Status queries
    # -----------------------------------------------------------------------

    async def get_organism_status(self, org_id: str) -> OrganismStatus:
        """Get the current status of an organism."""
        try:
            client = await self._get_client()
            # Query the organizations table
            resp = await client.get(
                "/rest/v1/organizations",
                params={"id": f"eq.{org_id}", "select": "*"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                org = data[0]
                return OrganismStatus(
                    org_id=org.get("id", org_id),
                    name=org.get("name", ""),
                    generation=org.get("generation", 0),
                    status=org.get("status", "unknown"),
                )
        except Exception as exc:
            logger.error("Organism get_organism_status error: %s", exc)

        return OrganismStatus(org_id=org_id)

    async def is_available(self) -> bool:
        """Check if the Organism service is reachable."""
        if not self.supabase_url:
            return False
        try:
            client = await self._get_client()
            resp = await client.get("/rest/v1/", timeout=5.0)
            return resp.status_code in (200, 401)  # 401 = reachable but needs auth
        except Exception:
            return False
