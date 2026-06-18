"""Memory condensers - 8 implementations from OpenHands.

Standalone implementations of 8 condenser types ported from OpenHands:
NoOpCondenser, RecentEventsCondenser, ObservationCondenser, LLMCondenser,
AmortizedCondenser, BrowserOutputCondenser, LLMAttentionCondenser, SummaryCondenser.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.types.events import Event, Observation, ObservationType
from ai_multicolony.types.memory import CondenserType

logger = get_logger(__name__)


class BaseCondenser(ABC):
    """Abstract base class for memory condensers.

    Condensers reduce memory content to fit within context windows.
    Ported from OpenHands condenser implementations.
    """

    @abstractmethod
    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Condense a list of events to fit within token limits.

        Args:
            events: The events to condense.
            max_tokens: Maximum token budget.

        Returns:
            Condensed list of events.
        """
        ...

    @property
    @abstractmethod
    def condenser_type(self) -> CondenserType:
        """Get the condenser type."""
        ...

    def _estimate_tokens(self, events: list[Event]) -> int:
        """Estimate the total token count of events (rough: 1 token ~ 4 chars)."""
        total = 0
        for e in events:
            if e.observation:
                total += len(e.observation.content) // 4
            if e.action:
                total += len(e.action.thought or "") // 4
            total += len(str(e.data)) // 4
        return total


class NoOpCondenser(BaseCondenser):
    """No-op condenser that passes events through unchanged.

    Useful for debugging or when full context is needed.
    """

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Pass events through unchanged."""
        return list(events)

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.NOOP


class RecentEventsCondenser(BaseCondenser):
    """Keep only the most recent N events.

    Drops older events when the total exceeds the token budget,
    preserving the most recent conversation context.
    """

    def __init__(self, max_events: int = 20, max_tokens: int = 4000) -> None:
        self.max_events = max_events
        self._max_tokens = max_tokens

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Keep only the most recent events within token budget."""
        budget = max_tokens or self._max_tokens
        result = events[-self.max_events:]

        # Further trim by token budget
        while result and self._estimate_tokens(result) > budget:
            result = result[1:]

        return result

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.RECENT


# Backward-compatible alias
RecentCondenser = RecentEventsCondenser


class ObservationCondenser(BaseCondenser):
    """Keep only observations, discarding intermediate actions.

    Preserves the most recent N actions to maintain some context
    about what the agent was doing, while dropping older actions.
    """

    def __init__(self, keep_recent_actions: int = 2) -> None:
        self.keep_recent_actions = keep_recent_actions

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Keep observations and recent actions only."""
        observations = [e for e in events if e.observation is not None]
        actions = [e for e in events if e.action is not None]
        recent_actions = actions[-self.keep_recent_actions:]

        combined = sorted(observations + recent_actions, key=lambda e: e.timestamp)

        # Trim by token budget
        while combined and self._estimate_tokens(combined) > max_tokens:
            combined = combined[1:]

        return combined

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.OBSERVATION


class LLMCondenser(BaseCondenser):
    """LLM-based summarization condenser.

    Uses an LLM to summarize events when they exceed the token budget.
    Falls back to recent-events-only when LLM is unavailable.
    """

    def __init__(self, llm_provider: Optional[Any] = None, summary_max_tokens: int = 1000) -> None:
        self._llm_provider = llm_provider
        self._summary_max_tokens = summary_max_tokens
        self._summary_cache: dict[str, str] = {}

    async def condense_async(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Async version of condense that uses LLM for summarization."""
        if not self._llm_provider or not events:
            return self.condense(events, max_tokens)

        if self._estimate_tokens(events) <= max_tokens:
            return events

        try:
            event_texts = []
            for event in events:
                if event.observation:
                    event_texts.append(f"[OBS] {event.observation.content[:200]}")
                elif event.action:
                    thought = event.action.thought or ""
                    event_texts.append(f"[ACT] {event.action.action_type.value}: {thought[:200]}")

            summary_text = "\n".join(event_texts)

            response = await self._llm_provider.chat(
                messages=[
                    {"role": "system", "content": "Summarize the following agent events concisely, preserving key information."},
                    {"role": "user", "content": summary_text},
                ],
                max_tokens=self._summary_max_tokens,
            )

            summary_event = Event(
                source="condenser",
                observation=Observation(
                    observation_type=ObservationType.MEMORY_CONDENSED,
                    agent_id="condenser",
                    action_id="condensed",
                    content=f"[Condensed Summary]\n{response.content}",
                ),
                data={"condensed": True, "original_count": len(events)},
            )
            return [summary_event]
        except Exception as e:
            logger.error("llm_condenser_error", error=str(e))
            return events[-10:]

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Synchronous fallback - use recent events only."""
        if self._estimate_tokens(events) <= max_tokens:
            return list(events)
        # Trim from the beginning until within budget
        result = list(events)
        while result and self._estimate_tokens(result) > max_tokens:
            result = result[1:]
        return result

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.LLM


class AmortizedCondenser(BaseCondenser):
    """Amortized forgetting - gradually reduce older event importance.

    Implements a decay factor that progressively reduces the importance
    of older events, eventually dropping them below a minimum threshold.
    """

    def __init__(self, decay_factor: float = 0.9, min_importance: float = 0.1) -> None:
        self.decay_factor = decay_factor
        self.min_importance = min_importance
        self._importance: dict[str, float] = {}

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Apply amortized decay to events, dropping low-importance ones."""
        # Decay all existing importance scores
        for event_id in list(self._importance.keys()):
            self._importance[event_id] *= self.decay_factor

        # Initialize new events with importance 1.0
        for event in events:
            if event.id not in self._importance:
                self._importance[event.id] = 1.0
            else:
                # Boost recently-accessed events
                self._importance[event.id] = min(1.0, self._importance[event.id] + 0.1)

        # Filter by importance threshold
        important_events = [
            e for e in events
            if self._importance.get(e.id, 0) >= self.min_importance
        ]

        # Clean up old entries
        self._importance = {
            k: v for k, v in self._importance.items()
            if v >= self.min_importance * 0.1
        }

        # Further trim by token budget
        while important_events and self._estimate_tokens(important_events) > max_tokens:
            # Remove the least important event
            least_important = min(important_events, key=lambda e: self._importance.get(e.id, 0))
            important_events.remove(least_important)

        return important_events

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.AMORTIZED


class BrowserOutputCondenser(BaseCondenser):
    """Specialized condenser for browser output.

    Truncates long HTML/browser output content to keep context
    manageable while preserving other event types unchanged.
    """

    def __init__(self, max_browser_output: int = 2000) -> None:
        self.max_browser_output = max_browser_output

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Truncate browser output and filter within token budget."""
        condensed = []
        for event in events:
            if event.observation and event.observation.observation_type in (
                ObservationType.BROWSER_PAGE,
                ObservationType.BROWSER_ERROR,
            ):
                content = event.observation.content
                if len(content) > self.max_browser_output:
                    try:
                        new_obs = event.observation.model_copy(update={
                            "content": content[:self.max_browser_output] + "\n[...truncated...]",
                        })
                        new_event = event.model_copy(update={"observation": new_obs})
                        condensed.append(new_event)
                    except Exception:
                        condensed.append(event)
                else:
                    condensed.append(event)
            else:
                condensed.append(event)

        # Trim by token budget
        while condensed and self._estimate_tokens(condensed) > max_tokens:
            condensed = condensed[1:]

        return condensed

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.BROWSER_OUTPUT


class LLMAttentionCondenser(BaseCondenser):
    """LLM attention-based condenser.

    Uses heuristics inspired by attention mechanisms to prioritize
    events that are most relevant to the current task. Falls back
    to recent-events-only when no attention scorer is available.
    """

    def __init__(
        self,
        recency_weight: float = 0.4,
        importance_weight: float = 0.3,
        relevance_weight: float = 0.3,
        llm_provider: Optional[Any] = None,
    ) -> None:
        self._recency_weight = recency_weight
        self._importance_weight = importance_weight
        self._relevance_weight = relevance_weight
        self._llm_provider = llm_provider
        self._current_task: Optional[str] = None

    def set_current_task(self, task: str) -> None:
        """Set the current task for relevance scoring."""
        self._current_task = task

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Score events by attention and keep top-scoring ones."""
        if not events:
            return []

        if self._estimate_tokens(events) <= max_tokens:
            return list(events)

        # Score each event
        now = time.time()
        scored_events: list[tuple[float, Event]] = []

        for event in events:
            # Recency score (0-1, higher is more recent)
            age = now - event.timestamp
            recency = max(0, 1.0 - age / 3600)  # 1-hour window

            # Importance score based on event type
            importance = 0.5
            if event.observation:
                if event.observation.observation_type == ObservationType.ERROR:
                    importance = 0.9
                elif event.observation.observation_type == ObservationType.COMMAND_OUTPUT:
                    importance = 0.6
            if event.action:
                if event.action.action_type.value in ("think", "message"):
                    importance = 0.8

            # Relevance score (keyword overlap with current task)
            relevance = 0.5
            if self._current_task:
                task_words = set(self._current_task.lower().split())
                event_text = ""
                if event.observation:
                    event_text += event.observation.content.lower()
                if event.action and event.action.thought:
                    event_text += " " + event.action.thought.lower()
                event_words = set(event_text.split())
                overlap = len(task_words & event_words)
                relevance = min(1.0, overlap / max(len(task_words), 1))

            # Weighted combination
            score = (
                self._recency_weight * recency
                + self._importance_weight * importance
                + self._relevance_weight * relevance
            )
            scored_events.append((score, event))

        # Sort by score (descending) and keep top events within budget
        scored_events.sort(key=lambda x: x[0], reverse=True)

        result: list[Event] = []
        total_tokens = 0
        for score, event in scored_events:
            event_tokens = self._estimate_tokens([event])
            if total_tokens + event_tokens <= max_tokens:
                result.append(event)
                total_tokens += event_tokens

        # Re-sort by timestamp for chronological order
        result.sort(key=lambda e: e.timestamp)
        return result

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.LLM  # Closest match


class SummaryCondenser(BaseCondenser):
    """Summary-based condenser that maintains a running summary.

    Periodically summarizes older events into a summary event,
    replacing the original events with a compact representation.
    """

    def __init__(
        self,
        summary_interval: int = 10,
        max_summary_tokens: int = 500,
        llm_provider: Optional[Any] = None,
    ) -> None:
        self._summary_interval = summary_interval
        self._max_summary_tokens = max_summary_tokens
        self._llm_provider = llm_provider
        self._current_summary: Optional[str] = None
        self._events_since_summary = 0

    def condense(self, events: list[Event], max_tokens: int = 4000) -> list[Event]:
        """Summarize older events, keeping recent ones intact."""
        if not events or self._estimate_tokens(events) <= max_tokens:
            return list(events)

        # Split events into old (to summarize) and recent (to keep)
        split_point = max(0, len(events) - self._summary_interval)
        old_events = events[:split_point]
        recent_events = events[split_point:]

        if not old_events:
            # If even recent events exceed budget, just trim
            while recent_events and self._estimate_tokens(recent_events) > max_tokens:
                recent_events = recent_events[1:]
            return recent_events

        # Build summary from old events
        summary_parts = []
        if self._current_summary:
            summary_parts.append(f"[Previous Summary] {self._current_summary}")

        for event in old_events:
            if event.observation:
                summary_parts.append(f"[OBS] {event.observation.content[:100]}")
            elif event.action:
                summary_parts.append(f"[ACT] {event.action.action_type.value}: {(event.action.thought or '')[:100]}")

        summary_text = "\n".join(summary_parts)
        # Truncate if too long
        if len(summary_text) > self._max_summary_tokens * 4:
            summary_text = summary_text[:self._max_summary_tokens * 4] + "\n[...summary truncated...]"

        self._current_summary = summary_text
        self._events_since_summary = 0

        # Create summary event
        summary_event = Event(
            source="summary_condenser",
            observation=Observation(
                observation_type=ObservationType.MEMORY_CONDENSED,
                agent_id="condenser",
                action_id="summary",
                content=summary_text,
            ),
            data={
                "condensed": True,
                "original_count": len(old_events),
                "summary": True,
            },
        )

        result = [summary_event] + recent_events

        # Trim if still over budget
        while result and self._estimate_tokens(result) > max_tokens:
            # Remove oldest non-summary event first
            if len(result) > 1:
                result.pop(1)
            else:
                break

        return result

    def reset(self) -> None:
        """Reset the summary state."""
        self._current_summary = None
        self._events_since_summary = 0

    @property
    def condenser_type(self) -> CondenserType:
        return CondenserType.LLMLINGUA  # Closest match for summary-style


# Aliases for backward compatibility
EventMaskCondenser = type(
    "EventMaskCondenser",
    (BaseCondenser,),
    {
        "__init__": lambda self, mask_types=None: (
            setattr(self, '_mask_types', mask_types or ["agent_state_changed"]) or None
        ),
        "condense": lambda self, events, max_tokens=4000: [
            e for e in events
            if e.event_type not in self._mask_types
            and e.data.get("observation_type", "") not in self._mask_types
        ],
        "condenser_type": property(lambda self: CondenserType.EVENT_MASK),
    },
)

LLMLinguaCondenser = type(
    "LLMLinguaCondenser",
    (BaseCondenser,),
    {
        "__init__": lambda self, compression_rate=0.5: (
            setattr(self, 'compression_rate', compression_rate) or None
        ),
        "condense": lambda self, events, max_tokens=4000: (
            events if len(events) <= int(len(events) * self.compression_rate)
            else events[:int(len(events) * self.compression_rate) // 2]
            + events[-(int(len(events) * self.compression_rate) - int(len(events) * self.compression_rate) // 2):]
        ),
        "condenser_type": property(lambda self: CondenserType.LLMLINGUA),
    },
)

__all__ = [
    "BaseCondenser",
    "NoOpCondenser",
    "RecentEventsCondenser",
    "RecentCondenser",
    "ObservationCondenser",
    "LLMCondenser",
    "AmortizedCondenser",
    "BrowserOutputCondenser",
    "LLMAttentionCondenser",
    "SummaryCondenser",
    "EventMaskCondenser",
    "LLMLinguaCondenser",
]
