"""Screener Orchestrator — Combines all screener engines.

Runs all screener component engines and produces a composite
screening result with overall score, direction, and breakdown.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult
from quant_nanggroe.engine.screener.monetary_fundamental import MonetaryFundamentalEngine
from quant_nanggroe.engine.screener.intermarket import IntermarketEngine
from quant_nanggroe.engine.screener.macro_analysis import MacroAnalysisEngine
from quant_nanggroe.engine.screener.market_structure import MarketStructureEngine
from quant_nanggroe.engine.screener.positioning_crowd import PositioningCrowdEngine
from quant_nanggroe.engine.screener.quant_scoring import QuantScoringEngine
from quant_nanggroe.engine.screener.dex_intelligence import DexIntelligenceEngine
from quant_nanggroe.engine.screener.liquidity_orderflow import LiquidityOrderflowEngine

logger = logging.getLogger(__name__)

# Default weights for each engine
DEFAULT_WEIGHTS = {
    "monetary_fundamental": 0.15,
    "intermarket": 0.12,
    "macro_analysis": 0.15,
    "market_structure": 0.15,
    "positioning_crowd": 0.10,
    "quant_scoring": 0.13,
    "dex_intelligence": 0.10,
    "liquidity_orderflow": 0.10,
}


class ScreenerOrchestrator:
    """Screener Orchestrator.

    Combines all screener engines, runs them in sequence,
    and produces a composite screening result.

    Features:
    - Runs all engines and aggregates results
    - Configurable weights per engine
    - Overall direction and score
    - Detailed breakdown per engine
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        enabled_engines: Optional[List[str]] = None,
    ) -> None:
        """Initialize orchestrator.

        Args:
            weights: Custom weights per engine. Defaults to DEFAULT_WEIGHTS.
            enabled_engines: List of engine names to enable. None = all.
        """
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        self._engines: Dict[str, ScreenerComponent] = {
            "monetary_fundamental": MonetaryFundamentalEngine(),
            "intermarket": IntermarketEngine(),
            "macro_analysis": MacroAnalysisEngine(),
            "market_structure": MarketStructureEngine(),
            "positioning_crowd": PositioningCrowdEngine(),
            "quant_scoring": QuantScoringEngine(),
            "dex_intelligence": DexIntelligenceEngine(),
            "liquidity_orderflow": LiquidityOrderflowEngine(),
        }

        # Filter enabled engines
        if enabled_engines is not None:
            self._engines = {
                k: v for k, v in self._engines.items() if k in enabled_engines
            }

    def screen(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all screener engines and produce composite result.

        Args:
            data: Dict with market data for all engines.

        Returns:
            Dict with composite score, direction, and per-engine results.
        """
        results: Dict[str, ScreenerResult] = {}

        for name, engine in self._engines.items():
            try:
                result = engine.analyze(data)
                results[name] = result
            except Exception as exc:
                logger.warning("Engine %s failed: %s", name, exc)
                results[name] = ScreenerResult(
                    component_name=name,
                    direction=ScreenerDirection.NEUTRAL,
                    score=0.0,
                    confidence=0.0,
                    status="error",
                    message=str(exc),
                )

        # Calculate composite score
        total_weight = 0.0
        weighted_score = 0.0

        for name, result in results.items():
            weight = self._weights.get(name, 0.1)
            if result.status == "configured" or result.status == "not_configured":
                if result.status == "configured":
                    weighted_score += result.score * weight * result.confidence
                    total_weight += weight * result.confidence
                # Skip not_configured engines

        composite_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # Determine overall direction
        if composite_score > 0.2:
            overall_direction = ScreenerDirection.BULLISH
        elif composite_score < -0.2:
            overall_direction = ScreenerDirection.BEARISH
        else:
            overall_direction = ScreenerDirection.NEUTRAL

        # Calculate overall confidence
        configured_count = sum(1 for r in results.values() if r.status == "configured")
        avg_confidence = (
            sum(r.confidence for r in results.values() if r.status == "configured")
            / configured_count
            if configured_count > 0
            else 0.0
        )

        # Direction agreement
        directions = [r.direction for r in results.values() if r.status == "configured"]
        bullish_count = sum(1 for d in directions if d == ScreenerDirection.BULLISH)
        bearish_count = sum(1 for d in directions if d == ScreenerDirection.BEARISH)
        neutral_count = sum(1 for d in directions if d == ScreenerDirection.NEUTRAL)

        return {
            "composite_score": composite_score,
            "overall_direction": overall_direction.value,
            "overall_confidence": avg_confidence,
            "engine_results": {name: result.model_dump() for name, result in results.items()},
            "direction_breakdown": {
                "bullish": bullish_count,
                "bearish": bearish_count,
                "neutral": neutral_count,
            },
            "configured_engines": configured_count,
            "total_engines": len(self._engines),
        }

    def configure_engine(self, name: str, **kwargs: Any) -> bool:
        """Configure a specific engine.

        Args:
            name: Engine name.
            **kwargs: Configuration parameters.

        Returns:
            True if engine was found and configured.
        """
        engine = self._engines.get(name)
        if engine is None:
            return False
        engine.configure(**kwargs)
        return True

    def list_engines(self) -> List[str]:
        """List all available engine names."""
        return sorted(self._engines.keys())

    def get_engine(self, name: str) -> Optional[ScreenerComponent]:
        """Get a specific engine by name."""
        return self._engines.get(name)
