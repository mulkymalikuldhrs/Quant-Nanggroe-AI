"""Geopolitical Tool — Geopolitical Analysis for Trading Intelligence.

Provides analysis frameworks for understanding geopolitical risks
and their impact on financial markets, based on three major frameworks:

1. **WorldOrder** — Analyzes the current global order, hegemony transitions,
   and multipolarity dynamics that drive macro risk.
2. **GrandChessboard** — Strategic framework based on Brzezinski's analysis
   of Eurasian geopolitics and great power competition.
3. **PrisonersOfGeography** — Geographic constraints framework based on
   Tim Marshall's analysis of how geography shapes national behavior.

Also provides sanctions and trade policy impact scoring.

References
----------
- Brzezinski, Z. "The Grand Chessboard" (1997)
- Marshall, T. "Prisoners of Geography" (2015)
- FinceptTerminal GeopoliticsAgents framework
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GeopoliticalRiskLevel(str, Enum):
    """Geopolitical risk classification."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    ELEVATED = "ELEVATED"
    MODERATE = "MODERATE"
    LOW = "LOW"
    MINIMAL = "MINIMAL"


class ImpactDirection(str, Enum):
    """Direction of geopolitical impact on markets."""
    STRONGLY_BEARISH = "STRONGLY_BEARISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    BULLISH = "BULLISH"
    STRONGLY_BULLISH = "STRONGLY_BULLISH"


class SanctionType(str, Enum):
    """Types of sanctions."""
    TRADE_EMBARGO = "TRADE_EMBARGO"
    FINANCIAL = "FINANCIAL"
    TECHNOLOGY = "TECHNOLOGY"
    ENERGY = "ENERGY"
    INDIVIDUAL = "INDIVIDUAL"
    SECTORAL = "SECTORAL"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class WorldOrderAnalysis(BaseModel):
    """World Order analysis result."""
    hegemon: str = Field("US", description="Current hegemon")
    transition_risk: float = Field(0.0, description="Hegemony transition risk (0-1)")
    multipolarity_index: float = Field(0.0, description="Degree of multipolarity (0-1)")
    trade_system_stability: float = Field(0.5, description="Trade system stability (0-1)")
    financial_system_stability: float = Field(0.5, description="Financial system stability (0-1)")
    alliance_shifts: List[str] = Field(default_factory=list, description="Major alliance shifts")
    flashpoints: List[str] = Field(default_factory=list, description="Current geopolitical flashpoints")
    market_impact: str = Field("NEUTRAL", description="Net market impact direction")
    risk_level: GeopoliticalRiskLevel = Field(GeopoliticalRiskLevel.MODERATE)
    timestamp: str = Field("")


class GrandChessboardAnalysis(BaseModel):
    """Grand Chessboard strategic analysis result."""
    region: str = Field(..., description="Analyzed region")
    geostrategic_value: float = Field(0.5, description="Geostrategic value (0-1)")
    great_power_competition: float = Field(0.0, description="Great power competition level (0-1)")
    resource_control: float = Field(0.0, description="Resource control significance (0-1)")
    trade_route_importance: float = Field(0.0, description="Trade route importance (0-1)")
    military_presence: float = Field(0.0, description="Military presence level (0-1)")
    key_players: List[str] = Field(default_factory=list, description="Key geopolitical players")
    strategic_imperatives: List[str] = Field(default_factory=list, description="Strategic imperatives")
    market_implications: List[str] = Field(default_factory=list, description="Market implications")
    risk_level: GeopoliticalRiskLevel = Field(GeopoliticalRiskLevel.MODERATE)
    timestamp: str = Field("")


class GeographyConstraint(BaseModel):
    """Geographic constraint analysis for a region."""
    region: str = Field(..., description="Region name")
    constraint: str = Field("", description="Primary geographic constraint")
    strategic_imperative: str = Field("", description="Strategic imperative from geography")
    current_implications: str = Field("", description="Current market/trade implications")
    historical_vulnerability: str = Field("", description="Historical vulnerability")


class PrisonersOfGeographyAnalysis(BaseModel):
    """Prisoners of Geography analysis result."""
    region: str = Field(..., description="Analyzed region")
    constraints: List[GeographyConstraint] = Field(default_factory=list)
    trade_impact: float = Field(0.0, description="Impact on trade routes (0-1)")
    commodity_impact: float = Field(0.0, description="Impact on commodity prices (0-1)")
    security_risk: float = Field(0.0, description="Security risk level (0-1)")
    affected_markets: List[str] = Field(default_factory=list, description="Affected markets/assets")
    risk_level: GeopoliticalRiskLevel = Field(GeopoliticalRiskLevel.MODERATE)
    timestamp: str = Field("")


class SanctionImpact(BaseModel):
    """Sanctions and trade policy impact scoring."""
    target_country: str = Field(..., description="Sanctioned/target country")
    sanction_types: List[SanctionType] = Field(default_factory=list)
    impact_score: float = Field(0.0, description="Overall impact score (0-1)")
    trade_disruption: float = Field(0.0, description="Trade disruption level (0-1)")
    commodity_impact: float = Field(0.0, description="Commodity market impact (0-1)")
    currency_impact: float = Field(0.0, description="Currency market impact (0-1)")
    affected_sectors: List[str] = Field(default_factory=list)
    affected_commodities: List[str] = Field(default_factory=list)
    supply_chain_risk: float = Field(0.0, description="Supply chain disruption risk (0-1)")
    market_direction: ImpactDirection = Field(ImpactDirection.NEUTRAL)
    confidence: float = Field(0.1, description="Confidence level (0-1)")
    timestamp: str = Field("")


# ---------------------------------------------------------------------------
# Geographic constraint database
# ---------------------------------------------------------------------------

_GEOGRAPHY_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "russia": {
        "constraints": [
            GeographyConstraint(
                region="russia",
                constraint="North European Plain vulnerability",
                strategic_imperative="Buffer state creation",
                current_implications="Ukraine conflict, Baltic tensions",
                historical_vulnerability="Napoleon, Hitler, NATO expansion",
            ),
            GeographyConstraint(
                region="russia",
                constraint="Warm-water port obsession",
                strategic_imperative="Year-round naval presence",
                current_implications="Crimea annexation, Syria presence",
                historical_vulnerability="Black Sea, Baltic, Pacific access",
            ),
        ],
        "trade_impact": 0.7,
        "commodity_impact": 0.8,
        "security_risk": 0.8,
        "affected_markets": ["OIL", "GAS", "WHEAT", "RUB", "EUR"],
    },
    "china": {
        "constraints": [
            GeographyConstraint(
                region="china",
                constraint="First Island Chain containment",
                strategic_imperative="Break island chain, control SCS",
                current_implications="South China Sea, Taiwan tensions",
                historical_vulnerability="Maritime access limited by US allies",
            ),
            GeographyConstraint(
                region="china",
                constraint="Resource import dependence",
                strategic_imperative="Secure supply chains (BRI)",
                current_implications="Energy security, rare earth dominance",
                historical_vulnerability="Malacca Strait chokepoint",
            ),
        ],
        "trade_impact": 0.9,
        "commodity_impact": 0.7,
        "security_risk": 0.7,
        "affected_markets": ["SEMIS", "RARE_EARTH", "OIL", "CNY", "HK"],
    },
    "middle_east": {
        "constraints": [
            GeographyConstraint(
                region="middle_east",
                constraint="Oil resource geography",
                strategic_imperative="Control energy supplies",
                current_implications="OPEC+ dynamics, Hormuz Strait",
                historical_vulnerability="Oil embargoes, Gulf Wars",
            ),
        ],
        "trade_impact": 0.8,
        "commodity_impact": 0.9,
        "security_risk": 0.9,
        "affected_markets": ["OIL", "GAS", "GOLD", "USD", "EM_BONDS"],
    },
    "usa": {
        "constraints": [
            GeographyConstraint(
                region="usa",
                constraint="Ocean-protected continental power",
                strategic_imperative="Maintain naval supremacy",
                current_implications="Indo-Pacific strategy, NATO",
                historical_vulnerability="Pearl Harbor, 9/11",
            ),
        ],
        "trade_impact": 0.3,
        "commodity_impact": 0.4,
        "security_risk": 0.2,
        "affected_markets": ["USD", "TREASURIES", "EQUITIES", "OIL"],
    },
    "europe": {
        "constraints": [
            GeographyConstraint(
                region="europe",
                constraint="North European Plain vulnerability",
                strategic_imperative="EU/NATO integration",
                current_implications="Ukraine war, energy dependence",
                historical_vulnerability="Two World Wars",
            ),
        ],
        "trade_impact": 0.6,
        "commodity_impact": 0.5,
        "security_risk": 0.5,
        "affected_markets": ["EUR", "GAS", "DEFENSE", "EUR_BONDS"],
    },
}

# Grand Chessboard regions
_CHESSBOARD_REGIONS: Dict[str, Dict[str, Any]] = {
    "central_asia": {
        "geostrategic_value": 0.8,
        "great_power_competition": 0.9,
        "resource_control": 0.8,
        "trade_route_importance": 0.9,
        "key_players": ["China", "Russia", "US", "Iran", "Turkey"],
        "imperatives": ["BRI connectivity", "Energy transit", "Great game competition"],
        "market_implications": ["Energy prices", "BRI infrastructure", "CNY internationalization"],
    },
    "indo_pacific": {
        "geostrategic_value": 0.9,
        "great_power_competition": 0.9,
        "resource_control": 0.6,
        "trade_route_importance": 0.9,
        "key_players": ["US", "China", "Japan", "India", "Australia"],
        "imperatives": ["Maritime dominance", "Supply chain control", "Tech competition"],
        "market_implications": ["Semiconductor supply", "Trade route disruption", "FX volatility"],
    },
    "middle_east": {
        "geostrategic_value": 0.9,
        "great_power_competition": 0.7,
        "resource_control": 0.9,
        "trade_route_importance": 0.7,
        "key_players": ["US", "Saudi Arabia", "Iran", "Russia", "China"],
        "imperatives": ["Energy security", "Religious politics", "Proxy conflicts"],
        "market_implications": ["Oil prices", "Defense spending", "Sovereign wealth flows"],
    },
}

# Sanctions database (simplified)
_SANCTIONS_DB: Dict[str, Dict[str, Any]] = {
    "russia": {
        "sanction_types": [SanctionType.FINANCIAL, SanctionType.ENERGY, SanctionType.TECHNOLOGY],
        "impact_score": 0.8,
        "trade_disruption": 0.7,
        "commodity_impact": 0.9,
        "currency_impact": 0.6,
        "affected_sectors": ["energy", "banking", "technology", "defense"],
        "affected_commodities": ["oil", "gas", "wheat", "palladium", "nickel"],
        "supply_chain_risk": 0.7,
    },
    "iran": {
        "sanction_types": [SanctionType.TRADE_EMBARGO, SanctionType.FINANCIAL, SanctionType.ENERGY],
        "impact_score": 0.7,
        "trade_disruption": 0.6,
        "commodity_impact": 0.6,
        "currency_impact": 0.3,
        "affected_sectors": ["energy", "banking", "shipping"],
        "affected_commodities": ["oil", "gas"],
        "supply_chain_risk": 0.4,
    },
}


# ---------------------------------------------------------------------------
# Geopolitical Tool
# ---------------------------------------------------------------------------

class GeopoliticalTool:
    """Geopolitical analysis tool for agent consumption.

    Provides three major analysis frameworks:
    - World Order analysis (hegemony transitions, global stability)
    - Grand Chessboard analysis (regional strategic competition)
    - Prisoners of Geography analysis (geographic constraints)

    Also provides sanctions and trade policy impact scoring.

    Usage::

        tool = GeopoliticalTool()
        world = await tool.analyze_world_order()
        chessboard = await tool.analyze_grand_chessboard("indo_pacific")
        geography = await tool.analyze_geography("russia")
    """

    def __init__(self, cache_ttl: int = 7200) -> None:
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl = cache_ttl

    async def analyze_world_order(self) -> WorldOrderAnalysis:
        """Analyze the current world order and transition risks.

        Returns:
            WorldOrderAnalysis with global order assessment.
        """
        # Simplified analysis - in production, use LLM or data providers
        return WorldOrderAnalysis(
            hegemon="US",
            transition_risk=0.4,
            multipolarity_index=0.6,
            trade_system_stability=0.4,
            financial_system_stability=0.5,
            alliance_shifts=[
                "BRICS expansion",
                "China-Russia alignment",
                "India multi-alignment",
                "Global South agency",
            ],
            flashpoints=[
                "Taiwan Strait",
                "Ukraine-Russia",
                "Middle East escalation",
                "Red Sea/Houthi disruption",
            ],
            market_impact="ELEVATED_VOLATILITY",
            risk_level=GeopoliticalRiskLevel.ELEVATED,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    async def analyze_grand_chessboard(
        self,
        region: str,
    ) -> GrandChessboardAnalysis:
        """Analyze a region through the Grand Chessboard framework.

        Args:
            region: Region identifier (central_asia, indo_pacific, middle_east).

        Returns:
            GrandChessboardAnalysis with strategic assessment.
        """
        key = region.lower().replace(" ", "_")
        data = _CHESSBOARD_REGIONS.get(key, {})

        if not data:
            return GrandChessboardAnalysis(
                region=region,
                risk_level=GeopoliticalRiskLevel.MODERATE,
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )

        risk = GeopoliticalRiskLevel.ELEVATED if data["great_power_competition"] > 0.7 else GeopoliticalRiskLevel.MODERATE

        return GrandChessboardAnalysis(
            region=region,
            geostrategic_value=data["geostrategic_value"],
            great_power_competition=data["great_power_competition"],
            resource_control=data["resource_control"],
            trade_route_importance=data["trade_route_importance"],
            military_presence=data.get("great_power_competition", 0.0) * 0.8,
            key_players=data["key_players"],
            strategic_imperatives=data["imperatives"],
            market_implications=data["market_implications"],
            risk_level=risk,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    async def analyze_geography(
        self,
        region: str,
    ) -> PrisonersOfGeographyAnalysis:
        """Analyze a region through the Prisoners of Geography framework.

        Args:
            region: Region identifier (russia, china, middle_east, usa, europe).

        Returns:
            PrisonersOfGeographyAnalysis with geographic constraint assessment.
        """
        key = region.lower().replace(" ", "_")
        data = _GEOGRAPHY_CONSTRAINTS.get(key, {})

        if not data:
            return PrisonersOfGeographyAnalysis(
                region=region,
                risk_level=GeopoliticalRiskLevel.MODERATE,
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )

        risk = GeopoliticalRiskLevel.HIGH if data["security_risk"] > 0.7 else GeopoliticalRiskLevel.MODERATE

        return PrisonersOfGeographyAnalysis(
            region=region,
            constraints=data.get("constraints", []),
            trade_impact=data.get("trade_impact", 0.0),
            commodity_impact=data.get("commodity_impact", 0.0),
            security_risk=data.get("security_risk", 0.0),
            affected_markets=data.get("affected_markets", []),
            risk_level=risk,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    async def analyze_sanctions(
        self,
        target_country: str,
    ) -> SanctionImpact:
        """Analyze sanctions and trade policy impact.

        Args:
            target_country: Country subject to sanctions.

        Returns:
            SanctionImpact with impact scoring.
        """
        key = target_country.lower().replace(" ", "_")
        data = _SANCTIONS_DB.get(key, {})

        if not data:
            return SanctionImpact(
                target_country=target_country,
                confidence=0.1,
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )

        # Determine market direction
        direction = ImpactDirection.BEARISH
        if data["impact_score"] > 0.7:
            direction = ImpactDirection.STRONGLY_BEARISH
        elif data["commodity_impact"] > 0.7:
            direction = ImpactDirection.BEARISH
            # Some commodities may rally (bullish for commodity holders)

        return SanctionImpact(
            target_country=target_country,
            sanction_types=data["sanction_types"],
            impact_score=data["impact_score"],
            trade_disruption=data["trade_disruption"],
            commodity_impact=data["commodity_impact"],
            currency_impact=data["currency_impact"],
            affected_sectors=data["affected_sectors"],
            affected_commodities=data["affected_commodities"],
            supply_chain_risk=data["supply_chain_risk"],
            market_direction=direction,
            confidence=0.6,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    async def comprehensive_analysis(
        self,
        region: str,
    ) -> Dict[str, Any]:
        """Run comprehensive geopolitical analysis combining all frameworks.

        Args:
            region: Region or country to analyze.

        Returns:
            Dict with combined analysis from all frameworks.
        """
        world = await self.analyze_world_order()
        chessboard = await self.analyze_grand_chessboard(region)
        geography = await self.analyze_geography(region)
        sanctions = await self.analyze_sanctions(region)

        # Composite risk score
        composite_risk = max(
            world.transition_risk,
            chessboard.great_power_competition,
            geography.security_risk,
            sanctions.impact_score,
        )

        return {
            "region": region,
            "composite_risk_score": round(composite_risk, 4),
            "world_order": world.model_dump(),
            "grand_chessboard": chessboard.model_dump(),
            "prisoners_of_geography": geography.model_dump(),
            "sanctions": sanctions.model_dump(),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Singleton and LangChain @tool
# ---------------------------------------------------------------------------

_default_geo_tool: GeopoliticalTool | None = None


def _get_default_geo_tool() -> GeopoliticalTool:
    global _default_geo_tool
    if _default_geo_tool is None:
        _default_geo_tool = GeopoliticalTool()
    return _default_geo_tool


@tool
async def analyze_geopolitical(region: str) -> str:
    """Analyze geopolitical risks and their market impact for a region.

    Uses World Order, Grand Chessboard, and Prisoners of Geography
    frameworks to assess geopolitical risks and their impact on
    financial markets. Also includes sanctions and trade policy analysis.

    Args:
        region: Region or country to analyze (e.g., 'russia', 'china',
                'middle_east', 'indo_pacific', 'central_asia')

    Returns:
        JSON string with comprehensive geopolitical analysis including
        composite risk score, world order assessment, strategic competition,
        geographic constraints, and sanctions impact.
    """
    try:
        gt = _get_default_geo_tool()
        result = await gt.comprehensive_analysis(region)
        return json.dumps(result, indent=2, default=str)
    except Exception as exc:
        logger.error("analyze_geopolitical tool error: %s", exc)
        return json.dumps({"error": f"Geopolitical analysis failed: {exc}", "region": region})


__all__ = [
    "GeopoliticalTool",
    "GeopoliticalRiskLevel",
    "ImpactDirection",
    "SanctionType",
    "WorldOrderAnalysis",
    "GrandChessboardAnalysis",
    "PrisonersOfGeographyAnalysis",
    "GeographyConstraint",
    "SanctionImpact",
    "analyze_geopolitical",
]
