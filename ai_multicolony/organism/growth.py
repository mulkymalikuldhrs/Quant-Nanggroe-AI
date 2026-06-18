"""Growth and marketing engine for the AI-MultiColony organism.

Implements the Growth phase of the organism lifecycle: promoting
solutions, tracking adoption metrics, and expanding the organism's
reach and impact.

The growth engine manages:
* Solution promotion and distribution
* Adoption tracking and analytics
* Feedback collection and analysis
* Market expansion strategies
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


class GrowthStage(str, Enum):
    """Stage of a solution's growth lifecycle."""
    SEED = "seed"
    SPROUT = "sprout"
    GROWING = "growing"
    MATURE = "mature"
    DECLINING = "declining"
    RETIRED = "retired"


class PromotionChannel(str, Enum):
    """Channel for promoting a solution."""
    INTERNAL = "internal"
    API = "api"
    DOCUMENTATION = "documentation"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    MARKETPLACE = "marketplace"
    SOCIAL = "social"


# ── Models ───────────────────────────────────────────────────────────────────


class GrowthMetrics(BaseModel):
    """Metrics tracking a solution's growth."""
    model_config = ConfigDict(frozen=False)

    solution_id: str = ""
    stage: GrowthStage = GrowthStage.SEED
    adoption_count: int = 0
    active_users: int = 0
    daily_active_users: int = 0
    total_requests: int = 0
    success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    error_count: int = 0
    feedback_score: float = 0.0  # 0-5 stars
    feedback_count: int = 0
    revenue_generated: float = 0.0
    cost_incurred: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PromotionRecord(BaseModel):
    """Record of a solution promotion action."""
    model_config = ConfigDict(frozen=False)

    promotion_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    solution_id: str = ""
    channel: PromotionChannel = PromotionChannel.INTERNAL
    target_audience: str = ""
    message: str = ""
    reach: int = 0
    engagement: int = 0
    conversions: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackEntry(BaseModel):
    """A user feedback entry."""
    model_config = ConfigDict(frozen=False)

    feedback_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    solution_id: str = ""
    user_id: str = ""
    rating: float = 0.0  # 0-5
    comment: str = ""
    category: str = "general"  # usability, performance, feature, bug
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Growth Engine ────────────────────────────────────────────────────────────


class GrowthEngine:
    """Manages solution growth, promotion, and adoption tracking.

    Usage::

        engine = GrowthEngine()
        engine.register_solution("sol-123", "Monitoring Service")
        engine.record_adoption("sol-123", 5)
        engine.record_request("sol-123", success=True)
        metrics = engine.get_metrics("sol-123")
    """

    def __init__(self):
        self._solutions: Dict[str, Dict[str, Any]] = {}
        self._metrics: Dict[str, GrowthMetrics] = {}
        self._promotions: List[PromotionRecord] = []
        self._feedbacks: Dict[str, List[FeedbackEntry]] = {}

    def register_solution(self, solution_id: str, name: str = "") -> GrowthMetrics:
        """Register a new solution for growth tracking."""
        metrics = GrowthMetrics(solution_id=solution_id)
        self._solutions[solution_id] = {"name": name, "registered_at": datetime.now(timezone.utc)}
        self._metrics[solution_id] = metrics
        self._feedbacks[solution_id] = []
        return metrics

    def record_adoption(self, solution_id: str, count: int = 1) -> Optional[GrowthMetrics]:
        """Record new adoptions of a solution."""
        metrics = self._metrics.get(solution_id)
        if metrics is None:
            return None
        metrics.adoption_count += count
        metrics.active_users += count
        metrics.updated_at = datetime.now(timezone.utc)
        self._update_stage(metrics)
        return metrics

    def record_request(self, solution_id: str, success: bool = True, response_time_ms: float = 0.0) -> Optional[GrowthMetrics]:
        """Record a request to a solution."""
        metrics = self._metrics.get(solution_id)
        if metrics is None:
            return None
        metrics.total_requests += 1
        if not success:
            metrics.error_count += 1
        if response_time_ms > 0:
            # Running average
            metrics.avg_response_time_ms = (
                (metrics.avg_response_time_ms * (metrics.total_requests - 1) + response_time_ms)
                / metrics.total_requests
            )
        metrics.success_rate = 1.0 - (metrics.error_count / max(1, metrics.total_requests))
        metrics.updated_at = datetime.now(timezone.utc)
        return metrics

    def record_feedback(
        self,
        solution_id: str,
        rating: float,
        comment: str = "",
        user_id: str = "",
        category: str = "general",
    ) -> Optional[FeedbackEntry]:
        """Record user feedback for a solution."""
        if solution_id not in self._metrics:
            return None

        entry = FeedbackEntry(
            solution_id=solution_id,
            user_id=user_id,
            rating=max(0.0, min(5.0, rating)),
            comment=comment,
            category=category,
        )
        self._feedbacks.setdefault(solution_id, []).append(entry)

        # Update metrics
        metrics = self._metrics[solution_id]
        all_feedback = self._feedbacks[solution_id]
        metrics.feedback_count = len(all_feedback)
        metrics.feedback_score = sum(f.rating for f in all_feedback) / len(all_feedback)
        metrics.updated_at = datetime.now(timezone.utc)

        return entry

    def promote(
        self,
        solution_id: str,
        channel: PromotionChannel = PromotionChannel.INTERNAL,
        target_audience: str = "",
        message: str = "",
    ) -> Optional[PromotionRecord]:
        """Promote a solution through a channel."""
        if solution_id not in self._solutions:
            return None

        record = PromotionRecord(
            solution_id=solution_id,
            channel=channel,
            target_audience=target_audience,
            message=message or f"Check out {self._solutions[solution_id].get('name', solution_id)}",
        )
        self._promotions.append(record)
        return record

    def get_metrics(self, solution_id: str) -> Optional[GrowthMetrics]:
        """Get growth metrics for a solution."""
        return self._metrics.get(solution_id)

    def get_feedback(self, solution_id: str) -> List[FeedbackEntry]:
        """Get all feedback for a solution."""
        return self._feedbacks.get(solution_id, [])

    def _update_stage(self, metrics: GrowthMetrics) -> None:
        """Update the growth stage based on adoption metrics."""
        if metrics.adoption_count == 0:
            metrics.stage = GrowthStage.SEED
        elif metrics.adoption_count < 10:
            metrics.stage = GrowthStage.SPROUT
        elif metrics.adoption_count < 100:
            metrics.stage = GrowthStage.GROWING
        elif metrics.adoption_count < 1000:
            metrics.stage = GrowthStage.MATURE
        else:
            metrics.stage = GrowthStage.MATURE

    @property
    def solution_count(self) -> int:
        return len(self._solutions)

    @property
    def stats(self) -> Dict[str, Any]:
        """Growth engine statistics."""
        total_adopters = sum(m.adoption_count for m in self._metrics.values())
        total_requests = sum(m.total_requests for m in self._metrics.values())
        avg_feedback = (
            sum(m.feedback_score for m in self._metrics.values()) / max(1, len(self._metrics))
        )
        return {
            "solutions_tracked": self.solution_count,
            "total_adopters": total_adopters,
            "total_requests": total_requests,
            "total_promotions": len(self._promotions),
            "avg_feedback_score": round(avg_feedback, 2),
        }
