"""Event type definitions for the AI MultiColony Ecosystem.

Merges OpenHands Action/Observation pattern with Nanobot event types.
Defines EventType, Action, Observation, Event, and EventStream.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from enum import Enum
from typing import Any, AsyncIterator, Callable, Coroutine, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Top-level event types in the system."""

    ACTION = "action"
    OBSERVATION = "observation"
    SYSTEM = "system"
    ERROR = "error"
    LIFECYCLE = "lifecycle"
    CUSTOM = "custom"


class ActionType(str, Enum):
    """Types of actions an agent can take."""

    # Core actions
    THINK = "think"
    MESSAGE = "message"
    DELEGATE = "delegate"

    # Tool actions
    RUN_COMMAND = "run_command"
    RUN_CODE = "run_code"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    BROWSE_URL = "browse_url"
    CLICK_ELEMENT = "click_element"
    TYPE_TEXT = "type_text"
    SCROLL_PAGE = "scroll_page"
    SEARCH_WEB = "search_web"

    # Communication actions
    SEND_MESSAGE = "send_message"
    BROADCAST = "broadcast"
    SPAWN_AGENT = "spawn_agent"
    KILL_AGENT = "kill_agent"

    # Memory actions
    STORE_MEMORY = "store_memory"
    RECALL_MEMORY = "recall_memory"
    CONDENSE_MEMORY = "condense_memory"

    # Colony actions
    ASSIGN_TASK = "assign_task"
    REPORT_STATUS = "report_status"
    REQUEST_RESOURCE = "request_resource"


class ObservationType(str, Enum):
    """Types of observations an agent can receive."""

    # Core observations
    THOUGHT = "thought"
    ERROR = "error"
    SUCCESS = "success"
    AGENT_STATE_CHANGED = "agent_state_changed"

    # Tool observations
    COMMAND_OUTPUT = "command_output"
    COMMAND_ERROR = "command_error"
    CODE_OUTPUT = "code_output"
    CODE_ERROR = "code_error"
    FILE_CONTENT = "file_content"
    FILE_LISTING = "file_listing"
    BROWSER_PAGE = "browser_page"
    BROWSER_ERROR = "browser_error"
    SEARCH_RESULTS = "search_results"

    # Communication observations
    MESSAGE_RECEIVED = "message_received"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_TERMINATED = "agent_terminated"

    # Memory observations
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_CONDENSED = "memory_condensed"

    # Colony observations
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    STATUS_REPORT = "status_report"
    RESOURCE_GRANTED = "resource_granted"


class Action(BaseModel):
    """An action taken by an agent.

    Following OpenHands Action pattern with additional metadata.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType
    agent_id: str
    timestamp: float = Field(default_factory=time.time)
    thought: Optional[str] = None
    args: dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None
    parent_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class Observation(BaseModel):
    """An observation received by an agent.

    Following OpenHands Observation pattern.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    observation_type: ObservationType
    agent_id: str
    action_id: str = ""
    timestamp: float = Field(default_factory=time.time)
    content: str = ""
    success: bool = True
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class Event(BaseModel):
    """A general event in the system.

    Can represent an action or an observation, used by the event bus.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.CUSTOM
    source: str = "system"
    timestamp: float = Field(default_factory=time.time)
    data: dict[str, Any] = Field(default_factory=dict)
    action: Optional[Action] = None
    observation: Optional[Observation] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventStream:
    """An asynchronous stream of events with filtering support.

    Provides a pub/sub interface for consuming events from the
    event bus with optional type-based filtering.
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._history: list[Event] = []
        self._max_history = max_history
        self._filters: list[Callable[[Event], bool]] = []
        self._subscribers: list[EventHandler] = []
        self._closed = False

    async def publish(self, event: Event) -> None:
        """Publish an event to the stream.

        Args:
            event: The event to publish.
        """
        if self._closed:
            return

        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Apply filters
        if self._filters and not all(f(event) for f in self._filters):
            return

        await self._queue.put(event)

        # Notify subscribers
        for handler in self._subscribers:
            try:
                await handler(event)
            except Exception:
                pass  # Subscriber errors should not break the stream

    async def receive(self, timeout: Optional[float] = None) -> Event:
        """Receive the next event from the stream.

        Args:
            timeout: Optional timeout in seconds.

        Returns:
            The next event.

        Raises:
            asyncio.TimeoutError: If timeout is reached.
        """
        if timeout is not None:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        return await self._queue.get()

    async def __aiter__(self) -> AsyncIterator[Event]:
        """Async iterator over events in the stream."""
        while not self._closed:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield event
            except asyncio.TimeoutError:
                continue

    def add_filter(self, predicate: Callable[[Event], bool]) -> None:
        """Add a filter predicate. Only events passing all filters are published.

        Args:
            predicate: A callable that returns True for events to keep.
        """
        self._filters.append(predicate)

    def subscribe(self, handler: EventHandler) -> None:
        """Subscribe a handler to be called for each event.

        Args:
            handler: Async callback for events.
        """
        self._subscribers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        """Remove a subscriber handler.

        Args:
            handler: The handler to remove.
        """
        self._subscribers = [h for h in self._subscribers if h != handler]

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get event history with optional filtering.

        Args:
            event_type: Filter by event type.
            source: Filter by source.
            limit: Maximum events to return.

        Returns:
            Filtered list of historical events.
        """
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        return events[-limit:]

    def close(self) -> None:
        """Close the stream, preventing new events from being published."""
        self._closed = True

    @property
    def is_closed(self) -> bool:
        """Whether the stream is closed."""
        return self._closed

    @property
    def event_count(self) -> int:
        """Total number of events published."""
        return len(self._history)

    def clear_history(self) -> None:
        """Clear all event history."""
        self._history.clear()
