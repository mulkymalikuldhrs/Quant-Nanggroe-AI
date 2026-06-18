"""Colony type definitions for the AI MultiColony Ecosystem.

Implements colony-based agent coordination from OpenFang and MultiColony patterns.
Defines ColonyState, HandType, ColonyConfig, and TaskAssignment.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ColonyState(str, Enum):
    """States of a colony."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    SCALING = "scaling"
    ERROR = "error"
    TERMINATED = "terminated"
    IDLE = "idle"


class HandType(str, Enum):
    """Types of colony hands (specialized agent groups).

    From OpenFang colony hand architecture.
    """

    SECURITY = "security"
    CODE = "code"
    RESEARCH = "research"
    BROWSER = "browser"
    VOICE = "voice"
    DATA = "data"
    INFRASTRUCTURE = "infrastructure"
    COMMUNICATION = "communication"
    PLANNING = "planning"
    EXECUTION = "execution"


class TaskPriority(str, Enum):
    """Priority levels for colony tasks."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Status of a colony task."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ColonyConfig(BaseModel):
    """Configuration for a colony."""

    colony_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="unnamed-colony")
    description: str = ""
    state: ColonyState = ColonyState.INITIALIZING
    model: str = Field(default="gpt-4o")

    # Hand configuration
    hands: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Limits
    max_agents: int = Field(default=10, ge=1, le=100)
    max_iterations: int = Field(default=50, ge=1)
    max_cost: float = Field(default=50.0, ge=0.0)
    timeout: int = Field(default=600, ge=1)

    # Scheduling
    scheduling_strategy: str = Field(default="round_robin")
    priority_weights: dict[str, float] = Field(default_factory=dict)

    # Communication
    broadcast_enabled: bool = Field(default=True)
    inter_colony_enabled: bool = Field(default=False)

    # Metadata
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class TaskAssignment(BaseModel):
    """Assignment of a task to a specific hand or agent within a colony.

    Tracks the full lifecycle of a task from creation through
    assignment, execution, and completion.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    colony_id: str = ""
    assigned_hand: Optional[HandType] = None
    assigned_agent_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    parent_task_id: Optional[str] = None
    subtask_ids: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    required_capabilities: list[str] = Field(default_factory=list)
    estimated_iterations: Optional[int] = None
    max_iterations: Optional[int] = None
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    deadline: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def mark_assigned(self, agent_id: str, hand: Optional[HandType] = None) -> None:
        """Mark the task as assigned to an agent.

        Args:
            agent_id: The agent being assigned.
            hand: Optional hand type.
        """
        self.assigned_agent_id = agent_id
        self.assigned_hand = hand
        self.status = TaskStatus.ASSIGNED
        self.updated_at_if_needed()

    def mark_started(self) -> None:
        """Mark the task as in progress."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = time.time()

    def mark_completed(self, result: Optional[str] = None) -> None:
        """Mark the task as completed.

        Args:
            result: Optional result string.
        """
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        if result is not None:
            self.result = result

    def mark_failed(self, error: Optional[str] = None) -> None:
        """Mark the task as failed.

        Args:
            error: Optional error message.
        """
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        if error is not None:
            self.error = error

    def updated_at_if_needed(self) -> None:
        """Update the timestamp if the model has updated_at (ColonyConfig compatibility)."""
        pass


class ColonyTask(BaseModel):
    """A task assigned to a colony or specific hand.

    Backward-compatible alias kept for existing code.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    assigned_hand: Optional[HandType] = None
    assigned_agent_id: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    status: str = "pending"
    parent_task_id: Optional[str] = None
    subtasks: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class ColonyStatus(BaseModel):
    """Runtime status of a colony."""

    colony_id: str
    name: str
    state: ColonyState
    agent_count: int = 0
    active_agents: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    uptime: float = 0.0
    hands: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}
