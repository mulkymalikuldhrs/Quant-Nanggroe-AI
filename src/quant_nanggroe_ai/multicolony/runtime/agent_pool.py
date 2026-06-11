"""Agent pool for spawning and managing agents within a colony.

This module provides the AgentPool class which manages the lifecycle
of agents within a colony, including spawning, tracking, and
terminating agents.

The agent pool enforces the colony's max_agents limit and tracks
resource usage per agent.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

from quant_nanggroe_ai.multicolony.colony.config import AgentConfig, ColonyConfig

logger = structlog.get_logger(__name__)


class AgentState(str, Enum):
    """States of an individual agent within the pool."""

    SPAWNING = "spawning"
    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"


class AgentInfo(BaseModel):
    """Runtime information about an agent in the pool.

    Attributes:
        agent_id: Unique identifier.
        name: Human-readable name.
        role: Agent's role within the colony.
        state: Current agent state.
        config: The agent's configuration.
        spawned_at: Timestamp when the agent was spawned.
        last_active: Timestamp of last activity.
        tasks_completed: Number of tasks completed.
        memory_usage_mb: Current memory usage.
        current_task_id: ID of the task being processed, if any.
        metadata: Additional runtime metadata.
    """

    agent_id: str
    name: str = "unnamed-agent"
    role: str = "worker"
    state: AgentState = AgentState.SPAWNING
    config: AgentConfig = Field(default_factory=AgentConfig)
    spawned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tasks_completed: int = 0
    memory_usage_mb: float = 0.0
    current_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentPool:
    """Manages a pool of agents within a colony.

    The agent pool handles spawning, tracking, and terminating agents,
    while respecting the colony's resource limits.

    Example::

        pool = AgentPool(colony_config)
        agent_id = await pool.spawn(agent_config)
        info = pool.get_agent(agent_id)
        await pool.terminate(agent_id)
    """

    def __init__(self, colony_config: ColonyConfig) -> None:
        """Initialize the agent pool.

        Args:
            colony_config: The parent colony configuration.
        """
        self._config = colony_config
        self._agents: dict[str, AgentInfo] = {}
        self._lock = asyncio.Lock()
        self._log = logger.bind(
            colony_id=colony_config.colony_id,
            component="agent_pool",
        )

    @property
    def active_count(self) -> int:
        """Number of active (non-terminated) agents."""
        return sum(
            1
            for a in self._agents.values()
            if a.state not in (AgentState.TERMINATED, AgentState.FAILED)
        )

    @property
    def busy_count(self) -> int:
        """Number of currently busy agents."""
        return sum(1 for a in self._agents.values() if a.state == AgentState.BUSY)

    @property
    def idle_count(self) -> int:
        """Number of currently idle agents."""
        return sum(1 for a in self._agents.values() if a.state == AgentState.IDLE)

    @property
    def total_memory_mb(self) -> float:
        """Total memory usage across all agents in MB."""
        return sum(a.memory_usage_mb for a in self._agents.values())

    @property
    def max_capacity(self) -> int:
        """Maximum agent capacity from colony config."""
        return self._config.max_agents

    @property
    def has_capacity(self) -> bool:
        """Whether the pool can accept more agents."""
        return self.active_count < self._config.max_agents

    async def spawn(
        self,
        config: AgentConfig | None = None,
        on_spawned: Callable[[AgentInfo], Any] | None = None,
    ) -> str:
        """Spawn a new agent in the pool.

        Args:
            config: Agent configuration. Uses colony defaults if not provided.
            on_spawned: Optional callback after agent is spawned.

        Returns:
            The agent_id of the spawned agent.

        Raises:
            AgentPoolFullError: If the pool has reached max capacity.
        """
        async with self._lock:
            if not self.has_capacity:
                raise AgentPoolFullError(
                    f"Agent pool is full ({self.active_count}/{self._config.max_agents})"
                )

            if config is None:
                config = self._config.get_default_agent_config()

            agent_id = config.agent_id or str(uuid.uuid4())
            info = AgentInfo(
                agent_id=agent_id,
                name=config.name,
                role=config.role,
                state=AgentState.SPAWNING,
                config=config,
                memory_usage_mb=config.memory_budget_mb,
            )

            self._agents[agent_id] = info

            self._log.info(
                "agent_spawning",
                agent_id=agent_id,
                name=config.name,
                role=config.role,
            )

            # Simulate async spawn initialization
            await asyncio.sleep(0)

            # Transition to idle after spawn
            info.state = AgentState.IDLE
            info.last_active = datetime.now(timezone.utc)

            if on_spawned is not None:
                on_spawned(info)

            self._log.info(
                "agent_spawned",
                agent_id=agent_id,
                pool_size=self.active_count,
            )

            return agent_id

    async def spawn_batch(
        self,
        configs: list[AgentConfig],
    ) -> list[str]:
        """Spawn multiple agents in parallel.

        Args:
            configs: List of agent configurations.

        Returns:
            List of spawned agent IDs.
        """
        tasks = [self.spawn(config) for config in configs]
        return list(await asyncio.gather(*tasks))

    async def terminate(self, agent_id: str) -> None:
        """Terminate an agent in the pool.

        Args:
            agent_id: ID of the agent to terminate.

        Raises:
            AgentNotFoundError: If the agent is not in the pool.
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise AgentNotFoundError(f"Agent {agent_id} not found in pool.")

            info = self._agents[agent_id]
            info.state = AgentState.TERMINATING
            info.last_active = datetime.now(timezone.utc)

            self._log.info("agent_terminating", agent_id=agent_id)

            # Simulate async cleanup
            await asyncio.sleep(0)

            info.state = AgentState.TERMINATED
            self._log.info(
                "agent_terminated",
                agent_id=agent_id,
                pool_size=self.active_count,
            )

    async def terminate_all(self) -> int:
        """Terminate all agents in the pool.

        Returns:
            Number of agents terminated.
        """
        agent_ids = [
            aid
            for aid, info in self._agents.items()
            if info.state not in (AgentState.TERMINATED, AgentState.FAILED)
        ]
        for agent_id in agent_ids:
            await self.terminate(agent_id)
        return len(agent_ids)

    def get_agent(self, agent_id: str) -> AgentInfo:
        """Get information about a specific agent.

        Args:
            agent_id: ID of the agent.

        Returns:
            Agent runtime information.

        Raises:
            AgentNotFoundError: If the agent is not in the pool.
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent {agent_id} not found in pool.")
        return self._agents[agent_id]

    def get_idle_agents(self) -> list[AgentInfo]:
        """Get all idle agents.

        Returns:
            A list of idle agent information objects.
        """
        return [a for a in self._agents.values() if a.state == AgentState.IDLE]

    def get_agents_by_role(self, role: str) -> list[AgentInfo]:
        """Get all agents with a specific role.

        Args:
            role: The role to filter by.

        Returns:
            A list of matching agent information objects.
        """
        return [a for a in self._agents.values() if a.role == role]

    def assign_task(self, agent_id: str, task_id: str) -> AgentInfo:
        """Assign a task to an agent.

        Args:
            agent_id: ID of the agent.
            task_id: ID of the task.

        Returns:
            Updated agent information.

        Raises:
            AgentNotFoundError: If the agent is not in the pool.
            AgentNotAvailableError: If the agent is not idle.
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent {agent_id} not found in pool.")

        info = self._agents[agent_id]
        if info.state != AgentState.IDLE:
            raise AgentNotAvailableError(
                f"Agent {agent_id} is not idle (state: {info.state.value})"
            )

        info.state = AgentState.BUSY
        info.current_task_id = task_id
        info.last_active = datetime.now(timezone.utc)

        self._log.info(
            "agent_assigned_task",
            agent_id=agent_id,
            task_id=task_id,
        )
        return info

    def complete_task(self, agent_id: str) -> AgentInfo:
        """Mark an agent's current task as complete.

        Args:
            agent_id: ID of the agent.

        Returns:
            Updated agent information.
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent {agent_id} not found in pool.")

        info = self._agents[agent_id]
        info.state = AgentState.IDLE
        info.current_task_id = None
        info.tasks_completed += 1
        info.last_active = datetime.now(timezone.utc)

        self._log.info(
            "agent_completed_task",
            agent_id=agent_id,
            total_completed=info.tasks_completed,
        )
        return info

    def list_agents(
        self,
        state: AgentState | None = None,
    ) -> list[AgentInfo]:
        """List agents in the pool, optionally filtered by state.

        Args:
            state: Optional state filter.

        Returns:
            A list of agent information objects.
        """
        agents = list(self._agents.values())
        if state is not None:
            agents = [a for a in agents if a.state == state]
        return agents

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            A dictionary of pool statistics.
        """
        return {
            "total_agents": len(self._agents),
            "active_agents": self.active_count,
            "idle_agents": self.idle_count,
            "busy_agents": self.busy_count,
            "max_capacity": self.max_capacity,
            "has_capacity": self.has_capacity,
            "total_memory_mb": self.total_memory_mb,
            "memory_budget_mb": self._config.memory_budget,
            "memory_utilization": self.total_memory_mb / max(self._config.memory_budget, 1),
        }


class AgentPoolFullError(Exception):
    """Raised when attempting to spawn an agent beyond pool capacity."""


class AgentNotFoundError(Exception):
    """Raised when an agent is not found in the pool."""


class AgentNotAvailableError(Exception):
    """Raised when an agent is not available for task assignment."""
