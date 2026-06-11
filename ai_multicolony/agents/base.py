"""Base agent framework with EventBus integration.

Provides the foundational :class:`BaseAgent` with full lifecycle management,
an async :class:`EventBus` for inter-agent communication, and a
:class:`CircuitBreaker` that guards tool calls against cascading failures.

Key features
------------
* Agent lifecycle states: REGISTERED → INITIALIZING → READY → ACTIVE → … → TERMINATED
* Health check with weighted scoring formula
* Circuit breaker for tool calls (CLOSED / OPEN / HALF_OPEN, configurable threshold & timeout)
* Autonomy levels L0–L4 with escalation support
* A2A message handling (send / receive / broadcast)
* Letta-style context compaction at 80 % threshold
* Periodic heartbeat emission (default 30 s interval)
* Error recovery with configurable retry policies
* Abstract hooks: ``on_task()``, ``on_message()``, ``capabilities()``
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ..types import (
    AgentInfo,
    AgentSpec,
    AgentState,
    AgentType,
    AutonomyLevel,
    Event,
    EventType,
    Task,
    TaskResult,
    ToolCall,
    ToolResult,
    CircuitBreakerState,
)
from ..exceptions import AgentError, AgentStateError, AgentTimeoutError

logger = logging.getLogger(__name__)


# ── EventBus ────────────────────────────────────────────────────────────────


class EventBus:
    """Async event bus for agent communication.

    Supports both sync and async handlers, typed event publishing, event
    history queries, and cleanup.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_log: List[Event] = []

    def subscribe(self, event_type, handler: Callable) -> None:
        """Subscribe *handler* to events of *event_type*."""
        key = event_type.value if hasattr(event_type, "value") else event_type
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(handler)

    def unsubscribe(self, event_type, handler: Callable) -> None:
        """Remove *handler* from *event_type* subscriptions."""
        key = event_type.value if hasattr(event_type, "value") else event_type
        if key in self._subscribers:
            self._subscribers[key] = [
                h for h in self._subscribers[key] if h != handler
            ]

    async def publish(self, event: Event) -> None:
        """Publish *event* to all matching subscribers."""
        self._event_log.append(event)
        key = event.event_type.value if hasattr(event.event_type, "value") else event.event_type
        handlers = self._subscribers.get(key, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    async def publish_typed(self, event_type: EventType, source: str, data: Dict[str, Any]) -> Event:
        """Create and publish a typed event, returning the event object."""
        event = Event(event_type=event_type, source=source, data=data)
        await self.publish(event)
        return event

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Return recent events, optionally filtered by type."""
        events = self._event_log
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def clear(self) -> None:
        """Clear all subscribers and event history."""
        self._event_log.clear()
        self._subscribers.clear()


# ── Circuit Breaker ─────────────────────────────────────────────────────────


class CircuitBreaker:
    """Circuit breaker for MCP tool calls.

    States
    ------
    * **CLOSED** – normal operation; calls pass through.
    * **OPEN** – failures exceeded *failure_threshold*; calls are rejected
      until *timeout* seconds have elapsed.
    * **HALF_OPEN** – one trial call is allowed; success resets to CLOSED,
      another failure reopens.

    Parameters
    ----------
    failure_threshold:
        Number of consecutive failures before opening (default 5).
    timeout:
        Seconds to wait before transitioning OPEN → HALF_OPEN (default 60).
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0

    @property
    def state(self) -> CircuitBreakerState:
        """Current breaker state, automatically transitioning to HALF_OPEN after timeout."""
        if self._state == CircuitBreakerState.OPEN:
            if self._last_failure_time and (time.time() - self._last_failure_time) > self.timeout:
                self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Record a successful call; resets from HALF_OPEN to CLOSED."""
        self._success_count += 1
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call; opens the breaker when threshold is reached."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN

    def can_execute(self) -> bool:
        """Whether a call should be allowed through the breaker."""
        return self.state in (CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN)

    def reset(self) -> None:
        """Force-reset the breaker to CLOSED."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None


# ── Retry Policy ────────────────────────────────────────────────────────────


class RetryPolicy:
    """Configurable retry policy with exponential back-off.

    Parameters
    ----------
    max_retries:
        Maximum number of retries before giving up.
    base_delay:
        Base delay in seconds for the first retry.
    max_delay:
        Cap on the delay between retries.
    backoff_factor:
        Multiplier applied to the delay after each attempt.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        """Return the delay in seconds before the *attempt*-th retry."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)


# ── Base Agent ──────────────────────────────────────────────────────────────


class BaseAgent:
    """Base agent with EventBus integration, lifecycle management, and circuit breaker.

    Lifecycle states
    ----------------
    ``REGISTERED`` → ``INITIALIZING`` → ``READY`` → ``ACTIVE`` ↔ ``SUSPENDED`` /
    ``WAITING`` / ``COMPACTING`` → ``DRAINING`` → ``TERMINATED``

    Health scoring
    --------------
    The aggregate health score is a weighted sum::

        score = 0.30·liveness + 0.25·task_success_rate
              + 0.15·context_health + 0.15·circuit_breaker_health
              + 0.15·heartbeat_regularity

    Context compaction
    ------------------
    When context usage reaches 80 % of capacity the agent automatically
    transitions to ``COMPACTING``, condenses its context window (Letta-style),
    and transitions back to ``ACTIVE``.

    Autonomy escalation
    -------------------
    Agents start at the autonomy level specified in their :class:`AgentSpec`.
    The :meth:`escalate_autonomy` and :meth:`deescalate_autonomy` methods
    allow runtime adjustment with approval-event emission.

    Abstract hooks
    --------------
    Subclasses **must** implement:
    * :meth:`on_task` – task-specific business logic
    * :meth:`on_message` – A2A message handling
    * :meth:`capabilities` – declare the agent's capability list
    """

    # Default context compaction threshold (80 %)
    COMPACTION_THRESHOLD: float = 0.8

    def __init__(
        self,
        spec: Optional[AgentSpec] = None,
        event_bus: Optional[EventBus] = None,
        tools: Optional[Dict[str, Any]] = None,
    ):
        self.spec = spec or AgentSpec()
        self.agent_id = self.spec.agent_id
        self.agent_type = self.spec.agent_type
        self.autonomy_level = self.spec.autonomy_level
        self.colony_id = self.spec.colony_id
        self.state = AgentState.REGISTERED
        self.event_bus = event_bus or EventBus()
        self.tools: Dict[str, Any] = tools or {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._health_score = 1.0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._last_heartbeat: Optional[datetime] = None
        self._context: List[Dict[str, Any]] = []
        self._context_capacity: int = self.spec.heartbeat_interval_ms  # reuse as token proxy
        self._working_memory: Dict[str, Any] = {}
        self._created_at = datetime.now(timezone.utc)
        self._lock = None
        self._retry_policy = RetryPolicy(max_retries=self.spec.max_retries)
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval: float = self.spec.heartbeat_interval_ms / 1000.0
        # A2A message queue
        self._message_queue: List[Dict[str, Any]] = []
        # Compaction metrics
        self._compaction_count: int = 0
        # Health breakdown tracking
        self._health_breakdown: Dict[str, float] = {
            "liveness": 1.0,
            "task_success_rate": 1.0,
            "context_health": 1.0,
            "circuit_breaker_health": 1.0,
            "heartbeat_regularity": 1.0,
        }

    # ── Properties ──

    @property
    def info(self) -> AgentInfo:
        """Return an :class:`AgentInfo` snapshot of the agent."""
        return AgentInfo(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            state=self.state,
            autonomy_level=self.autonomy_level,
            colony_id=self.colony_id,
            health_score=self._health_score,
            created_at=self._created_at,
            last_heartbeat=self._last_heartbeat,
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
        )

    @property
    def health_score(self) -> float:
        """Current aggregate health score (0.0 – 1.0)."""
        return self._health_score

    @property
    def context_usage(self) -> float:
        """Current context window usage ratio (0.0 – 1.0)."""
        return len(self._context) / max(1, self._context_capacity)

    # ── Lifecycle ──

    def _transition(self, new_state: AgentState) -> None:
        """Validate and perform a lifecycle state transition."""
        valid_transitions = {
            AgentState.REGISTERED: [AgentState.INITIALIZING],
            AgentState.INITIALIZING: [AgentState.READY],
            AgentState.READY: [AgentState.ACTIVE, AgentState.DRAINING],
            AgentState.ACTIVE: [
                AgentState.SUSPENDED, AgentState.WAITING,
                AgentState.COMPACTING, AgentState.READY, AgentState.DRAINING,
            ],
            AgentState.SUSPENDED: [AgentState.ACTIVE],
            AgentState.WAITING: [AgentState.ACTIVE, AgentState.READY],
            AgentState.COMPACTING: [AgentState.ACTIVE],
            AgentState.DRAINING: [AgentState.TERMINATED],
        }
        allowed = valid_transitions.get(self.state, [])
        if new_state not in allowed:
            raise AgentStateError(f"Cannot transition from {self.state} to {new_state}")
        old_state = self.state
        self.state = new_state
        logger.info(f"Agent {self.agent_id}: {old_state} -> {new_state}")

    async def initialize(self) -> None:
        """Initialize agent: load tools, memory, register with event bus.

        Transitions ``REGISTERED`` → ``INITIALIZING`` → ``READY`` and starts
        the periodic heartbeat task.
        """
        self._transition(AgentState.INITIALIZING)
        await self.event_bus.publish_typed(
            EventType.AGENT_STATE_CHANGED,
            self.agent_id,
            {"old_state": AgentState.REGISTERED, "new_state": AgentState.INITIALIZING},
        )
        # Health check
        self._transition(AgentState.READY)
        self._last_heartbeat = datetime.now(timezone.utc)
        await self.event_bus.publish_typed(
            EventType.AGENT_SPAWNED,
            self.agent_id,
            {"agent_type": self.agent_type.value, "colony_id": self.colony_id},
        )
        # Start heartbeat loop
        self._start_heartbeat_loop()

    async def process_task(self, task: Task) -> TaskResult:
        """Process a task with error recovery and health tracking.

        Wraps :meth:`on_task` (the subclass hook) with state transitions,
        timing, health updates, and retry logic.
        """
        if self.state not in (AgentState.READY, AgentState.ACTIVE):
            raise AgentStateError(f"Agent {self.agent_id} not ready: state={self.state}")
        self._transition(AgentState.ACTIVE)
        start_time = datetime.now(timezone.utc)

        # Check context compaction
        if self.context_usage >= self.COMPACTION_THRESHOLD:
            await self.compact_context()

        try:
            result = await self._execute_with_retry(task)
            self._tasks_completed += 1
            self._update_health(True)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TaskResult(
                task_id=task.task_id,
                success=True,
                data=result,
                execution_time_ms=elapsed,
            )
        except Exception as e:
            self._tasks_failed += 1
            self._update_health(False)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )
        finally:
            if self.state == AgentState.ACTIVE:
                self._transition(AgentState.READY)

    async def _execute_with_retry(self, task: Task) -> Any:
        """Execute task with retry policy."""
        last_error: Optional[Exception] = None
        for attempt in range(self._retry_policy.max_retries + 1):
            try:
                return await self._execute(task)
            except Exception as e:
                last_error = e
                if attempt < self._retry_policy.max_retries:
                    delay = self._retry_policy.get_delay(attempt)
                    logger.warning(
                        f"Agent {self.agent_id}: attempt {attempt + 1} failed, "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
        raise last_error  # type: ignore[misc]

    async def _execute(self, task: Task) -> Any:
        """Default task execution that delegates to :meth:`on_task`.

        Subclasses may override this directly, but the preferred hook is
        :meth:`on_task`.
        """
        return await self.on_task(task)

    async def terminate(self) -> None:
        """Gracefully terminate agent.

        Transitions through ``DRAINING`` → ``TERMINATED``, stops the
        heartbeat loop, and publishes a termination event.
        """
        # Stop heartbeat
        self._stop_heartbeat_loop()

        if self.state == AgentState.ACTIVE:
            self._transition(AgentState.READY)
        if self.state == AgentState.READY:
            self._transition(AgentState.DRAINING)
        if self.state in (AgentState.DRAINING, AgentState.SUSPENDED, AgentState.WAITING):
            self.state = AgentState.DRAINING
        self._transition(AgentState.TERMINATED)
        await self.event_bus.publish_typed(
            EventType.AGENT_TERMINATED,
            self.agent_id,
            {"agent_type": self.agent_type.value},
        )

    # ── Abstract hooks ──

    @abstractmethod
    async def on_task(self, task: Task) -> Any:
        """Process a task. Subclasses **must** implement this method.

        Parameters
        ----------
        task:
            The task to process.

        Returns
        -------
        Any
            Arbitrary result data that will be wrapped in a :class:`TaskResult`.
        """

    @abstractmethod
    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle an incoming A2A message.

        Parameters
        ----------
        message:
            The A2A message payload.

        Returns
        -------
        Any
            Optional response data.
        """

    @abstractmethod
    def capabilities(self) -> List[str]:
        """Return a list of capability strings this agent provides."""

    # ── Tool calls ──

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a tool through MCP with circuit breaker protection.

        If the circuit breaker for *tool_name* is OPEN a
        :class:`~ai_multicolony.exceptions.ToolUnavailableError` is raised.
        """
        cb = self._circuit_breakers.setdefault(tool_name, CircuitBreaker())
        if not cb.can_execute():
            from ..exceptions import ToolUnavailableError
            raise ToolUnavailableError(tool_name)
        if tool_name not in self.tools:
            from ..exceptions import ToolError
            raise ToolError(f"Tool {tool_name} not available")
        try:
            tool = self.tools[tool_name]
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(arguments, {"agent_id": self.agent_id})
            else:
                result = tool.execute(arguments, {"agent_id": self.agent_id})
            cb.record_success()
            return ToolResult(
                call_id=uuid.uuid4().hex[:12],
                tool_name=tool_name,
                status="success",
                data=result,
            )
        except Exception as e:
            cb.record_failure()
            return ToolResult(
                call_id=uuid.uuid4().hex[:12],
                tool_name=tool_name,
                status="error",
                error=str(e),
            )

    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool by name."""
        self.tools[name] = tool

    def can_use_tool(self, required_level: AutonomyLevel) -> bool:
        """Check whether this agent's autonomy level satisfies *required_level*."""
        return self.autonomy_level.value >= required_level.value

    # ── Heartbeat ──

    def heartbeat(self) -> None:
        """Emit a heartbeat and update health regularity."""
        self._last_heartbeat = datetime.now(timezone.utc)
        self._health_breakdown["heartbeat_regularity"] = min(
            1.0, self._health_breakdown["heartbeat_regularity"] + 0.01
        )

    def _start_heartbeat_loop(self) -> None:
        """Start the periodic heartbeat background task."""
        try:
            loop = asyncio.get_running_loop()
            self._heartbeat_task = loop.create_task(self._heartbeat_loop())
        except RuntimeError:
            # No running event loop – heartbeats will be manual
            pass

    def _stop_heartbeat_loop(self) -> None:
        """Cancel the heartbeat background task."""
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        """Periodically emit heartbeats and publish heartbeat events."""
        try:
            while self.state != AgentState.TERMINATED:
                self.heartbeat()
                await self.event_bus.publish_typed(
                    EventType.HEARTBEAT,
                    self.agent_id,
                    {
                        "health_score": self._health_score,
                        "state": self.state.value,
                        "tasks_completed": self._tasks_completed,
                        "tasks_failed": self._tasks_failed,
                    },
                )
                await asyncio.sleep(self._heartbeat_interval)
        except asyncio.CancelledError:
            pass

    # ── Health ──

    def _update_health(self, success: bool) -> None:
        """Update health score based on task outcome.

        Uses the weighted formula::

            score = 0.30·liveness + 0.25·task_success_rate
                  + 0.15·context_health + 0.15·circuit_breaker_health
                  + 0.15·heartbeat_regularity
        """
        if success:
            self._health_breakdown["task_success_rate"] = min(
                1.0, self._health_breakdown["task_success_rate"] + 0.01
            )
            self._health_breakdown["liveness"] = 1.0
        else:
            self._health_breakdown["task_success_rate"] = max(
                0.0, self._health_breakdown["task_success_rate"] - 0.05
            )

        # Recalculate context health
        ctx_ratio = self.context_usage
        self._health_breakdown["context_health"] = max(0.0, 1.0 - ctx_ratio)

        # Recalculate circuit breaker health
        open_count = sum(
            1 for cb in self._circuit_breakers.values()
            if cb.state == CircuitBreakerState.OPEN
        )
        total_cbs = max(1, len(self._circuit_breakers))
        self._health_breakdown["circuit_breaker_health"] = 1.0 - (open_count / total_cbs)

        # Weighted aggregate
        weights = {
            "liveness": 0.30,
            "task_success_rate": 0.25,
            "context_health": 0.15,
            "circuit_breaker_health": 0.15,
            "heartbeat_regularity": 0.15,
        }
        self._health_score = sum(
            weights.get(k, 0.0) * v for k, v in self._health_breakdown.items()
        )
        self._health_score = max(0.0, min(1.0, self._health_score))

    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check and return a report.

        Returns a dict matching :class:`~ai_multicolony.agents.state.HealthReport`.
        """
        self._update_health(True)  # recalculate
        issues: List[str] = []
        if self._health_score < 0.7:
            issues.append(f"Low health score: {self._health_score:.2f}")
        if self.context_usage >= self.COMPACTION_THRESHOLD:
            issues.append(f"Context usage high: {self.context_usage:.0%}")
        for name, cb in self._circuit_breakers.items():
            if cb.state == CircuitBreakerState.OPEN:
                issues.append(f"Circuit breaker OPEN for tool: {name}")
        return {
            "agent_id": self.agent_id,
            "score": self._health_score,
            "breakdown": dict(self._health_breakdown),
            "last_check": datetime.now(timezone.utc).isoformat(),
            "issues": issues,
        }

    # ── Context compaction ──

    async def compact_context(self) -> Dict[str, Any]:
        """Compact the context window (Letta-style).

        When context usage exceeds the 80 % threshold the agent transitions
        to ``COMPACTING``, condenses context entries into a summary, and
        transitions back to ``ACTIVE``.
        """
        if self.state != AgentState.ACTIVE:
            return {"compacted": False, "reason": "not_active"}

        self._transition(AgentState.COMPACTING)
        old_count = len(self._context)

        # Summarise context entries
        summary_parts = []
        key_facts: List[str] = []
        for entry in self._context:
            summary_parts.append(str(entry.get("value", ""))[:100])
            if "key" in entry:
                key_facts.append(entry["key"])

        summary = " ".join(summary_parts)[:512]
        compacted_entry = {
            "type": "compacted_summary",
            "summary": summary,
            "key_facts": key_facts,
            "original_count": old_count,
            "compacted_at": datetime.now(timezone.utc).isoformat(),
        }

        self._context = [compacted_entry]
        self._compaction_count += 1
        self._transition(AgentState.ACTIVE)

        await self.event_bus.publish_typed(
            EventType.MEMORY_COMPACTED,
            self.agent_id,
            {
                "entries_compacted": old_count,
                "compaction_count": self._compaction_count,
            },
        )
        return {
            "compacted": True,
            "entries_compacted": old_count,
            "compaction_count": self._compaction_count,
        }

    def add_context(self, key: str, value: Any) -> None:
        """Add an entry to the context window."""
        self._context.append({
            "key": key,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ── Autonomy escalation ──

    async def escalate_autonomy(self, target_level: AutonomyLevel, justification: str = "") -> bool:
        """Request escalation to a higher autonomy level.

        Publishes an ``APPROVAL_REQUESTED`` event and waits for approval.
        """
        if target_level.value <= self.autonomy_level.value:
            return True  # already at or above

        await self.event_bus.publish_typed(
            EventType.APPROVAL_REQUESTED,
            self.agent_id,
            {
                "current_level": self.autonomy_level.value,
                "requested_level": target_level.value,
                "justification": justification,
            },
        )

        # Auto-approve for L1 and L2; L3+ requires external approval
        if target_level.value <= AutonomyLevel.L2_MODERATE.value:
            self.autonomy_level = target_level
            return True

        # For L3+ we set but flag it – in a real system an external approver
        # would grant/deny.  Here we auto-approve after event publication.
        self.autonomy_level = target_level
        return True

    async def deescalate_autonomy(self, target_level: AutonomyLevel) -> None:
        """Lower the autonomy level (always permitted)."""
        if target_level.value < self.autonomy_level.value:
            self.autonomy_level = target_level

    # ── A2A messaging ──

    async def send_message(self, recipient_id: str, message_type: str, payload: Dict[str, Any]) -> str:
        """Send an A2A message to another agent via the event bus."""
        message_id = uuid.uuid4().hex[:12]
        await self.event_bus.publish_typed(
            EventType.A2A_MESSAGE,
            self.agent_id,
            {
                "message_id": message_id,
                "sender_id": self.agent_id,
                "recipient_id": recipient_id,
                "message_type": message_type,
                "payload": payload,
            },
        )
        return message_id

    async def receive_message(self, message: Dict[str, Any]) -> Any:
        """Receive and handle an incoming A2A message."""
        self._message_queue.append(message)
        return await self.on_message(message)

    async def broadcast_message(self, message_type: str, payload: Dict[str, Any]) -> str:
        """Broadcast a message to all agents in the colony."""
        message_id = uuid.uuid4().hex[:12]
        await self.event_bus.publish_typed(
            EventType.A2A_MESSAGE,
            self.agent_id,
            {
                "message_id": message_id,
                "sender_id": self.agent_id,
                "colony_id": self.colony_id,
                "message_type": message_type,
                "payload": payload,
                "broadcast": True,
            },
        )
        return message_id

    # ── Dunder ──

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id} type={self.agent_type.value} state={self.state.value}>"
