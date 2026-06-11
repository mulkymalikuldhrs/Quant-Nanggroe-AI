"""7 Hand types – specialist agent groups within a colony.

Each *hand* manages a group of agents that share a speciality:

1. **SecurityHand** – Security analysis & vulnerability scanning  (1–5 replicas)
2. **CodeHand**     – Code generation, review & testing            (2–10 replicas)
3. **ResearchHand** – Web & codebase research                      (1–5 replicas)
4. **BrowserHand**  – Browser automation & web scraping            (2–10 replicas)
5. **VoiceHand**    – Voice I/O & transcription                    (0–3 replicas)
6. **ComputeHand**  – Sandboxed code execution                     (3–20 replicas)
7. **IntegrationHand** – VCS, CI/CD & external integrations        (1–5 replicas)

Every hand tracks: replica count, scaling, task distribution, health monitoring.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ..types import HandType, Task, TaskStatus, AutonomyLevel

logger = logging.getLogger(__name__)

# ── Descriptions ──────────────────────────────────────────────────────────────

HAND_DESCRIPTIONS: Dict[HandType, str] = {
    HandType.SECURITY: "Security analysis and vulnerability scanning",
    HandType.CODE: "Code generation, review, and testing",
    HandType.RESEARCH: "Web and codebase research",
    HandType.BROWSER: "Browser automation and web scraping",
    HandType.VOICE: "Voice input/output and transcription",
    HandType.COMPUTE: "Sandboxed code execution",
    HandType.INTEGRATION: "VCS, CI/CD, and external integrations",
}

# Default replica ranges per hand type
HAND_DEFAULTS: Dict[HandType, Dict[str, int]] = {
    HandType.SECURITY: {"min": 1, "max": 5},
    HandType.CODE: {"min": 2, "max": 10},
    HandType.RESEARCH: {"min": 1, "max": 5},
    HandType.BROWSER: {"min": 2, "max": 10},
    HandType.VOICE: {"min": 0, "max": 3},
    HandType.COMPUTE: {"min": 3, "max": 20},
    HandType.INTEGRATION: {"min": 1, "max": 5},
}


class Hand:
    """A specialist group of agents within a colony.

    Each hand is responsible for:
    * Managing replica count (min/max bounds)
    * Auto-scaling based on task queue depth
    * Distributing tasks to agents (round-robin within the hand)
    * Monitoring health of its agents
    """

    def __init__(
        self,
        hand_type: HandType,
        min_replicas: int = 1,
        max_replicas: int = 10,
        description: str = "",
    ):
        self.hand_type = hand_type
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.description = description or HAND_DESCRIPTIONS.get(hand_type, "")

        # Agent tracking
        self._agents: List[str] = []
        self._agent_health: Dict[str, float] = {}  # agent_id → health score
        self._agent_load: Dict[str, int] = {}  # agent_id → current task count
        self._rr_index: int = 0  # round-robin index

        # Task queue
        self._task_queue: List[Task] = []
        self._active_tasks: Dict[str, Task] = {}  # task_id → Task
        self._completed_count: int = 0
        self._failed_count: int = 0

        # Scaling policy
        self.scaling_policy: str = "manual"  # manual | auto
        self.target_queue_depth: int = 5
        self.scale_up_cooldown_s: int = 60
        self._last_scale_up: Optional[datetime] = None

    # ── Replica management ─────────────────────────────────────────────────

    def add_agent(self, agent_id: str) -> bool:
        """Add an agent replica to this hand.

        Returns ``True`` if added, ``False`` if the hand is at max capacity.
        """
        if agent_id in self._agents:
            return True  # already present
        if len(self._agents) >= self.max_replicas:
            logger.warning("Hand %s at max capacity (%d)", self.hand_type.value, self.max_replicas)
            return False
        self._agents.append(agent_id)
        self._agent_health[agent_id] = 1.0
        self._agent_load[agent_id] = 0
        logger.debug("Agent %s added to hand %s", agent_id, self.hand_type.value)
        return True

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent replica from this hand."""
        if agent_id in self._agents:
            self._agents.remove(agent_id)
            self._agent_health.pop(agent_id, None)
            self._agent_load.pop(agent_id, None)

    @property
    def agent_count(self) -> int:
        """Current number of agent replicas."""
        return len(self._agents)

    @property
    def is_staffed(self) -> bool:
        """Whether the hand meets its minimum replica count."""
        return len(self._agents) >= self.min_replicas

    # ── Scaling ────────────────────────────────────────────────────────────

    def should_scale_up(self) -> bool:
        """Check if auto-scaling recommends adding a replica."""
        if self.scaling_policy != "auto":
            return False
        if len(self._agents) >= self.max_replicas:
            return False
        if self.pending_tasks > self.target_queue_depth:
            now = datetime.now(timezone.utc)
            if self._last_scale_up is None or (now - self._last_scale_up).total_seconds() >= self.scale_up_cooldown_s:
                return True
        return False

    def should_scale_down(self) -> bool:
        """Check if auto-scaling recommends removing a replica."""
        if self.scaling_policy != "auto":
            return False
        if len(self._agents) <= self.min_replicas:
            return False
        if self.pending_tasks == 0 and self.active_task_count == 0:
            return True
        return False

    def mark_scaled_up(self) -> None:
        """Record that a scale-up event occurred."""
        self._last_scale_up = datetime.now(timezone.utc)

    # ── Task distribution ──────────────────────────────────────────────────

    def enqueue_task(self, task: Task) -> None:
        """Add a task to the hand's queue."""
        self._task_queue.append(task)

    def dequeue_task(self) -> Optional[Task]:
        """Pop the next task from the queue."""
        return self._task_queue.pop(0) if self._task_queue else None

    def assign_task(self, task: Task) -> Optional[str]:
        """Assign a task to the least-loaded agent in this hand.

        Returns the agent_id that received the task, or ``None`` if
        no agents are available.
        """
        if not self._agents:
            return None
        # Pick least-loaded agent
        best_agent = min(self._agents, key=lambda a: self._agent_load.get(a, 0))
        task.assigned_agent = best_agent
        task.status = TaskStatus.ASSIGNED
        self._active_tasks[task.task_id] = task
        self._agent_load[best_agent] = self._agent_load.get(best_agent, 0) + 1
        return best_agent

    def assign_task_round_robin(self, task: Task) -> Optional[str]:
        """Assign a task using round-robin across agents."""
        if not self._agents:
            return None
        agent_id = self._agents[self._rr_index % len(self._agents)]
        self._rr_index += 1
        task.assigned_agent = agent_id
        task.status = TaskStatus.ASSIGNED
        self._active_tasks[task.task_id] = task
        self._agent_load[agent_id] = self._agent_load.get(agent_id, 0) + 1
        return agent_id

    def complete_task(self, task_id: str, success: bool = True) -> None:
        """Mark a task as completed and update agent load."""
        task = self._active_tasks.pop(task_id, None)
        if task and task.assigned_agent:
            load = self._agent_load.get(task.assigned_agent, 0)
            self._agent_load[task.assigned_agent] = max(0, load - 1)
        if success:
            self._completed_count += 1
        else:
            self._failed_count += 1

    @property
    def pending_tasks(self) -> int:
        """Number of tasks waiting in the queue."""
        return len(self._task_queue)

    @property
    def active_task_count(self) -> int:
        """Number of tasks currently being processed."""
        return len(self._active_tasks)

    # ── Health monitoring ──────────────────────────────────────────────────

    def update_agent_health(self, agent_id: str, health_score: float) -> None:
        """Update an agent's health score."""
        self._agent_health[agent_id] = max(0.0, min(1.0, health_score))

    def get_unhealthy_agents(self, threshold: float = 0.5) -> List[str]:
        """Return agent IDs with health below the threshold."""
        return [aid for aid, score in self._agent_health.items() if score < threshold]

    @property
    def average_health(self) -> float:
        """Mean health score across all agents."""
        scores = list(self._agent_health.values())
        return sum(scores) / len(scores) if scores else 1.0

    # ── Status ─────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return a structured status dict for this hand."""
        return {
            "hand_type": self.hand_type.value,
            "description": self.description,
            "agents": list(self._agents),
            "agent_count": self.agent_count,
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "is_staffed": self.is_staffed,
            "pending_tasks": self.pending_tasks,
            "active_tasks": self.active_task_count,
            "completed_tasks": self._completed_count,
            "failed_tasks": self._failed_count,
            "average_health": round(self.average_health, 3),
            "scaling_policy": self.scaling_policy,
        }


# ── Concrete hand subclasses with specialised defaults ─────────────────────────


class SecurityHand(Hand):
    """Security analysis and vulnerability scanning (1–5 replicas)."""

    def __init__(self):
        super().__init__(HandType.SECURITY, min_replicas=1, max_replicas=5)


class CodeHand(Hand):
    """Code generation, review, and testing (2–10 replicas)."""

    def __init__(self):
        super().__init__(HandType.CODE, min_replicas=2, max_replicas=10)


class ResearchHand(Hand):
    """Web and codebase research (1–5 replicas)."""

    def __init__(self):
        super().__init__(HandType.RESEARCH, min_replicas=1, max_replicas=5)


class BrowserHand(Hand):
    """Browser automation and web scraping (2–10 replicas)."""

    def __init__(self):
        super().__init__(HandType.BROWSER, min_replicas=2, max_replicas=10)


class VoiceHand(Hand):
    """Voice input/output and transcription (0–3 replicas)."""

    def __init__(self):
        super().__init__(HandType.VOICE, min_replicas=0, max_replicas=3)


class ComputeHand(Hand):
    """Sandboxed code execution (3–20 replicas)."""

    def __init__(self):
        super().__init__(HandType.COMPUTE, min_replicas=3, max_replicas=20)


class IntegrationHand(Hand):
    """VCS, CI/CD, and external integrations (1–5 replicas)."""

    def __init__(self):
        super().__init__(HandType.INTEGRATION, min_replicas=1, max_replicas=5)


# ── Hand Manager ──────────────────────────────────────────────────────────────


class HandManager:
    """Manages all 7 hands for a colony.

    Provides a unified interface for:
    * Agent assignment across hands
    * Cross-hand task routing
    * Aggregate health monitoring
    * Auto-scaling coordination
    """

    def __init__(self):
        self._hands: Dict[HandType, Hand] = {
            HandType.SECURITY: SecurityHand(),
            HandType.CODE: CodeHand(),
            HandType.RESEARCH: ResearchHand(),
            HandType.BROWSER: BrowserHand(),
            HandType.VOICE: VoiceHand(),
            HandType.COMPUTE: ComputeHand(),
            HandType.INTEGRATION: IntegrationHand(),
        }

    # ── Hand access ────────────────────────────────────────────────────────

    def get_hand(self, hand_type: HandType) -> Hand:
        """Get a specific hand by type."""
        return self._hands[hand_type]

    def get_available_hands(self) -> List[Hand]:
        """Return hands that have at least one agent."""
        return [h for h in self._hands.values() if h.agent_count > 0]

    def get_staffed_hands(self) -> List[Hand]:
        """Return hands that meet their minimum replica count."""
        return [h for h in self._hands.values() if h.is_staffed]

    def get_unstaffed_hands(self) -> List[Hand]:
        """Return hands that are below their minimum replica count."""
        return [h for h in self._hands.values() if not h.is_staffed]

    # ── Agent assignment ───────────────────────────────────────────────────

    def assign_agent(self, hand_type: HandType, agent_id: str) -> bool:
        """Assign an agent to a specific hand type.

        Returns ``True`` on success, ``False`` if the hand is at capacity.
        """
        hand = self._hands[hand_type]
        return hand.add_agent(agent_id)

    def unassign_agent(self, hand_type: HandType, agent_id: str) -> None:
        """Remove an agent from a hand."""
        self._hands[hand_type].remove_agent(agent_id)

    def find_agent_hand(self, agent_id: str) -> Optional[HandType]:
        """Find which hand an agent belongs to."""
        for ht, hand in self._hands.items():
            if agent_id in hand._agents:
                return ht
        return None

    # ── Task routing ───────────────────────────────────────────────────────

    def route_task(self, task: Task) -> Optional[HandType]:
        """Route a task to the most appropriate hand based on required capabilities.

        Returns the chosen HandType, or ``None`` if no hand matches.
        """
        caps = task.required_capabilities
        if not caps:
            # Default: route to the least-loaded hand that is staffed
            staffed = self.get_staffed_hands()
            if not staffed:
                available = self.get_available_hands()
                if not available:
                    return None
                return min(available, key=lambda h: h.active_task_count).hand_type
            return min(staffed, key=lambda h: h.active_task_count + h.pending_tasks).hand_type

        # Map capability keywords to hand types
        cap_map: Dict[str, HandType] = {
            "security": HandType.SECURITY,
            "vulnerability": HandType.SECURITY,
            "scan": HandType.SECURITY,
            "code": HandType.CODE,
            "coding": HandType.CODE,
            "review": HandType.CODE,
            "test": HandType.CODE,
            "research": HandType.RESEARCH,
            "search": HandType.RESEARCH,
            "browse": HandType.BROWSER,
            "browser": HandType.BROWSER,
            "scrape": HandType.BROWSER,
            "voice": HandType.VOICE,
            "speech": HandType.VOICE,
            "transcri": HandType.VOICE,
            "compute": HandType.COMPUTE,
            "exec": HandType.COMPUTE,
            "run": HandType.COMPUTE,
            "integration": HandType.INTEGRATION,
            "vcs": HandType.INTEGRATION,
            "git": HandType.INTEGRATION,
            "deploy": HandType.INTEGRATION,
            "ci": HandType.INTEGRATION,
        }

        candidates: Dict[HandType, int] = {}
        for cap in caps:
            cap_lower = cap.lower()
            for keyword, ht in cap_map.items():
                if keyword in cap_lower:
                    candidates[ht] = candidates.get(ht, 0) + 1

        if not candidates:
            # Fallback: least loaded staffed hand
            staffed = self.get_staffed_hands()
            if staffed:
                return min(staffed, key=lambda h: h.active_task_count + h.pending_tasks).hand_type
            return None

        # Pick the hand with the most capability matches; break ties by load
        best_type = max(candidates, key=lambda ht: (candidates[ht], -(self._hands[ht].active_task_count + self._hands[ht].pending_tasks)))
        return best_type

    # ── Auto-scaling ───────────────────────────────────────────────────────

    def check_scaling(self) -> Dict[HandType, str]:
        """Check all auto-scaling hands and return recommendations.

        Returns a dict mapping HandType to "scale_up" | "scale_down" | "ok".
        """
        result: Dict[HandType, str] = {}
        for ht, hand in self._hands.items():
            if hand.should_scale_up():
                result[ht] = "scale_up"
            elif hand.should_scale_down():
                result[ht] = "scale_down"
            else:
                result[ht] = "ok"
        return result

    # ── Health ─────────────────────────────────────────────────────────────

    def get_all_health(self) -> Dict[HandType, float]:
        """Return average health for each hand."""
        return {ht: hand.average_health for ht, hand in self._hands.items()}

    def get_unhealthy_agents(self, threshold: float = 0.5) -> Dict[HandType, List[str]]:
        """Return unhealthy agent IDs grouped by hand type."""
        result: Dict[HandType, List[str]] = {}
        for ht, hand in self._hands.items():
            unhealthy = hand.get_unhealthy_agents(threshold)
            if unhealthy:
                result[ht] = unhealthy
        return result

    # ── Status ─────────────────────────────────────────────────────────────

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Return status dicts for all hands."""
        return {ht.value: hand.get_status() for ht, hand in self._hands.items()}

    @property
    def total_agents(self) -> int:
        return sum(h.agent_count for h in self._hands.values())

    @property
    def total_pending_tasks(self) -> int:
        return sum(h.pending_tasks for h in self._hands.values())

    @property
    def total_active_tasks(self) -> int:
        return sum(h.active_task_count for h in self._hands.values())
