"""
Query Router — adapted from agenticSeek agent routing system.

Provides:
  - Rule-based query classification for trading/finance domain
  - Complexity estimation (simple vs multi-step)
  - Agent selection based on query intent
  - Extensible classifier interface for ML-based routing

Adapted from agenticSeek/sources/router.py with:
  - Trading/finance domain instead of general-purpose coding
  - No torch/transformers dependency (rule-based with optional ML extension)
  - quant_nanggroe_ai.* import paths
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and data models
# ---------------------------------------------------------------------------

class AgentRole(str, Enum):
    """Available agent roles in the trading system."""
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    STRATEGIST = "strategist"
    RISK_MANAGER = "risk_manager"
    TRADER = "trader"
    PORTFOLIO = "portfolio"
    MACRO = "macro"
    FOREX = "forex"
    CRYPTO = "crypto"
    CASUAL = "casual"


class QueryComplexity(str, Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    agent_role: AgentRole
    complexity: QueryComplexity
    confidence: float
    reasoning: str
    secondary_agents: List[AgentRole] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Keyword rule definitions
# ---------------------------------------------------------------------------

# Trading domain keyword patterns → agent roles
_ROLE_PATTERNS: Dict[AgentRole, List[str]] = {
    AgentRole.RESEARCHER: [
        r"\b(research|find|search|look up|investigate|explore|analyze data)\b",
        r"\b(news|article|report|paper|publication)\b",
        r"\b(what is|tell me about|explain)\b",
    ],
    AgentRole.ANALYST: [
        r"\b(analy[zs]e|analysis|technical|fundamental|indicator|chart pattern)\b",
        r"\b(moving average|rsi|macd|bollinger|support|resistance)\b",
        r"\b(volume|trend|momentum|oscillator)\b",
    ],
    AgentRole.STRATEGIST: [
        r"\b(strategy|strateg|plan|approach|method|system)\b",
        r"\b(backtest|optimize|signal|entry|exit)\b",
        r"\b(algo|algorithmic|automated)\b",
    ],
    AgentRole.RISK_MANAGER: [
        r"\b(risk|exposure|drawdown|stop.loss|position.size)\b",
        r"\b(var|cvar|sharpe|sortino|max.drawdown)\b",
        r"\b(hedge|protect|limit|cap)\b",
    ],
    AgentRole.TRADER: [
        r"\b(trade|buy|sell|order|execute|fill)\b",
        r"\b(limit.order|market.order|stop.order)\b",
        r"\b(open|close|position|entry|exit)\b",
    ],
    AgentRole.PORTFOLIO: [
        r"\b(portfolio|allocation|diversif|rebalanc|weight)\b",
        r"\b(asset.class|correlation|optimization)\b",
        r"\b(holdings|basket|bundle)\b",
    ],
    AgentRole.MACRO: [
        r"\b(macro|economy|gdp|inflation|interest.rate|fed|central.bank)\b",
        r"\b(employment|cpi|pmi|yield|bond|treasury)\b",
        r"\b(geopolit|sanction|tariff|trade.war)\b",
    ],
    AgentRole.FOREX: [
        r"\b(forex|fx|currency|exchange.rate|pair)\b",
        r"\b(eur.usd|gbp.usd|usd.jpy|usd.chf|aud.usd)\b",
        r"\b(pip|lot|spread|swap|carry)\b",
    ],
    AgentRole.CRYPTO: [
        r"\b(crypto|bitcoin|btc|ethereum|eth|solana|sol|defi)\b",
        r"\b(token|coin|blockchain|dex|nft|web3)\b",
        r"\b(wallet|staking|yield|liquidity|amm)\b",
    ],
}

# Complexity patterns
_COMPLEX_PATTERNS: Dict[QueryComplexity, List[str]] = {
    QueryComplexity.COMPLEX: [
        r"\b(and then|followed by|after that|then use|multi.step|comprehensive)\b",
        r"\b(compare|contrast|correlat|cross.asset|intermarket)\b",
        r"\b(build|create|design|develop|implement|deploy)\b",
        r"\b(full|complete|entire|comprehensive|holistic|end.to.end)\b",
        r"\b(portfolio.*risk|risk.*portfolio|strategy.*backtest|backtest.*strategy)\b",
    ],
    QueryComplexity.MODERATE: [
        r"\b(analy[zs]e|evaluate|assess|compare|review)\b",
        r"\b(how does|what if|scenario|sensitiv|stress.test)\b",
        r"\b(recommend|suggest|advise|propose)\b",
    ],
}


# ---------------------------------------------------------------------------
# Query Router
# ---------------------------------------------------------------------------

class QueryRouter:
    """
    Routes user queries to appropriate trading agents.

    Uses keyword-based classification with configurable confidence thresholds.
    Supports optional ML-based classifier extension for improved accuracy.

    Adapted from agenticSeek AgentRouter which uses:
      - BART zero-shot classification
      - AdaptiveClassifier for LLM routing
      - Few-shot learning for task and complexity classification

    This version uses rule-based classification to avoid heavy ML dependencies
    while providing the same architectural pattern.
    """

    def __init__(
        self,
        available_roles: Optional[List[AgentRole]] = None,
        complexity_threshold: float = 0.5,
        ml_classifier: Optional[Callable[[str], Tuple[str, float]]] = None,
    ) -> None:
        """
        Args:
            available_roles: Roles available for routing. Defaults to all.
            complexity_threshold: Minimum confidence to classify as complex.
            ml_classifier: Optional callable(text) -> (label, confidence) for ML routing.
        """
        self.available_roles = available_roles or list(AgentRole)
        self.complexity_threshold = complexity_threshold
        self.ml_classifier = ml_classifier
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._role_compiled: Dict[AgentRole, List[re.Pattern]] = {}
        for role, patterns in _ROLE_PATTERNS.items():
            if role in self.available_roles:
                self._role_compiled[role] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]

        self._complexity_compiled: Dict[QueryComplexity, List[re.Pattern]] = {}
        for level, patterns in _COMPLEX_PATTERNS.items():
            self._complexity_compiled[level] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def route(self, query: str) -> RoutingDecision:
        """
        Route a query to the most appropriate agent.

        Args:
            query: Natural language query from user.

        Returns:
            RoutingDecision with selected agent, complexity, and reasoning.
        """
        # Step 1: Estimate complexity
        complexity = self._estimate_complexity(query)

        # Step 2: If ML classifier available and high confidence, use it
        if self.ml_classifier is not None:
            try:
                ml_label, ml_confidence = self.ml_classifier(query)
                if ml_confidence > 0.7:
                    try:
                        role = AgentRole(ml_label)
                        if role in self.available_roles:
                            return RoutingDecision(
                                agent_role=role,
                                complexity=complexity,
                                confidence=ml_confidence,
                                reasoning=f"ML classifier (confidence={ml_confidence:.2f})",
                            )
                    except ValueError:
                        pass  # Fall through to rule-based
            except Exception as e:
                logger.warning(f"ML classifier failed: {e}")

        # Step 3: Rule-based classification
        scores = self._score_by_role(query)
        if not scores:
            return RoutingDecision(
                agent_role=AgentRole.CASUAL,
                complexity=complexity,
                confidence=0.0,
                reasoning="No matching patterns, defaulting to casual",
            )

        best_role, best_score = max(scores.items(), key=lambda x: x[1])
        secondary = [
            role for role, score in scores.items()
            if role != best_role and score > best_score * 0.5
        ][:2]  # Top 2 secondary agents

        reasoning = (
            f"Rule-based match (score={best_score:.2f}, "
            f"matched patterns={self._count_matches(query, best_role)})"
        )

        return RoutingDecision(
            agent_role=best_role,
            complexity=complexity,
            confidence=min(best_score / 3.0, 1.0),  # Normalize to 0-1
            reasoning=reasoning,
            secondary_agents=secondary,
        )

    def _score_by_role(self, query: str) -> Dict[AgentRole, float]:
        """Score query against each available role's patterns."""
        scores: Dict[AgentRole, float] = {}
        for role, compiled_patterns in self._role_compiled.items():
            score = 0.0
            for pattern in compiled_patterns:
                matches = pattern.findall(query)
                score += len(matches)
            if score > 0:
                scores[role] = score
        return scores

    def _count_matches(self, query: str, role: AgentRole) -> int:
        """Count total pattern matches for a role."""
        count = 0
        for pattern in self._role_compiled.get(role, []):
            count += len(pattern.findall(query))
        return count

    def _estimate_complexity(self, query: str) -> QueryComplexity:
        """
        Estimate query complexity.

        Adapted from agenticSeek's AdaptiveClassifier-based complexity estimation.
        Uses rule-based patterns as a lightweight alternative.
        """
        # Short queries are simple
        if len(query.strip()) <= 10:
            return QueryComplexity.SIMPLE

        # Check complex patterns first
        complex_score = 0
        for pattern in self._complexity_compiled.get(QueryComplexity.COMPLEX, []):
            complex_score += len(pattern.findall(query))

        if complex_score >= 2:
            return QueryComplexity.COMPLEX

        # Check moderate patterns
        moderate_score = 0
        for pattern in self._complexity_compiled.get(QueryComplexity.MODERATE, []):
            moderate_score += len(pattern.findall(query))

        if moderate_score >= 1 or complex_score >= 1:
            return QueryComplexity.MODERATE

        # Word count heuristic
        word_count = len(query.split())
        if word_count > 20:
            return QueryComplexity.MODERATE

        return QueryComplexity.SIMPLE


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def route_query(
    query: str,
    available_roles: Optional[List[AgentRole]] = None,
) -> RoutingDecision:
    """
    Quick-route a query without instantiating a router.

    Args:
        query: Natural language query.
        available_roles: Optional list of available roles.

    Returns:
        RoutingDecision with selected agent and reasoning.
    """
    router = QueryRouter(available_roles=available_roles)
    return router.route(query)
