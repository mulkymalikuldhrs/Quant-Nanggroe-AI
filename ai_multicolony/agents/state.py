"""Shared agent state management with Pydantic models.

Provides thread-safe shared state and rich Pydantic models for agent lifecycle,
health, autonomy, context, colony coordination, task tracking, A2A messaging,
and health reporting.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from ..types import AgentState, AgentType, AutonomyLevel, HandType, TaskStatus


# ── Pydantic State Models ──


class AgentStateModel(BaseModel):
    """Pydantic model capturing the full runtime state of an agent.

    Covers lifecycle state, health score, autonomy level, and context window
    usage so that an agent's complete condition can be serialized, inspected,
    or persisted at any moment.
    """

    model_config = ConfigDict(frozen=False)

    agent_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    lifecycle: AgentState = AgentState.REGISTERED
    health_score: float = 1.0
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    context_usage: float = 0.0
    context_capacity: int = 4096
    colony_id: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def context_ratio(self) -> float:
        """Return context usage as a ratio of capacity (0.0 - 1.0)."""
        return self.context_usage / max(1, self.context_capacity)


class AgentConfig(BaseModel):
    """Configuration model for agent creation and customization.

    Encapsulates type, tier, colony assignment, capabilities, tools, skills,
    memory settings, resource limits, lifecycle parameters, and security
    constraints so that agents can be consistently spawned from declarative
    configs.
    """

    model_config = ConfigDict(frozen=False)

    agent_type: AgentType = AgentType.MANUS
    tier: int = Field(default=1, ge=0, le=5, description="Resource tier 0-5")
    colony_id: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    memory: Dict[str, Any] = Field(
        default_factory=lambda: {
            "compaction_threshold": 0.8,
            "page_size": 4096,
            "tier": "t1_letta",
        }
    )
    resources: Dict[str, Any] = Field(
        default_factory=lambda: {
            "cpu_limit": 1.0,
            "memory_mb": 512,
            "timeout_ms": 300000,
        }
    )
    lifecycle: Dict[str, Any] = Field(
        default_factory=lambda: {
            "heartbeat_interval_ms": 30000,
            "max_retries": 3,
            "drain_timeout_ms": 60000,
        }
    )
    security: Dict[str, Any] = Field(
        default_factory=lambda: {
            "autonomy_level": "L1_SAFE_OPS",
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout_s": 60,
            "allowed_tools": [],
            "denied_tools": [],
        }
    )


class ColonyState(BaseModel):
    """Pydantic model capturing the runtime state of a colony.

    Includes colony identity, overseer, hand composition, member agents,
    and resource allocation so that colony-level decisions can be made from
    a consistent data snapshot.
    """

    model_config = ConfigDict(frozen=False)

    colony_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "default"
    overseer_id: Optional[str] = None
    hands: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "security": [],
            "code": [],
            "research": [],
            "browser": [],
            "voice": [],
            "compute": [],
            "integration": [],
        }
    )
    agents: List[str] = Field(default_factory=list)
    resources: Dict[str, Any] = Field(
        default_factory=lambda: {
            "total_cpu": 8.0,
            "total_memory_mb": 16384,
            "used_cpu": 0.0,
            "used_memory_mb": 0,
        }
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"

    @property
    def agent_count(self) -> int:
        """Total number of agents in the colony."""
        return len(self.agents)

    @property
    def hand_coverage(self) -> Dict[str, int]:
        """Number of agents in each hand."""
        return {hand: len(members) for hand, members in self.hands.items()}


class TaskStateModel(BaseModel):
    """Pydantic model for task lifecycle tracking.

    Captures task identity, current status, priority, deadline, and
    assignment information so that task state can be persisted, inspected,
    and restored across system restarts.
    """

    model_config = ConfigDict(frozen=False)

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Field(default=0, ge=0, le=10)
    deadline: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    description: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0

    @property
    def is_expired(self) -> bool:
        """Check whether the task deadline has passed."""
        if self.deadline is None:
            return False
        return datetime.now(timezone.utc) > self.deadline

    @property
    def can_retry(self) -> bool:
        """Whether the task still has retries available."""
        return self.retries < self.max_retries


class A2AMessageState(BaseModel):
    """Pydantic model for Agent-to-Agent message tracking.

    Extends the core A2AMessage with delivery status, correlation IDs for
    request-response patterns, and hop metadata useful for debugging and
    observability.
    """

    model_config = ConfigDict(frozen=False)

    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    sender_id: str = ""
    sender_colony: str = ""
    recipient_id: str = ""
    recipient_colony: str = ""
    message_type: str = "task_delegation"
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    delivered: bool = False
    hops: List[Dict[str, Any]] = Field(default_factory=list)


class HealthReport(BaseModel):
    """Detailed health report for an agent.

    Computes an aggregate health score from component scores and provides a
    breakdown so that operators and automated systems can pinpoint degradation.
    """

    model_config = ConfigDict(frozen=False)

    agent_id: str = ""
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    breakdown: Dict[str, float] = Field(
        default_factory=lambda: {
            "liveness": 1.0,
            "task_success_rate": 1.0,
            "context_health": 1.0,
            "circuit_breaker_health": 1.0,
            "heartbeat_regularity": 1.0,
        }
    )
    last_check: datetime = Field(default_factory=datetime.utcnow)
    issues: List[str] = Field(default_factory=list)

    def recalculate(self) -> None:
        """Recalculate the aggregate score from the breakdown.

        Uses a weighted formula where liveness is critical (30%), task success
        is important (25%), and the remaining factors share the rest.

        Formula::

            score = 0.30*liv + 0.25*tsr + 0.15*ctx + 0.15*cb + 0.15*hb
        """
        weights = {
            "liveness": 0.30,
            "task_success_rate": 0.25,
            "context_health": 0.15,
            "circuit_breaker_health": 0.15,
            "heartbeat_regularity": 0.15,
        }
        self.score = sum(
            weights.get(k, 0.0) * v for k, v in self.breakdown.items()
        )
        self.score = max(0.0, min(1.0, self.score))
        self.last_check = datetime.now(timezone.utc)

    @property
    def is_healthy(self) -> bool:
        """Return True when the aggregate score is above the 0.7 threshold."""
        return self.score >= 0.7

    @property
    def is_degraded(self) -> bool:
        """Return True when the score is between 0.4 and 0.7."""
        return 0.4 <= self.score < 0.7

    @property
    def is_critical(self) -> bool:
        """Return True when the score falls below 0.4."""
        return self.score < 0.4


# ── Thread-safe Shared State ──


class SharedAgentState:
    """Thread-safe shared state for agents within a colony.

    Provides a simple key-value store with per-agent namespaces, backed by a
    threading lock so that concurrent agents can safely read and write shared
    data without external synchronisation.
    """

    def __init__(self, colony_id: str = ""):
        self.colony_id = colony_id
        self._state: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._agent_states: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any) -> None:
        """Set a global shared key."""
        with self._lock:
            self._state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a global shared key, returning *default* if absent."""
        with self._lock:
            return self._state.get(key, default)

    def delete(self, key: str) -> None:
        """Delete a global shared key."""
        with self._lock:
            self._state.pop(key, None)

    def set_agent_state(self, agent_id: str, key: str, value: Any) -> None:
        """Set a key within an agent's private namespace."""
        with self._lock:
            if agent_id not in self._agent_states:
                self._agent_states[agent_id] = {}
            self._agent_states[agent_id][key] = value

    def get_agent_state(self, agent_id: str, key: str, default: Any = None) -> Any:
        """Get a key from an agent's private namespace."""
        with self._lock:
            return self._agent_states.get(agent_id, {}).get(key, default)

    def get_all_state(self) -> Dict[str, Any]:
        """Return a shallow copy of the global state dict."""
        with self._lock:
            return dict(self._state)

    def get_all_agent_states(self) -> Dict[str, Dict[str, Any]]:
        """Return a shallow copy of all per-agent state dicts."""
        with self._lock:
            return {aid: dict(state) for aid, state in self._agent_states.items()}

    def clear(self) -> None:
        """Clear all global and per-agent state."""
        with self._lock:
            self._state.clear()
            self._agent_states.clear()
