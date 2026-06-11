"""Task scheduler for colony task management.

Features:
* Priority queue (critical / high / medium / low)
* Deadline tracking with timeout enforcement
* Capability-based routing (least-loaded, round-robin, capability-match)
* Exponential back-off retry
* Task result collection
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from ..types import (
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
    TaskDeadline,
    RoutingStrategy,
    HandType,
)
from ..exceptions import AgentTimeoutError

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Priority-based task scheduler with routing, retry, and timeout support.

    The scheduler maintains a priority queue of pending tasks, a set of
    running tasks, and a record of completed tasks.  It routes tasks to
    agents based on the chosen strategy, retries failures with exponential
    back-off, and enforces deadlines.
    """

    def __init__(
        self,
        max_concurrent: int = 20,
        routing_strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED,
        default_timeout_ms: int = 300_000,
        default_max_retries: int = 3,
        retry_base_delay_ms: int = 1_000,
        retry_max_delay_ms: int = 60_000,
    ):
        self.max_concurrent = max_concurrent
        self.routing_strategy = routing_strategy
        self.default_timeout_ms = default_timeout_ms
        self.default_max_retries = default_max_retries
        self.retry_base_delay_ms = retry_base_delay_ms
        self.retry_max_delay_ms = retry_max_delay_ms

        # Priority queue: (-priority_value, counter, task)
        self._queue: List[tuple] = []
        self._counter: int = 0

        # Running & completed
        self._running: Dict[str, Task] = {}
        self._completed: Dict[str, Task] = {}
        self._results: Dict[str, TaskResult] = {}

        # Agent tracking for routing
        self._agent_load: Dict[str, int] = {}  # agent_id → task count
        self._agent_caps: Dict[str, List[str]] = {}  # agent_id → capabilities
        self._rr_agents: List[str] = []
        self._rr_index: int = 0

        # Deadline tracking
        self._deadlines: Dict[str, datetime] = {}  # task_id → absolute deadline

    # ── Submit ─────────────────────────────────────────────────────────────

    def submit(self, task: Task) -> str:
        """Submit a task to the priority queue.

        Returns the task_id.
        """
        if task.max_retries <= 0:
            task.max_retries = self.default_max_retries
        if task.timeout_ms <= 0:
            task.timeout_ms = self.default_timeout_ms

        self._counter += 1
        heapq.heappush(self._queue, (-task.priority.value, self._counter, task))
        task.status = TaskStatus.PENDING

        # Track deadline
        if task.deadline:
            if task.deadline.absolute:
                self._deadlines[task.task_id] = task.deadline.absolute
            elif task.deadline.relative_ms:
                self._deadlines[task.task_id] = datetime.now(timezone.utc) + timedelta(milliseconds=task.deadline.relative_ms)

        logger.debug("Task %s submitted (priority=%s)", task.task_id, task.priority.name)
        return task.task_id

    # ── Next task ──────────────────────────────────────────────────────────

    def next_task(self) -> Optional[Task]:
        """Pop the highest-priority pending task.

        Skips tasks that have been cancelled or timed out.
        """
        while self._queue:
            _, _, task = heapq.heappop(self._queue)
            if task.status == TaskStatus.PENDING:
                # Check deadline
                deadline = self._deadlines.get(task.task_id)
                if deadline and datetime.now(timezone.utc) > deadline:
                    task.status = TaskStatus.TIMED_OUT
                    task.error = "Deadline exceeded before assignment"
                    self._completed[task.task_id] = task
                    continue
                task.status = TaskStatus.ASSIGNED
                self._running[task.task_id] = task
                task.started_at = datetime.now(timezone.utc)
                return task
        return None

    def peek(self) -> Optional[Task]:
        """Peek at the highest-priority task without removing it."""
        for _, _, task in sorted(self._queue):
            if task.status == TaskStatus.PENDING:
                return task
        return None

    # ── Routing ────────────────────────────────────────────────────────────

    def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """Register an agent for routing decisions."""
        self._agent_load[agent_id] = 0
        self._agent_caps[agent_id] = capabilities
        if agent_id not in self._rr_agents:
            self._rr_agents.append(agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from routing consideration."""
        self._agent_load.pop(agent_id, None)
        self._agent_caps.pop(agent_id, None)
        if agent_id in self._rr_agents:
            self._rr_agents.remove(agent_id)

    def route_task(self, task: Task) -> Optional[str]:
        """Select the best agent for a task using the configured strategy.

        Strategies:
        * ``least-loaded``  – pick the agent with fewest running tasks
        * ``round-robin``   – cycle through agents in order
        * ``capability-match`` – prefer agents whose capabilities overlap
          with ``task.required_capabilities``, then least-loaded

        Returns the chosen agent_id, or ``None`` if no agents are available.
        """
        if not self._agent_load:
            return None

        if self.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin()
        elif self.routing_strategy == RoutingStrategy.CAPABILITY_MATCH:
            return self._route_capability_match(task)
        else:
            return self._route_least_loaded()

    def _route_least_loaded(self) -> Optional[str]:
        """Pick the agent with the lowest current load."""
        if not self._agent_load:
            return None
        return min(self._agent_load, key=lambda a: self._agent_load.get(a, 0))

    def _route_round_robin(self) -> Optional[str]:
        """Cycle through available agents."""
        if not self._rr_agents:
            return None
        agent_id = self._rr_agents[self._rr_index % len(self._rr_agents)]
        self._rr_index += 1
        return agent_id

    def _route_capability_match(self, task: Task) -> Optional[str]:
        """Prefer agents whose capabilities match the task requirements."""
        required = set(task.required_capabilities)
        if not required:
            return self._route_least_loaded()

        best_agents: List[str] = []
        best_overlap = 0
        for agent_id, caps in self._agent_caps.items():
            overlap = len(required & set(caps))
            if overlap > best_overlap:
                best_overlap = overlap
                best_agents = [agent_id]
            elif overlap == best_overlap and overlap > 0:
                best_agents.append(agent_id)

        if not best_agents:
            return self._route_least_loaded()

        # Among agents with the same overlap, pick least loaded
        return min(best_agents, key=lambda a: self._agent_load.get(a, 0))

    # ── Task lifecycle ─────────────────────────────────────────────────────

    def start_task(self, task_id: str, agent_id: str) -> None:
        """Mark a task as running on a specific agent."""
        task = self._running.get(task_id)
        if task:
            task.assigned_agent = agent_id
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            self._agent_load[agent_id] = self._agent_load.get(agent_id, 0) + 1

    def complete_task(self, task_id: str, result: Any = None, error: Optional[str] = None) -> TaskResult:
        """Mark a task as completed or failed and record the result.

        If the task failed and retries remain, it is rescheduled with
        exponential back-off.
        """
        task = self._running.pop(task_id, None)
        if task is None:
            return TaskResult(task_id=task_id, success=False, error="Task not found in running set")

        # Decrement agent load
        if task.assigned_agent:
            load = self._agent_load.get(task.assigned_agent, 0)
            self._agent_load[task.assigned_agent] = max(0, load - 1)

        if error and task.retry_count < task.max_retries:
            # Retry with exponential back-off
            task.retry_count += 1
            delay_ms = min(
                self.retry_base_delay_ms * (2 ** (task.retry_count - 1)),
                self.retry_max_delay_ms,
            )
            task.status = TaskStatus.RETRYING
            task.error = error
            logger.info("Task %s retry %d/%d (delay=%dms)", task_id, task.retry_count, task.max_retries, delay_ms)
            # Re-queue after back-off (caller should handle the delay)
            self._counter += 1
            heapq.heappush(self._queue, (-task.priority.value, self._counter, task))
            task.status = TaskStatus.PENDING  # will be picked up again

            return TaskResult(
                task_id=task_id,
                success=False,
                error=f"Retry {task.retry_count}/{task.max_retries}: {error}",
                retry_count=task.retry_count,
            )

        # Final completion
        is_success = error is None
        task.status = TaskStatus.COMPLETED if is_success else TaskStatus.FAILED
        task.result = result
        task.error = error
        task.completed_at = datetime.now(timezone.utc)
        self._completed[task_id] = task

        task_result = TaskResult(
            task_id=task_id,
            success=is_success,
            data=result,
            error=error,
            agent_id=task.assigned_agent,
            colony_id=task.colony_id,
            retry_count=task.retry_count,
        )
        if task.started_at and task.completed_at:
            delta = (task.completed_at - task.started_at).total_seconds() * 1000
            task_result.execution_time_ms = delta

        self._results[task_id] = task_result
        return task_result

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        task = self._running.pop(task_id, None)
        if task:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
            self._completed[task_id] = task
            if task.assigned_agent:
                load = self._agent_load.get(task.assigned_agent, 0)
                self._agent_load[task.assigned_agent] = max(0, load - 1)
            return True
        # Also try to remove from queue
        for i, (pri, cnt, t) in enumerate(self._queue):
            if t.task_id == task_id:
                self._queue.pop(i)
                heapq.heapify(self._queue)
                t.status = TaskStatus.CANCELLED
                self._completed[task_id] = t
                return True
        return False

    # ── Deadline & timeout enforcement ─────────────────────────────────────

    def check_timeouts(self) -> List[str]:
        """Check running tasks for deadline/timeout violations.

        Returns a list of task_ids that have timed out.
        """
        now = datetime.now(timezone.utc)
        timed_out: List[str] = []

        for task_id, task in list(self._running.items()):
            # Absolute deadline
            deadline = self._deadlines.get(task_id)
            if deadline and now > deadline:
                timed_out.append(task_id)
                continue

            # Relative timeout from start
            if task.started_at:
                elapsed_ms = (now - task.started_at).total_seconds() * 1000
                if elapsed_ms > task.timeout_ms:
                    timed_out.append(task_id)

        for task_id in timed_out:
            self.complete_task(task_id, error="Task timed out")

        return timed_out

    # ── Result collection ──────────────────────────────────────────────────

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve the result of a completed task."""
        return self._results.get(task_id)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID (from any state)."""
        task = self._running.get(task_id) or self._completed.get(task_id)
        if task:
            return task
        for _, _, t in self._queue:
            if t.task_id == task_id:
                return t
        return None

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Return the status of a task."""
        task = self.get_task(task_id)
        return task.status if task else None

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self._completed.values() if t.status == TaskStatus.FAILED)

    def get_stats(self) -> Dict[str, Any]:
        """Return scheduler statistics."""
        return {
            "pending": self.pending_count,
            "running": self.running_count,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "max_concurrent": self.max_concurrent,
            "routing_strategy": self.routing_strategy.value,
            "registered_agents": len(self._agent_load),
        }
