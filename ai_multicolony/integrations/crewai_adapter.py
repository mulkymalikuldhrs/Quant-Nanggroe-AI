"""CrewAI framework adapter for AI-MultiColony.

Provides an adapter that wraps CrewAI-style multi-agent crews
into the AI-MultiColony ecosystem, enabling seamless integration
with CrewAI agents, tasks, and crew orchestration patterns.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class CrewRole(str, Enum):
    """Role types for crew agents."""
    RESEARCHER = "researcher"
    WRITER = "writer"
    ANALYZER = "analyzer"
    CODER = "coder"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"


class CrewStatus(str, Enum):
    """Status of a crew execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Status of a crew task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── Models ───────────────────────────────────────────────────────────────────


class CrewAgent(BaseModel):
    """A crew agent definition."""
    model_config = ConfigDict(frozen=False)

    agent_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    role: CrewRole = CrewRole.EXECUTOR
    goal: str = ""
    backstory: str = ""
    tools: List[str] = Field(default_factory=list)
    allow_delegation: bool = False
    verbose: bool = False


class CrewTask(BaseModel):
    """A crew task definition."""
    model_config = ConfigDict(frozen=False)

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    expected_output: str = ""
    assigned_agent: str = ""
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None


class CrewExecution(BaseModel):
    """Record of a crew execution."""
    model_config = ConfigDict(frozen=False)

    execution_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    crew_name: str = ""
    status: CrewStatus = CrewStatus.PENDING
    agents: List[CrewAgent] = Field(default_factory=list)
    tasks: List[CrewTask] = Field(default_factory=list)
    results: Dict[str, str] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── CrewAI Adapter ───────────────────────────────────────────────────────────


class CrewAIAdapter:
    """Adapter for CrewAI-style multi-agent orchestration.

    Translates CrewAI concepts (crews, agents, tasks) into
    AI-MultiColony execution patterns.

    Usage::

        adapter = CrewAIAdapter()
        adapter.add_agent(CrewAgent(name="Researcher", role=CrewRole.RESEARCHER, goal="Research topics"))
        adapter.add_task(CrewTask(name="Research", description="Research AI trends", assigned_agent="Researcher"))
        result = await adapter.execute()
    """

    def __init__(self, crew_name: str = "default_crew"):
        self._crew_name = crew_name
        self._agents: Dict[str, CrewAgent] = {}
        self._tasks: Dict[str, CrewTask] = {}
        self._task_order: List[str] = []
        self._action_map: Dict[str, Callable] = {}
        self._executions: List[CrewExecution] = []

    def add_agent(self, agent: CrewAgent) -> None:
        """Add an agent to the crew."""
        self._agents[agent.name] = agent
        logger.debug("Added crew agent: %s (%s)", agent.name, agent.role.value)

    def add_task(self, task: CrewTask) -> None:
        """Add a task to the crew."""
        self._tasks[task.task_id] = task
        self._task_order.append(task.task_id)
        logger.debug("Added crew task: %s", task.name)

    def register_action(self, agent_name: str, action: Callable) -> None:
        """Register a custom action for an agent."""
        self._action_map[agent_name] = action

    async def execute(self, context: Optional[Dict[str, Any]] = None) -> CrewExecution:
        """Execute the crew's tasks sequentially.

        Parameters
        ----------
        context:
            Shared context passed to all tasks.

        Returns
        -------
        CrewExecution
            Execution result with task outputs.
        """
        import time
        start = time.monotonic()

        execution = CrewExecution(
            crew_name=self._crew_name,
            agents=list(self._agents.values()),
            tasks=list(self._tasks.values()),
            status=CrewStatus.RUNNING,
        )

        context = context or {}

        for task_id in self._task_order:
            task = self._tasks.get(task_id)
            if task is None:
                continue

            # Check dependencies
            deps_met = all(
                self._tasks.get(dep_id, CrewTask()).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if not deps_met:
                task.status = TaskStatus.SKIPPED
                execution.errors.append(f"Task {task.name} skipped: dependencies not met")
                continue

            # Execute task
            task.status = TaskStatus.IN_PROGRESS
            agent = self._agents.get(task.assigned_agent)

            try:
                action = self._action_map.get(task.assigned_agent)
                if action:
                    if asyncio.iscoroutinefunction(action):
                        result = await action(task=task, agent=agent, context=context)
                    else:
                        result = action(task=task, agent=agent, context=context)
                else:
                    result = f"Completed: {task.description}"

                task.result = str(result) if result else ""
                task.status = TaskStatus.COMPLETED
                execution.results[task.name] = task.result
                context[task.name] = task.result

            except Exception as e:
                task.status = TaskStatus.FAILED
                execution.errors.append(f"Task {task.name} failed: {e}")
                logger.error("CrewAI task %s failed: %s", task.name, e)

        execution.status = CrewStatus.COMPLETED if not execution.errors else CrewStatus.FAILED
        execution.duration_ms = (time.monotonic() - start) * 1000
        self._executions.append(execution)
        return execution

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def crew_name(self) -> str:
        return self._crew_name

    @property
    def agents(self) -> Dict[str, CrewAgent]:
        return dict(self._agents)

    @property
    def tasks(self) -> Dict[str, CrewTask]:
        return dict(self._tasks)

    @property
    def executions(self) -> List[CrewExecution]:
        return list(self._executions)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "crew_name": self._crew_name,
            "agent_count": len(self._agents),
            "task_count": len(self._tasks),
            "total_executions": len(self._executions),
        }
