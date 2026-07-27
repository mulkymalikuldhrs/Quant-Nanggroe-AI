"""
Causal Bias Engine — Event-driven directional bias computation for QNA.

Maps macroeconomic and geopolitical events to directional biases across
global asset classes. Implements the Causal Knowledge Graph (CKG) approach:

    Tuple = ⟨Cause Event, Effect Variable, Direction, Impact Magnitude⟩

Reference:
    - Lopez de Prado (2018): "Advances in Financial Machine Learning"
    - Peters et al. (arXiv:1712.04918): "Elements of Causal Inference"
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Type alias for CKG tuples: (Cause, Effect, Direction, Magnitude)
CKGTuple = Tuple[str, str, str, float]


class CausalKnowledgeGraph:
    """
    Causal Knowledge Graph — maps events to asset-level directional impacts.

    Maintains a directed graph where edges represent causal relationships
    between macroeconomic events and asset price impacts.

    Edge weights (impact magnitude) are in range [0.0, 1.0].
    """

    # Default causal rules: event_type → [(affected_asset, direction, magnitude)]
    DEFAULT_RULES: Dict[str, List[Tuple[str, str, float]]] = {
        "GEOPOLITICAL_SUPPLY_SHOCK": [
            ("GC1!", "bullish", 0.9),   # Gold safe-haven demand
            ("SI1!", "bullish", 0.6),    # Silver follows gold
            ("ES1!", "bearish", 0.8),   # Equities risk-off
            ("NQ1!", "bearish", 0.7),   # Nasdaq risk-off
            ("YM1!", "bearish", 0.6),   # Dow risk-off
            ("DXY", "bullish", 0.6),    # USD cash inflow
            ("ZB1!", "bullish", 0.7),   # Bond safe-haven
            ("ZN1!", "bullish", 0.6),   # 10Y note safe-haven
            ("6E1!", "bearish", 0.5),   # EUR weakness
            ("6B1!", "bearish", 0.4),   # GBP weakness
            ("6J1!", "bullish", 0.3),   # JPY safe-haven
            ("BTC1!", "bearish", 0.5),  # Crypto risk-off
            ("CL1!", "bullish", 0.9),   # Crude oil supply shock
        ],
        "INFLATION_SURPRISE": [
            ("DXY", "bullish", 0.9),    # USD strengthens
            ("ES1!", "bearish", 0.7),   # Equities sell-off
            ("NQ1!", "bearish", 0.8),   # Growth stocks hit hardest
            ("GC1!", "neutral", 0.3),   # Gold mixed (real rates vs inflation hedge)
            ("ZB1!", "bearish", 0.8),   # Bonds sell off
            ("ZN1!", "bearish", 0.7),   # 10Y note sell off
            ("6E1!", "bearish", 0.6),   # EUR weakness
            ("6J1!", "neutral", 0.2),   # JPY mixed
            ("BTC1!", "bearish", 0.4),  # Crypto mixed
        ],
        "RATE_CUT": [
            ("DXY", "bearish", 0.7),    # USD weakens
            ("ES1!", "bullish", 0.7),   # Equities rally
            ("NQ1!", "bullish", 0.8),   # Tech rally
            ("GC1!", "bullish", 0.5),   # Gold rises (lower opportunity cost)
            ("ZB1!", "bullish", 0.6),   # Bonds rally
            ("BTC1!", "bullish", 0.6),  # Crypto rally
        ],
        "RATE_HIKE": [
            ("DXY", "bullish", 0.8),    # USD strengthens
            ("ES1!", "bearish", 0.7),   # Equities sell-off
            ("NQ1!", "bearish", 0.8),   # Tech sell-off
            ("GC1!", "bearish", 0.5),   # Gold falls
            ("ZB1!", "bearish", 0.7),   # Bonds sell-off
            ("BTC1!", "bearish", 0.5),  # Crypto sell-off
        ],
        "RISK_ON_MOMENTUM": [
            ("ES1!", "bullish", 0.6),   # S&P momentum
            ("NQ1!", "bullish", 0.7),   # Nasdaq momentum
            ("GC1!", "neutral", 0.2),   # Gold flat/weak
            ("DXY", "neutral", 0.1),   # USD mixed
            ("ZB1!", "bearish", 0.4),   # Bonds sell-off
            ("6A1!", "bullish", 0.5),   # AUD risk proxy
            ("6N1!", "bullish", 0.5),   # NZD risk proxy
            ("BTC1!", "bullish", 0.6),  # Crypto momentum
        ],
        "RISK_OFF_CRISIS": [
            ("GC1!", "bullish", 0.9),   # Gold safe-haven
            ("DXY", "bullish", 0.7),    # USD safe-haven
            ("ZB1!", "bullish", 0.8),   # Bond safe-haven
            ("ES1!", "bearish", 0.9),   # Equities crash
            ("NQ1!", "bearish", 0.9),   # Nasdaq crash
            ("6E1!", "bearish", 0.6),   # EUR weakness
            ("6A1!", "bearish", 0.6),   # AUD weakness
            ("BTC1!", "bearish", 0.7),  # Crypto crash
        ],
    }

    def __init__(self):
        self.rules: Dict[str, List[Tuple[str, str, float]]] = dict(
            self.DEFAULT_RULES
        )
        self._history: List[CKGTuple] = []

    def add_rule(
        self,
        event_type: str,
        asset: str,
        direction: str,
        magnitude: float,
    ) -> None:
        """Add a custom causal rule."""
        if event_type not in self.rules:
            self.rules[event_type] = []
        self.rules[event_type].append((asset, direction, magnitude))

    def get_impact(
        self,
        event_type: str,
        asset: str,
    ) -> Tuple[str, float]:
        """
        Get the directional impact for an asset given an event type.

        Returns:
            (direction, magnitude) tuple. Direction is 'bullish', 'bearish', or 'neutral'.
            Magnitude is in [0.0, 1.0].
        """
        rules = self.rules.get(event_type, [])
        for target_asset, direction, magnitude in rules:
            if target_asset == asset:
                return direction, magnitude
        return "neutral", 0.0

    def record_event(
        self,
        cause: str,
        effect: str,
        direction: str,
        magnitude: float,
    ) -> None:
        """Record a causal event tuple in history."""
        self._history.append((cause, effect, direction, magnitude))

    @property
    def history(self) -> List[CKGTuple]:
        """Get all recorded causal events."""
        return self._history.copy()


class CausalBiasEngine:
    """
    Causal bias engine — evaluates event-driven directional biases.

    Uses CausalKnowledgeGraph to map events to asset biases and
    applies scaling based on event severity and market conditions.
    """

    def __init__(self, knowledge_graph: Optional[CausalKnowledgeGraph] = None):
        self._kg = knowledge_graph or CausalKnowledgeGraph()

    @property
    def knowledge_graph(self) -> CausalKnowledgeGraph:
        return self._kg

    def evaluate_causal_bias(
        self,
        event_type: str,
        msi_score: float = 0.0,
        geopolitical_risk_delta: float = 0.0,
    ) -> Dict[str, float]:
        """
        Evaluate directional biases for ALL tracked assets.

        Args:
            event_type: Macro event type (e.g. GEOPOLITICAL_SUPPLY_SHOCK).
            msi_score: Macro Surprise Index score for scaling.
            geopolitical_risk_delta: Geopolitical risk delta (0-100).

        Returns:
            Dict of {asset: bias_score} where bias ∈ [-1.0, +1.0].
            Positive = bullish, Negative = bearish, Zero = neutral.
        """
        rules = self._kg.rules.get(event_type, [])
        if not rules:
            logger.debug("No causal rules found for event: %s", event_type)
            return {}

        # Compute event severity multiplier
        severity = self._compute_severity(
            event_type=event_type,
            msi_score=msi_score,
            geopolitical_risk_delta=geopolitical_risk_delta,
        )

        biases: Dict[str, float] = {}
        for asset, direction, base_magnitude in rules:
            # Scale magnitude by severity
            scaled = base_magnitude * severity

            # Apply direction
            if direction == "bullish":
                biases[asset] = round(+scaled, 4)
            elif direction == "bearish":
                biases[asset] = round(-scaled, 4)
            else:
                biases[asset] = round(scaled * 0.1, 4)  # near-neutral

            # Clamp to [-1.0, 1.0]
            biases[asset] = max(-1.0, min(1.0, biases[asset]))

        # Record in knowledge graph history
        for asset, bias in biases.items():
            direction = "bullish" if bias > 0 else "bearish" if bias < 0 else "neutral"
            self._kg.record_event(event_type, asset, direction, abs(bias))

        return biases

    def _compute_severity(
        self,
        event_type: str,
        msi_score: float,
        geopolitical_risk_delta: float,
    ) -> float:
        """
        Compute event severity multiplier based on event type and market data.

        Returns a multiplier in [0.3, 1.0] that scales the base impact magnitude.
        """
        base = 1.0

        # Adjust for geopolitical risk
        if "SUPPLY_SHOCK" in event_type or "CRISIS" in event_type:
            gpr_factor = np.clip(geopolitical_risk_delta / 100.0, 0.0, 1.0)
            base *= max(0.5, gpr_factor)

        # Adjust for macro surprise magnitude
        if abs(msi_score) > 0:
            msi_factor = np.clip(abs(msi_score) / 3.0, 0.0, 1.0)
            base *= max(0.5, msi_factor)

        return float(np.clip(base, 0.3, 1.0))


__all__ = [
    "CausalKnowledgeGraph",
    "CausalBiasEngine",
]
