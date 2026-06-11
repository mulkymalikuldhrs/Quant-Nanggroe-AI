"""Colony router for task-to-colony assignment.

This module provides routing logic to assign incoming tasks to the
most appropriate colony based on colony type, current load, and
task requirements.

Routing Strategy:
    1. Match task category to colony type specialization.
    2. Among matching colonies, select the one with lowest load.
    3. Fall back to least-loaded colony if no type match exists.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from quant_nanggroe_ai.multicolony.colony.config import ColonyConfig, ColonyType
from quant_nanggroe_ai.multicolony.colony.lifecycle import ColonyState

logger = structlog.get_logger(__name__)


class TaskPriority(str, Enum):
    """Priority levels for routed tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskRequest(BaseModel):
    """A task to be routed to a colony.

    Attributes:
        task_id: Unique identifier for the task.
        category: Task category used for colony-type matching.
        description: Human-readable description of the task.
        priority: Task priority level.
        required_tools: Tools required to complete the task.
        required_skills: Skills required to complete the task.
        preferred_colony_type: Optional preference for colony type.
        payload: Task-specific data payload.
        metadata: Additional metadata for the task.
    """

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str = "general"
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    required_tools: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_colony_type: ColonyType | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    """Result of a routing decision.

    Attributes:
        task_id: The task that was routed.
        colony_id: The selected colony.
        colony_type: The type of the selected colony.
        reason: Human-readable explanation of the routing decision.
        score: Routing score (0.0-1.0, higher is better match).
        timestamp: When the routing decision was made.
        alternatives: Other colonies considered, with their scores.
    """

    task_id: str
    colony_id: str
    colony_type: ColonyType
    reason: str = ""
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alternatives: list[dict[str, Any]] = Field(default_factory=list)


class ColonyInfo(BaseModel):
    """Runtime information about a colony for routing decisions.

    Attributes:
        config: The colony configuration.
        state: Current lifecycle state.
        agent_count: Number of active agents.
        task_count: Number of pending tasks.
        load_factor: Current load as a fraction (0.0-1.0).
    """

    config: ColonyConfig
    state: ColonyState = ColonyState.INITIALIZING
    agent_count: int = 0
    task_count: int = 0
    load_factor: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def is_available(self) -> bool:
        """Check if the colony is available to accept tasks."""
        return self.state in (
            ColonyState.RUNNING,
            ColonyState.IDLE,
        )

    @property
    def has_capacity(self) -> bool:
        """Check if the colony has capacity for more agents."""
        return self.agent_count < self.config.max_agents


# Mapping from task categories to preferred colony types
CATEGORY_COLONY_MAP: dict[str, ColonyType] = {
    "code": ColonyType.CODING,
    "coding": ColonyType.CODING,
    "programming": ColonyType.CODING,
    "debugging": ColonyType.CODING,
    "refactoring": ColonyType.CODING,
    "research": ColonyType.RESEARCH,
    "analysis": ColonyType.RESEARCH,
    "investigation": ColonyType.RESEARCH,
    "trading": ColonyType.TRADING,
    "finance": ColonyType.TRADING,
    "quantitative": ColonyType.TRADING,
    "ops": ColonyType.OPS,
    "operations": ColonyType.OPS,
    "deployment": ColonyType.OPS,
    "monitoring": ColonyType.OPS,
    "creative": ColonyType.CREATIVE,
    "writing": ColonyType.CREATIVE,
    "design": ColonyType.CREATIVE,
    "content": ColonyType.CREATIVE,
}


class ColonyRouter:
    """Routes tasks to the most appropriate colony.

    The router evaluates incoming tasks and assigns them to colonies
    based on type matching, current load, and capacity.

    Example::

        router = ColonyRouter()
        router.register_colony(colony_info)
        decision = await router.route_task(task_request)
    """

    def __init__(self) -> None:
        """Initialize the colony router."""
        self._colonies: dict[str, ColonyInfo] = {}
        self._routing_history: list[RoutingDecision] = []
        self._log = logger.bind(component="colony_router")

    def register_colony(self, colony_info: ColonyInfo) -> None:
        """Register a colony with the router.

        Args:
            colony_info: Runtime information about the colony.
        """
        colony_id = colony_info.config.colony_id
        self._colonies[colony_id] = colony_info
        self._log.info(
            "colony_registered",
            colony_id=colony_id,
            colony_type=colony_info.config.colony_type.value,
        )

    def unregister_colony(self, colony_id: str) -> None:
        """Unregister a colony from the router.

        Args:
            colony_id: ID of the colony to unregister.
        """
        self._colonies.pop(colony_id, None)
        self._log.info("colony_unregistered", colony_id=colony_id)

    def update_colony(
        self,
        colony_id: str,
        state: ColonyState | None = None,
        agent_count: int | None = None,
        task_count: int | None = None,
        load_factor: float | None = None,
    ) -> None:
        """Update a colony's runtime information.

        Args:
            colony_id: ID of the colony to update.
            state: Updated lifecycle state.
            agent_count: Updated agent count.
            task_count: Updated task count.
            load_factor: Updated load factor.
        """
        if colony_id not in self._colonies:
            self._log.warning("colony_not_found_for_update", colony_id=colony_id)
            return

        info = self._colonies[colony_id]
        if state is not None:
            info.state = state
        if agent_count is not None:
            info.agent_count = agent_count
        if task_count is not None:
            info.task_count = task_count
        if load_factor is not None:
            info.load_factor = load_factor

    async def route_task(self, task: TaskRequest) -> RoutingDecision:
        """Route a task to the most appropriate colony.

        Routing logic:
            1. Filter to available colonies with capacity.
            2. Determine preferred colony type from task category/preference.
            3. Score each colony based on type match and load.
            4. Select the highest-scoring colony.

        Args:
            task: The task to route.

        Returns:
            A routing decision with the selected colony.

        Raises:
            NoAvailableColonyError: If no suitable colony is found.
        """
        self._log.info(
            "routing_task",
            task_id=task.task_id,
            category=task.category,
            priority=task.priority.value,
        )

        # Determine preferred colony type
        preferred_type = task.preferred_colony_type or CATEGORY_COLONY_MAP.get(
            task.category.lower()
        )

        # Filter available colonies
        available = {
            cid: info
            for cid, info in self._colonies.items()
            if info.is_available and info.has_capacity
        }

        if not available:
            self._log.error("no_available_colonies", task_id=task.task_id)
            raise NoAvailableColonyError(
                f"No available colony found for task {task.task_id}"
            )

        # Score each colony
        scores: list[dict[str, Any]] = []
        for colony_id, info in available.items():
            score = self._score_colony(info, preferred_type, task)
            scores.append({
                "colony_id": colony_id,
                "colony_type": info.config.colony_type.value,
                "score": score,
            })

        # Sort by score descending
        scores.sort(key=lambda x: x["score"], reverse=True)
        best = scores[0]

        # Build alternatives list (without the winner)
        alternatives = [
            {"colony_id": s["colony_id"], "colony_type": s["colony_type"], "score": s["score"]}
            for s in scores[1:]
        ]

        best_info = self._colonies[best["colony_id"]]
        reason = self._build_reason(best_info, preferred_type, best["score"])

        decision = RoutingDecision(
            task_id=task.task_id,
            colony_id=best["colony_id"],
            colony_type=best_info.config.colony_type,
            reason=reason,
            score=best["score"],
            alternatives=alternatives,
        )

        self._routing_history.append(decision)
        self._log.info(
            "task_routed",
            task_id=task.task_id,
            colony_id=best["colony_id"],
            score=best["score"],
        )

        return decision

    def _score_colony(
        self,
        info: ColonyInfo,
        preferred_type: ColonyType | None,
        task: TaskRequest,
    ) -> float:
        """Score a colony for a given task.

        Scoring factors:
            - Type match: +0.4 if colony type matches preferred type.
            - Load: Lower load = higher score (up to 0.3).
            - Tool match: +0.15 for each required tool available.
            - Skill match: +0.15 for each required skill available.

        Args:
            info: Colony runtime information.
            preferred_type: The preferred colony type for the task.
            task: The task being routed.

        Returns:
            A score between 0.0 and 1.0.
        """
        score = 0.0

        # Type match bonus
        if preferred_type and info.config.colony_type == preferred_type:
            score += 0.4

        # Load factor (inverse: lower load = higher score)
        score += 0.3 * (1.0 - info.load_factor)

        # Tool match bonus
        if task.required_tools:
            available_tools = set(info.config.tool_access)
            required_tools = set(task.required_tools)
            if required_tools:
                tool_match_ratio = len(available_tools & required_tools) / len(required_tools)
                score += 0.15 * tool_match_ratio

        # Capacity bonus
        capacity_ratio = 1.0 - (info.agent_count / max(info.config.max_agents, 1))
        score += 0.15 * capacity_ratio

        return min(score, 1.0)

    def _build_reason(
        self,
        info: ColonyInfo,
        preferred_type: ColonyType | None,
        score: float,
    ) -> str:
        """Build a human-readable reason for the routing decision.

        Args:
            info: Selected colony information.
            preferred_type: The preferred colony type.
            score: The routing score.

        Returns:
            A description of why this colony was selected.
        """
        type_match = preferred_type and info.config.colony_type == preferred_type
        parts = [
            f"Selected {info.config.colony_type.value} colony "
            f"({info.config.name}) with score {score:.2f}",
        ]
        if type_match:
            parts.append("colony type matches task preference")
        else:
            parts.append("best available option based on load and capacity")
        return "; ".join(parts)

    def get_routing_history(
        self,
        limit: int | None = None,
    ) -> list[RoutingDecision]:
        """Get recent routing decisions.

        Args:
            limit: Maximum number of decisions to return.

        Returns:
            A list of recent routing decisions, newest first.
        """
        history = list(reversed(self._routing_history))
        if limit is not None:
            history = history[:limit]
        return history

    def list_colonies(self) -> list[ColonyInfo]:
        """List all registered colonies.

        Returns:
            A list of colony information objects.
        """
        return list(self._colonies.values())


class NoAvailableColonyError(Exception):
    """Raised when no suitable colony is available for task routing."""
