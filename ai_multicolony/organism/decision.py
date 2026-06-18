"""Decision scoring engine for the AI-MultiColony organism.

Implements the Decision phase of the organism lifecycle: evaluating
detected signals against configurable scoring criteria to determine
which problems/opportunities to act on.

Supports multi-criteria decision analysis (MCDA) with weighted
scoring, cost-benefit analysis, and priority ranking.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class DecisionStatus(str, Enum):
    """Status of a decision."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    ESCALATED = "escalated"


class CriterionCategory(str, Enum):
    """Category of a scoring criterion."""
    IMPACT = "impact"
    URGENCY = "urgency"
    FEASIBILITY = "feasibility"
    COST = "cost"
    RISK = "risk"
    ALIGNMENT = "alignment"
    INNOVATION = "innovation"


# ── Models ───────────────────────────────────────────────────────────────────


class ScoringCriterion(BaseModel):
    """A single scoring criterion with weight and scale."""
    model_config = ConfigDict(frozen=False)

    name: str = ""
    category: CriterionCategory = CriterionCategory.IMPACT
    description: str = ""
    weight: float = 1.0  # 0.0 to 2.0
    min_score: float = 0.0
    max_score: float = 10.0
    threshold: float = 5.0  # Minimum score to pass this criterion

    def normalize(self, score: float) -> float:
        """Normalize a score to 0-1 range."""
        if self.max_score == self.min_score:
            return 0.0
        return max(0.0, min(1.0, (score - self.min_score) / (self.max_score - self.min_score)))


class DecisionScore(BaseModel):
    """Score breakdown for a decision."""
    model_config = ConfigDict(frozen=False)

    decision_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    signal_id: str = ""
    signal_title: str = ""
    criteria_scores: Dict[str, float] = Field(default_factory=dict)  # criterion_name → raw score
    weighted_scores: Dict[str, float] = Field(default_factory=dict)  # criterion_name → weighted score
    total_score: float = 0.0
    max_possible_score: float = 0.0
    normalized_score: float = 0.0  # 0.0 to 1.0
    passed_thresholds: bool = True
    status: DecisionStatus = DecisionStatus.PENDING
    reason: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_approved(self) -> bool:
        return self.status == DecisionStatus.APPROVED


class DecisionConfig(BaseModel):
    """Configuration for the decision engine."""
    model_config = ConfigDict(frozen=False)

    approval_threshold: float = 0.6  # Normalized score required for approval
    rejection_threshold: float = 0.3  # Below this → auto-reject
    max_deferred: int = 100
    require_all_thresholds: bool = False  # If True, all criteria must pass
    escalation_threshold: float = 0.8  # Above this → escalate for review
    criteria: List[ScoringCriterion] = Field(default_factory=list)


# ── Default criteria ─────────────────────────────────────────────────────────


DEFAULT_CRITERIA: List[ScoringCriterion] = [
    ScoringCriterion(
        name="business_impact",
        category=CriterionCategory.IMPACT,
        description="Expected impact on business outcomes",
        weight=1.5,
        threshold=4.0,
    ),
    ScoringCriterion(
        name="urgency",
        category=CriterionCategory.URGENCY,
        description="Time sensitivity and deadline pressure",
        weight=1.2,
        threshold=3.0,
    ),
    ScoringCriterion(
        name="feasibility",
        category=CriterionCategory.FEASIBILITY,
        description="Technical and operational feasibility",
        weight=1.0,
        threshold=5.0,
    ),
    ScoringCriterion(
        name="cost_efficiency",
        category=CriterionCategory.COST,
        description="Return on investment and resource efficiency",
        weight=0.8,
        threshold=4.0,
    ),
    ScoringCriterion(
        name="risk_level",
        category=CriterionCategory.RISK,
        description="Risk assessment (higher score = lower risk)",
        weight=1.0,
        threshold=4.0,
    ),
    ScoringCriterion(
        name="strategic_alignment",
        category=CriterionCategory.ALIGNMENT,
        description="Alignment with strategic objectives",
        weight=1.3,
        threshold=5.0,
    ),
    ScoringCriterion(
        name="innovation_potential",
        category=CriterionCategory.INNOVATION,
        description="Potential for breakthrough innovation",
        weight=0.7,
        threshold=3.0,
    ),
]


# ── Decision Engine ──────────────────────────────────────────────────────────


class DecisionEngine:
    """Multi-criteria decision scoring engine.

    Evaluates signals against configurable scoring criteria,
    computes weighted scores, and determines whether to approve,
    reject, defer, or escalate.

    Usage::

        engine = DecisionEngine()
        score = engine.evaluate(
            signal_id="sig-123",
            signal_title="Market opportunity detected",
            criteria_scores={
                "business_impact": 8.0,
                "urgency": 7.0,
                "feasibility": 6.0,
                "cost_efficiency": 5.0,
                "risk_level": 7.0,
                "strategic_alignment": 8.0,
                "innovation_potential": 6.0,
            }
        )
    """

    def __init__(self, config: Optional[DecisionConfig] = None):
        self._config = config or DecisionConfig(
            criteria=list(DEFAULT_CRITERIA),
        )
        self._decisions: List[DecisionScore] = []
        self._deferred_count: int = 0

    def evaluate(
        self,
        signal_id: str,
        signal_title: str,
        criteria_scores: Dict[str, float],
    ) -> DecisionScore:
        """Evaluate a signal against scoring criteria.

        Parameters
        ----------
        signal_id:
            ID of the signal being evaluated.
        signal_title:
            Title of the signal.
        criteria_scores:
            Raw scores for each criterion (key must match criterion name).

        Returns
        -------
        DecisionScore
            Scored decision with approval status.
        """
        criteria_map = {c.name: c for c in self._config.criteria}

        # Compute weighted scores
        weighted_scores: Dict[str, float] = {}
        total_score = 0.0
        max_possible = 0.0
        passed_all = True

        for criterion in self._config.criteria:
            raw_score = criteria_scores.get(criterion.name, 0.0)
            # Clamp to valid range
            raw_score = max(criterion.min_score, min(criterion.max_score, raw_score))

            normalized = criterion.normalize(raw_score)
            weighted = normalized * criterion.weight
            weighted_scores[criterion.name] = round(weighted, 3)
            total_score += weighted
            max_possible += criterion.weight

            # Check threshold
            if raw_score < criterion.threshold:
                passed_all = False

        # Compute normalized score
        normalized_score = total_score / max_possible if max_possible > 0 else 0.0
        normalized_score = round(min(1.0, max(0.0, normalized_score)), 3)

        # Determine status
        if self._config.require_all_thresholds and not passed_all:
            status = DecisionStatus.REJECTED
            reason = "One or more criteria did not meet threshold"
        elif normalized_score >= self._config.escalation_threshold:
            status = DecisionStatus.ESCALATED
            reason = "Score exceeds escalation threshold"
        elif normalized_score >= self._config.approval_threshold:
            status = DecisionStatus.APPROVED
            reason = "Score meets approval threshold"
        elif normalized_score < self._config.rejection_threshold:
            status = DecisionStatus.REJECTED
            reason = f"Score {normalized_score:.3f} below rejection threshold {self._config.rejection_threshold}"
        else:
            status = DecisionStatus.DEFERRED
            reason = "Score in deferment range"
            self._deferred_count += 1

        decision = DecisionScore(
            signal_id=signal_id,
            signal_title=signal_title,
            criteria_scores=criteria_scores,
            weighted_scores=weighted_scores,
            total_score=round(total_score, 3),
            max_possible_score=round(max_possible, 3),
            normalized_score=normalized_score,
            passed_thresholds=passed_all,
            status=status,
            reason=reason,
        )

        self._decisions.append(decision)
        return decision

    def batch_evaluate(
        self,
        signals: List[Dict[str, Any]],
    ) -> List[DecisionScore]:
        """Evaluate multiple signals.

        Parameters
        ----------
        signals:
            List of dicts with keys: signal_id, signal_title, criteria_scores.

        Returns
        -------
        list[DecisionScore]
            Scored decisions sorted by normalized_score (descending).
        """
        results = []
        for sig in signals:
            score = self.evaluate(
                signal_id=sig.get("signal_id", ""),
                signal_title=sig.get("signal_title", ""),
                criteria_scores=sig.get("criteria_scores", {}),
            )
            results.append(score)

        results.sort(key=lambda d: d.normalized_score, reverse=True)
        return results

    @property
    def decisions(self) -> List[DecisionScore]:
        return list(self._decisions)

    @property
    def config(self) -> DecisionConfig:
        return self._config

    @property
    def stats(self) -> Dict[str, Any]:
        total = len(self._decisions)
        approved = sum(1 for d in self._decisions if d.status == DecisionStatus.APPROVED)
        rejected = sum(1 for d in self._decisions if d.status == DecisionStatus.REJECTED)
        deferred = sum(1 for d in self._decisions if d.status == DecisionStatus.DEFERRED)
        escalated = sum(1 for d in self._decisions if d.status == DecisionStatus.ESCALATED)
        return {
            "total_decisions": total,
            "approved": approved,
            "rejected": rejected,
            "deferred": deferred,
            "escalated": escalated,
            "approval_rate": approved / max(1, total),
            "criteria_count": len(self._config.criteria),
        }
