"""
Ecosystem Routes — Aggregated API endpoints for all ecosystem services.

Provides cross-service status checks, data proxying, and a unified
overview dashboard endpoint.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from ai_multicolony.config.logging_config import get_logger

logger = get_logger(__name__)


def create_router() -> APIRouter:
    """Create the ecosystem routes router."""
    router = APIRouter()

    @router.get("/status", summary="Overall ecosystem health")
    async def ecosystem_status() -> Dict[str, Any]:
        """Check health of all ecosystem services.

        Returns a status object for each integrated package:
        Crucix OSINT, HermesQuant Trading, Autonomous Organism.
        """
        result: Dict[str, Any] = {
            "ecosystem": "AI-MultiColony-Ecosystem",
            "version": "3.0.0",
            "services": {},
        }

        # Check Crucix OSINT
        try:
            from ai_multicolony.integrations.crucix_client import CrucixClient

            crucix = CrucixClient()
            healthy = await crucix.is_healthy()
            result["services"]["crucix"] = {
                "status": "healthy" if healthy else "unhealthy",
                "type": "osint_intelligence",
                "port": 3117,
            }
            await crucix.close()
        except Exception as exc:
            result["services"]["crucix"] = {
                "status": "unavailable",
                "error": str(exc),
            }

        # Check HermesQuant
        try:
            from ai_multicolony.integrations.hermes_bridge import HermesQuantBridge

            hermes = HermesQuantBridge()
            available = await hermes.is_available()
            result["services"]["hermes_quant"] = {
                "status": "available" if available else "unavailable",
                "type": "quantitative_trading",
            }
        except Exception as exc:
            result["services"]["hermes_quant"] = {
                "status": "unavailable",
                "error": str(exc),
            }

        # Check Autonomous Organism
        try:
            from ai_multicolony.integrations.organism_bridge import OrganismBridge
            import os

            organism = OrganismBridge(
                supabase_url=os.getenv("SUPABASE_URL", ""),
                supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            )
            available = await organism.is_available()
            result["services"]["autonomous_organism"] = {
                "status": "available" if available else "unavailable",
                "type": "autonomous_organism",
            }
            await organism.close()
        except Exception as exc:
            result["services"]["autonomous_organism"] = {
                "status": "unavailable",
                "error": str(exc),
            }

        # Overall status
        all_healthy = all(
            s.get("status") in ("healthy", "available")
            for s in result["services"].values()
        )
        result["overall"] = "healthy" if all_healthy else "degraded"

        return result

    @router.get("/crucix", summary="Crucix OSINT data")
    async def crucix_data() -> Dict[str, Any]:
        """Proxy to Crucix OSINT sweep data."""
        try:
            from ai_multicolony.integrations.crucix_client import CrucixClient

            client = CrucixClient()
            data = await client.get_sweep_data()
            health = await client.get_health()
            await client.close()
            return {"sweep": data.model_dump(), "health": health.model_dump()}
        except Exception as exc:
            logger.error("ecosystem_crucix_error", error=str(exc))
            return {"error": str(exc), "status": "unavailable"}

    @router.get("/hermes", summary="HermesQuant trading status")
    async def hermes_status() -> Dict[str, Any]:
        """HermesQuant trading engine status and portfolio data."""
        try:
            from ai_multicolony.integrations.hermes_bridge import HermesQuantBridge

            bridge = HermesQuantBridge()
            portfolio = await bridge.get_portfolio_status()
            available = await bridge.is_available()
            return {
                "available": available,
                "portfolio": portfolio,
            }
        except Exception as exc:
            logger.error("ecosystem_hermes_error", error=str(exc))
            return {"error": str(exc), "status": "unavailable"}

    @router.get("/organism", summary="Autonomous Organism status")
    async def organism_status() -> Dict[str, Any]:
        """Autonomous Organism service status."""
        try:
            from ai_multicolony.integrations.organism_bridge import OrganismBridge
            import os

            bridge = OrganismBridge(
                supabase_url=os.getenv("SUPABASE_URL", ""),
                supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            )
            available = await bridge.is_available()
            result: Dict[str, Any] = {"available": available}
            if available:
                # Try to get status for a default org
                org_id = os.getenv("DEFAULT_ORG_ID", "")
                if org_id:
                    status = await bridge.get_organism_status(org_id)
                    result["organism"] = status.model_dump()
            await bridge.close()
            return result
        except Exception as exc:
            logger.error("ecosystem_organism_error", error=str(exc))
            return {"error": str(exc), "status": "unavailable"}

    @router.get("/overview", summary="Combined ecosystem overview")
    async def ecosystem_overview() -> Dict[str, Any]:
        """Combined dashboard data from all ecosystem services.

        This is the primary endpoint for the unified dashboard,
        aggregating data from Crucix, HermesQuant, and Autonomous Organism.
        """
        overview: Dict[str, Any] = {
            "ecosystem": "AI-MultiColony-Ecosystem",
            "version": "3.0.0",
            "crucix": {},
            "hermes_quant": {},
            "autonomous_organism": {},
        }

        # Crucix data
        try:
            from ai_multicolony.integrations.crucix_client import CrucixClient

            client = CrucixClient()
            sweep = await client.get_sweep_data()
            health = await client.get_health()
            await client.close()
            overview["crucix"] = {
                "regime": sweep.regime,
                "sources_active": sweep.sources_active,
                "signal_count": len(sweep.signals),
                "news_count": len(sweep.news),
                "health": health.status,
            }
        except Exception:
            overview["crucix"] = {"status": "unavailable"}

        # HermesQuant data
        try:
            from ai_multicolony.integrations.hermes_bridge import HermesQuantBridge

            bridge = HermesQuantBridge()
            portfolio = await bridge.get_portfolio_status()
            overview["hermes_quant"] = portfolio
        except Exception:
            overview["hermes_quant"] = {"status": "unavailable"}

        # Organism data
        try:
            from ai_multicolony.integrations.organism_bridge import OrganismBridge
            import os

            bridge = OrganismBridge(
                supabase_url=os.getenv("SUPABASE_URL", ""),
                supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            )
            available = await bridge.is_available()
            overview["autonomous_organism"] = {"available": available}
            await bridge.close()
        except Exception:
            overview["autonomous_organism"] = {"status": "unavailable"}

        return overview

    return router
