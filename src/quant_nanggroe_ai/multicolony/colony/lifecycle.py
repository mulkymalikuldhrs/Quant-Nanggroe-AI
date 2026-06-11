"""Colony lifecycle manager for the Multi-Colony Ecosystem.

This module manages the lifecycle states and transitions of agent colonies,
including initialization, scaling, hibernation, and termination.

Lifecycle States:
    INITIALIZING -> RUNNING: Colony setup complete, agents spawned.
    RUNNING -> SCALING: Colony is scaling up or down.
    SCALING -> RUNNING: Scaling operation complete.
    RUNNING -> IDLE: No tasks pending, agents waiting.
    IDLE -> RUNNING: New tasks assigned.
    RUNNING -> HIBERNATING: Colony entering low-power mode.
    HIBERNATING -> RUNNING: Colony reactivated.
    * -> TERMINATING: Colony is shutting down.
    * -> FAILED: Colony encountered an unrecoverable error.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from quant_nanggroe_ai.multicolony.colony.config import ColonyConfig

logger = structlog.get_logger(__name__)


class ColonyState(str, Enum):
    """Lifecycle states for an agent colony.

    States represent the current phase of a colony's lifecycle.
    Transitions between states follow a defined state machine.
    """

    INITIALIZING = "initializing"
    RUNNING = "running"
    SCALING = "scaling"
    IDLE = "idle"
    HIBERNATING = "hibernating"
    TERMINATING = "terminating"
    FAILED = "failed"


# Valid state transitions: from_state -> set of allowed to_states
VALID_TRANSITIONS: dict[ColonyState, set[ColonyState]] = {
    ColonyState.INITIALIZING: {
        ColonyState.RUNNING,
        ColonyState.FAILED,
        ColonyState.TERMINATING,
    },
    ColonyState.RUNNING: {
        ColonyState.SCALING,
        ColonyState.IDLE,
        ColonyState.HIBERNATING,
        ColonyState.TERMINATING,
        ColonyState.FAILED,
    },
    ColonyState.SCALING: {
        ColonyState.RUNNING,
        ColonyState.TERMINATING,
        ColonyState.FAILED,
    },
    ColonyState.IDLE: {
        ColonyState.RUNNING,
        ColonyState.HIBERNATING,
        ColonyState.TERMINATING,
        ColonyState.FAILED,
    },
    ColonyState.HIBERNATING: {
        ColonyState.RUNNING,
        ColonyState.TERMINATING,
        ColonyState.FAILED,
    },
    ColonyState.TERMINATING: set(),  # Terminal state
    ColonyState.FAILED: {ColonyState.TERMINATING},  # Can only terminate from failed
}


class ColonyStatus(BaseModel):
    """Current status snapshot of a colony.

    Attributes:
        colony_id: Unique identifier of the colony.
        state: Current lifecycle state.
        previous_state: The previous lifecycle state.
        agent_count: Number of active agents.
        task_count: Number of pending/active tasks.
        memory_usage_mb: Current memory usage in MB.
        last_state_change: Timestamp of the last state transition.
        error_message: Error details if state is FAILED.
        uptime_seconds: Seconds since the colony was initialized.
    """

    colony_id: str
    state: ColonyState = ColonyState.INITIALIZING
    previous_state: ColonyState | None = None
    agent_count: int = 0
    task_count: int = 0
    memory_usage_mb: float = 0.0
    last_state_change: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    error_message: str | None = None
    uptime_seconds: float = 0.0


class ColonyLifecycle:
    """Manages the lifecycle state machine for an agent colony.

    This class encapsulates the state machine logic for colony lifecycle
    transitions, providing methods to safely transition between states
    and query the current status.

    Example::

        lifecycle = ColonyLifecycle(config=colony_config)
        await lifecycle.initialize()
        await lifecycle.transition_to(ColonyState.RUNNING)
        status = lifecycle.get_status()
    """

    def __init__(self, config: ColonyConfig) -> None:
        """Initialize the lifecycle manager.

        Args:
            config: The colony configuration to manage lifecycle for.
        """
        self._config = config
        self._status = ColonyStatus(colony_id=config.colony_id)
        self._initialized_at: datetime | None = None
        self._state_history: list[dict[str, Any]] = []
        self._log = logger.bind(
            colony_id=config.colony_id,
            colony_type=config.colony_type.value,
        )

    @property
    def state(self) -> ColonyState:
        """Current lifecycle state of the colony."""
        return self._status.state

    @property
    def status(self) -> ColonyStatus:
        """Current status snapshot of the colony."""
        return self._status

    def can_transition_to(self, target: ColonyState) -> bool:
        """Check if a transition to the target state is valid.

        Args:
            target: The desired target state.

        Returns:
            True if the transition is valid, False otherwise.
        """
        allowed = VALID_TRANSITIONS.get(self._status.state, set())
        return target in allowed

    async def transition_to(self, target: ColonyState) -> ColonyStatus:
        """Transition the colony to a new lifecycle state.

        Args:
            target: The target state to transition to.

        Returns:
            The updated colony status.

        Raises:
            InvalidStateTransition: If the transition is not valid.
        """
        if not self.can_transition_to(target):
            raise InvalidStateTransition(
                f"Cannot transition from {self._status.state.value} "
                f"to {target.value}"
            )

        previous = self._status.state
        self._status.previous_state = previous
        self._status.state = target
        self._status.last_state_change = datetime.now(timezone.utc)

        self._state_history.append({
            "from": previous.value,
            "to": target.value,
            "timestamp": self._status.last_state_change.isoformat(),
        })

        self._log.info(
            "colony_state_transition",
            from_state=previous.value,
            to_state=target.value,
        )

        return self._status

    async def initialize(self) -> ColonyStatus:
        """Initialize the colony lifecycle.

        Sets the colony to INITIALIZING state and records the start time.

        Returns:
            The initial colony status.
        """
        self._status.state = ColonyState.INITIALIZING
        self._initialized_at = datetime.now(timezone.utc)
        self._status.last_state_change = self._initialized_at
        self._log.info("colony_initializing")
        return self._status

    async def mark_running(self) -> ColonyStatus:
        """Mark the colony as running.

        Returns:
            The updated colony status.
        """
        return await self.transition_to(ColonyState.RUNNING)

    async def mark_idle(self) -> ColonyStatus:
        """Mark the colony as idle (no pending tasks).

        Returns:
            The updated colony status.
        """
        return await self.transition_to(ColonyState.IDLE)

    async def start_scaling(self) -> ColonyStatus:
        """Mark the colony as scaling (adjusting agent count).

        Returns:
            The updated colony status.
        """
        return await self.transition_to(ColonyState.SCALING)

    async def finish_scaling(self) -> ColonyStatus:
        """Mark the colony as done scaling, return to running.

        Returns:
            The updated colony status.
        """
        return await self.transition_to(ColonyState.RUNNING)

    async def hibernate(self) -> ColonyStatus:
        """Put the colony into hibernation (low-power mode).

        Returns:
            The updated colony status.
        """
        return await self.transition_to(ColonyState.HIBERNATING)

    async def wake(self) -> ColonyStatus:
        """Wake the colony from hibernation.

        Returns:
            The updated colony status.
        """
        return await self.transition_to(ColonyState.RUNNING)

    async def terminate(self) -> ColonyStatus:
        """Terminate the colony.

        Returns:
            The updated colony status.
        """
        return await self.transition_to(ColonyState.TERMINATING)

    async def mark_failed(self, error_message: str = "") -> ColonyStatus:
        """Mark the colony as failed.

        Args:
            error_message: Description of the failure.

        Returns:
            The updated colony status.
        """
        self._status.error_message = error_message
        try:
            return await self.transition_to(ColonyState.FAILED)
        except InvalidStateTransition:
            # Force the transition for failures
            self._status.previous_state = self._status.state
            self._status.state = ColonyState.FAILED
            self._status.last_state_change = datetime.now(timezone.utc)
            self._log.error("colony_force_failed", error=error_message)
            return self._status

    def update_metrics(
        self,
        agent_count: int | None = None,
        task_count: int | None = None,
        memory_usage_mb: float | None = None,
    ) -> ColonyStatus:
        """Update colony metrics in the status.

        Args:
            agent_count: Updated agent count.
            task_count: Updated task count.
            memory_usage_mb: Updated memory usage.

        Returns:
            The updated colony status.
        """
        if agent_count is not None:
            self._status.agent_count = agent_count
        if task_count is not None:
            self._status.task_count = task_count
        if memory_usage_mb is not None:
            self._status.memory_usage_mb = memory_usage_mb

        if self._initialized_at is not None:
            delta = datetime.now(timezone.utc) - self._initialized_at
            self._status.uptime_seconds = delta.total_seconds()

        return self._status

    def get_state_history(self) -> list[dict[str, Any]]:
        """Get the history of all state transitions.

        Returns:
            A list of state transition records.
        """
        return list(self._state_history)


class InvalidStateTransition(Exception):
    """Raised when an invalid colony state transition is attempted."""
