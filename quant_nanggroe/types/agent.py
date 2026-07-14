from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AutonomyLevel(Enum):
    """Level of agent autonomous operation."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    FULL = 4


class HandType(str, Enum):
    """Types of hands in the colony system."""
    SECURITY = "security"
    CODE = "code"
    RESEARCH = "research"
    BROWSER = "browser"
    VOICE = "voice"
    COMPUTE = "compute"
    INTEGRATION = "integration"


@dataclass
class ColonyConfig:
    """Configuration for an agent colony."""
    max_agents_per_hand: int = 10
    heartbeat_interval: int = 30
    rebalance_interval: int = 300
    task_timeout: int = 120
    debug_mode: bool = False
    
    def model_dump(self) -> Dict[str, Any]:
        return {
            "max_agents_per_hand": self.max_agents_per_hand,
            "heartbeat_interval": self.heartbeat_interval,
            "rebalance_interval": self.rebalance_interval,
            "task_timeout": self.task_timeout,
            "debug_mode": self.debug_mode,
        }


class AgentType(str, Enum):
    """Types of agents in the Quant Nanggroe system."""

    BROWSER = "BROWSER"
    CODER = "CODER"
    COLONY = "COLONY"
    EXECUTOR = "EXECUTOR"
    MANUS = "MANUS"
    PLANNER = "PLANNER"
    RESEARCHER = "RESEARCHER"
    SECURITY = "SECURITY"
    VOICE = "VOICE"
    TRADER = "TRADER"
    ANALYST = "ANALYST"
    ORCHESTRATOR = "ORCHESTRATOR"


@dataclass
class AgentSpec:
    """Specification for an agent instance.

    Attributes:
        agent_type: The type/category of agent.
        autonomy_level: Level of autonomous operation (0-5).
        config: Optional configuration dictionary.
    """

    agent_type: AgentType = AgentType.RESEARCHER
    autonomy_level: int = 1
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.autonomy_level < 0 or self.autonomy_level > 5:
            raise ValueError(f"autonomy_level must be 0-5, got {self.autonomy_level}")


@dataclass
class Task:
    """Represents a task to be executed by an agent.

    Attributes:
        id: Unique task identifier.
        description: Human-readable task description.
        payload: Task-specific data payload.
        priority: Task priority (higher = more important).
        dependencies: List of task IDs that must complete first.
        metadata: Additional task metadata.
    """

    id: str = ""
    description: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a task execution.

    Attributes:
        task_id: ID of the executed task.
        success: Whether the task completed successfully.
        output: Output data from task execution.
        error: Error message if task failed.
        execution_time_ms: Time taken to execute in milliseconds.
        metadata: Additional result metadata.
    """

    task_id: str = ""
    success: bool = True
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
