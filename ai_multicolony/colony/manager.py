"""Colony manager – lifecycle, coordination, health, and inter-colony gateway.

A *colony* is a logical grouping of agents that share context, memory, and
tool access.  The ``ColonyManager`` creates, deletes, and monitors colonies,
assigns overseers, binds agents to colonies, and routes inter-colony messages.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from ..types import (
    ColonyConfig,
    ColonyHealth,
    ColonyInfo,
    ColonyScale,
    ColonyStatus,
    AgentType,
    AgentInfo,
    HandType,
    Task,
    TaskResult,
    TaskStatus,
    AutonomyLevel,
    RoutingStrategy,
    Event,
    EventType,
)
from ..exceptions import ColonyNotFoundError, ColonyFullError

logger = logging.getLogger(__name__)

# ── Scale presets ──────────────────────────────────────────────────────────────

SCALE_PRESETS: Dict[ColonyScale, Dict[str, Any]] = {
    ColonyScale.MICRO: {
        "max_agents": 5,
        "hands": {
            "security": {"min": 1, "max": 2},
            "code": {"min": 1, "max": 3},
            "research": {"min": 0, "max": 2},
            "browser": {"min": 1, "max": 2},
            "voice": {"min": 0, "max": 1},
            "compute": {"min": 1, "max": 5},
            "integration": {"min": 0, "max": 2},
        },
    },
    ColonyScale.SMALL: {
        "max_agents": 15,
        "hands": {
            "security": {"min": 1, "max": 3},
            "code": {"min": 2, "max": 5},
            "research": {"min": 1, "max": 3},
            "browser": {"min": 1, "max": 5},
            "voice": {"min": 0, "max": 2},
            "compute": {"min": 2, "max": 10},
            "integration": {"min": 1, "max": 3},
        },
    },
    ColonyScale.MEDIUM: {
        "max_agents": 50,
        "hands": {
            "security": {"min": 1, "max": 5},
            "code": {"min": 2, "max": 10},
            "research": {"min": 1, "max": 5},
            "browser": {"min": 2, "max": 10},
            "voice": {"min": 0, "max": 3},
            "compute": {"min": 3, "max": 20},
            "integration": {"min": 1, "max": 5},
        },
    },
    ColonyScale.LARGE: {
        "max_agents": 200,
        "hands": {
            "security": {"min": 2, "max": 10},
            "code": {"min": 5, "max": 30},
            "research": {"min": 2, "max": 10},
            "browser": {"min": 5, "max": 20},
            "voice": {"min": 1, "max": 5},
            "compute": {"min": 10, "max": 50},
            "integration": {"min": 2, "max": 10},
        },
    },
}


class Colony:
    """A colony of agents with shared context, memory, and tools.

    Each colony owns a set of *hands* (specialist agent groups), has an
    optional overseer, and maintains its own task queue and health score.
    """

    def __init__(self, config: Optional[ColonyConfig] = None):
        self.config = config or ColonyConfig()
        self.colony_id: str = self.config.colony_id
        self.name: str = self.config.name
        self.goal: str = self.config.goal
        self.status: ColonyStatus = ColonyStatus.CREATING
        self.scale: ColonyScale = self.config.scale
        self.routing_strategy: RoutingStrategy = self.config.routing_strategy

        # Agent tracking
        self._agents: Dict[str, Any] = {}
        self._agent_info: Dict[str, AgentInfo] = {}
        self._hand_assignments: Dict[HandType, List[str]] = {ht: [] for ht in HandType}

        # Task tracking
        self._tasks: Dict[str, Task] = {}
        self._task_results: Dict[str, TaskResult] = {}

        # Overseer
        self._overseer_id: Optional[str] = None

        # Health
        self._health: Optional[ColonyHealth] = None
        self._created_at: datetime = datetime.now(timezone.utc)

        # Inter-colony gateway
        self._inter_colony_queue: List[Dict[str, Any]] = []

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def bootstrap(self) -> None:
        """Activate the colony after creation."""
        self.status = ColonyStatus.ACTIVE
        logger.info("Colony %s (%s) bootstrapped – scale=%s", self.colony_id, self.name, self.scale.value)

    async def pause(self) -> None:
        """Temporarily pause the colony (agents suspend)."""
        if self.status != ColonyStatus.ACTIVE:
            raise ValueError(f"Cannot pause colony in state {self.status.value}")
        self.status = ColonyStatus.PAUSED
        logger.info("Colony %s paused", self.colony_id)

    async def resume(self) -> None:
        """Resume a paused colony."""
        if self.status != ColonyStatus.PAUSED:
            raise ValueError(f"Cannot resume colony in state {self.status.value}")
        self.status = ColonyStatus.ACTIVE
        logger.info("Colony %s resumed", self.colony_id)

    async def shutdown(self) -> None:
        """Gracefully terminate the colony and all its agents."""
        self.status = ColonyStatus.TERMINATING
        for agent_id, agent in list(self._agents.items()):
            if hasattr(agent, "terminate"):
                try:
                    await agent.terminate()
                except Exception as exc:
                    logger.warning("Error terminating agent %s: %s", agent_id, exc)
        self._agents.clear()
        self._agent_info.clear()
        self._hand_assignments = {ht: [] for ht in HandType}
        self.status = ColonyStatus.TERMINATED
        logger.info("Colony %s shut down", self.colony_id)

    # ── Overseer ───────────────────────────────────────────────────────────

    def assign_overseer(self, agent_id: str) -> None:
        """Designate an agent as the colony overseer."""
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} is not in colony {self.colony_id}")
        self._overseer_id = agent_id
        logger.info("Agent %s assigned as overseer of colony %s", agent_id, self.colony_id)

    def remove_overseer(self) -> None:
        """Remove the current overseer."""
        self._overseer_id = None

    @property
    def overseer_id(self) -> Optional[str]:
        return self._overseer_id

    # ── Agent binding ──────────────────────────────────────────────────────

    def add_agent(self, agent_id: str, agent: Any, hand_type: Optional[HandType] = None) -> None:
        """Bind an agent to the colony, optionally assigning it to a hand."""
        if len(self._agents) >= self.config.max_agents:
            raise ColonyFullError(self.colony_id, self.config.max_agents)
        self._agents[agent_id] = agent
        if hand_type:
            self._hand_assignments[hand_type].append(agent_id)

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the colony."""
        self._agents.pop(agent_id, None)
        self._agent_info.pop(agent_id, None)
        for ht in self._hand_assignments:
            if agent_id in self._hand_assignments[ht]:
                self._hand_assignments[ht].remove(agent_id)
        if self._overseer_id == agent_id:
            self._overseer_id = None

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Retrieve an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """List all agent IDs in the colony."""
        return list(self._agents.keys())

    def set_agent_info(self, agent_id: str, info: AgentInfo) -> None:
        """Store runtime info for an agent."""
        self._agent_info[agent_id] = info

    def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Retrieve runtime info for an agent."""
        return self._agent_info.get(agent_id)

    # ── Task management ────────────────────────────────────────────────────

    async def submit_task(self, task: Task) -> TaskResult:
        """Submit a task to the colony's internal queue."""
        task.colony_id = self.colony_id
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.PENDING
        self._tasks[task.task_id] = task
        logger.debug("Task %s submitted to colony %s", task.task_id, self.colony_id)
        return TaskResult(task_id=task.task_id, success=True, data={"status": "submitted"})

    def store_task_result(self, result: TaskResult) -> None:
        """Persist a task result."""
        self._task_results[result.task_id] = result

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        return self._task_results.get(task_id)

    # ── Inter-colony gateway ───────────────────────────────────────────────

    def send_inter_colony(self, target_colony_id: str, message: Dict[str, Any]) -> str:
        """Queue a message for another colony."""
        msg_id = f"ic-{len(self._inter_colony_queue)}"
        self._inter_colony_queue.append({
            "id": msg_id,
            "source": self.colony_id,
            "target": target_colony_id,
            "payload": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return msg_id

    def receive_inter_colony(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve pending inter-colony messages."""
        msgs = self._inter_colony_queue[:limit]
        self._inter_colony_queue = self._inter_colony_queue[limit:]
        return msgs

    # ── Health scoring ─────────────────────────────────────────────────────

    def compute_health(self) -> ColonyHealth:
        """Calculate the colony's health score."""
        now = datetime.now(timezone.utc)

        # Agent health average
        agent_scores = [info.health_score for info in self._agent_info.values()]
        agent_avg = sum(agent_scores) / len(agent_scores) if agent_scores else 1.0

        # Task success rate
        completed = [t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED]
        failed = [t for t in self._tasks.values() if t.status == TaskStatus.FAILED]
        total_tasks = len(completed) + len(failed)
        success_rate = len(completed) / total_tasks if total_tasks > 0 else 1.0

        # Hand coverage: ratio of hands that have ≥1 agent
        covered = sum(1 for agents in self._hand_assignments.values() if agents)
        hand_cov = covered / len(HandType) if HandType else 1.0

        # Resource utilization (heuristic: agent count / max agents)
        res_util = len(self._agents) / self.config.max_agents if self.config.max_agents > 0 else 0.0

        issues: List[str] = []
        if agent_avg < 0.5:
            issues.append("Agent health below threshold")
        if success_rate < 0.7:
            issues.append("Task success rate below 70%")
        if hand_cov < 0.5:
            issues.append("Less than half of hand types are staffed")

        overall = (agent_avg * 0.3 + success_rate * 0.3 + hand_cov * 0.2 + (1.0 - min(res_util, 1.0)) * 0.2)

        self._health = ColonyHealth(
            colony_id=self.colony_id,
            overall_score=round(overall, 3),
            agent_health_avg=round(agent_avg, 3),
            task_success_rate=round(success_rate, 3),
            hand_coverage=round(hand_cov, 3),
            resource_utilization=round(res_util, 3),
            last_heartbeat=now,
            issues=issues,
            checked_at=now,
        )
        return self._health

    # ── Status / introspection ─────────────────────────────────────────────

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def get_info(self) -> ColonyInfo:
        """Return structured colony information."""
        hand_status = {
            ht.value: {"agents": len(ids), "agent_ids": ids}
            for ht, ids in self._hand_assignments.items()
        }
        return ColonyInfo(
            colony_id=self.colony_id,
            name=self.name,
            goal=self.goal,
            status=self.status,
            scale=self.scale,
            agent_count=self.agent_count,
            task_count=self.task_count,
            overseer_id=self._overseer_id,
            created_at=self._created_at,
            routing_strategy=self.routing_strategy,
            hand_status=hand_status,
        )

    def get_status(self) -> Dict[str, Any]:
        """Return a flat dict of colony status (for API compatibility)."""
        return self.get_info().model_dump(mode="json")


class ColonyManager:
    """Manages the lifecycle of multiple colonies.

    Responsibilities:
    * Create / delete colonies.
    * Assign overseers.
    * Bind agents to colonies.
    * Monitor resource allocation.
    * Compute health scores.
    * Route inter-colony messages.
    * Apply scale presets (micro/small/medium/large).
    """

    def __init__(self):
        self._colonies: Dict[str, Colony] = {}
        self._agent_colony_map: Dict[str, str] = {}  # agent_id → colony_id

    # ── CRUD ───────────────────────────────────────────────────────────────

    async def create_colony(self, config: Optional[ColonyConfig] = None) -> Colony:
        """Create and bootstrap a new colony."""
        config = config or ColonyConfig()

        # Apply scale preset if not customised
        if config.scale in SCALE_PRESETS:
            preset = SCALE_PRESETS[config.scale]
            if config.max_agents == 50:  # still the default
                config.max_agents = preset["max_agents"]
            if not any(v != {"min": 0, "max": 10} for v in config.hands.values()):
                config.hands = preset["hands"]

        colony = Colony(config=config)
        await colony.bootstrap()
        self._colonies[colony.colony_id] = colony
        logger.info("Created colony %s (%s) scale=%s", colony.colony_id, colony.name, colony.scale.value)
        return colony

    async def delete_colony(self, colony_id: str) -> bool:
        """Shutdown and remove a colony."""
        colony = self._colonies.get(colony_id)
        if not colony:
            raise ColonyNotFoundError(colony_id)
        # Unbind all agents
        for agent_id in colony.list_agents():
            self._agent_colony_map.pop(agent_id, None)
        await colony.shutdown()
        del self._colonies[colony_id]
        logger.info("Deleted colony %s", colony_id)
        return True

    # ── Lookup ─────────────────────────────────────────────────────────────

    def get_colony(self, colony_id: str) -> Optional[Colony]:
        """Retrieve a colony by ID."""
        return self._colonies.get(colony_id)

    def get_colony_or_raise(self, colony_id: str) -> Colony:
        """Retrieve a colony or raise ColonyNotFoundError."""
        colony = self._colonies.get(colony_id)
        if colony is None:
            raise ColonyNotFoundError(colony_id)
        return colony

    def list_colonies(self) -> List[Dict[str, Any]]:
        """Return status dicts for all colonies."""
        return [c.get_status() for c in self._colonies.values()]

    def list_active_colonies(self) -> List[Colony]:
        """Return only active colonies."""
        return [c for c in self._colonies.values() if c.status == ColonyStatus.ACTIVE]

    # ── Overseer assignment ────────────────────────────────────────────────

    def assign_overseer(self, colony_id: str, agent_id: str) -> None:
        """Assign an agent as the overseer of a colony."""
        colony = self.get_colony_or_raise(colony_id)
        colony.assign_overseer(agent_id)

    # ── Agent binding ──────────────────────────────────────────────────────

    async def bind_agent(self, colony_id: str, agent_id: str, agent: Any, hand_type: Optional[HandType] = None) -> None:
        """Bind an agent to a colony (and optionally a hand)."""
        colony = self.get_colony_or_raise(colony_id)
        colony.add_agent(agent_id, agent, hand_type=hand_type)
        self._agent_colony_map[agent_id] = colony_id

    async def unbind_agent(self, colony_id: str, agent_id: str) -> None:
        """Remove an agent from its colony."""
        colony = self.get_colony_or_raise(colony_id)
        colony.remove_agent(agent_id)
        self._agent_colony_map.pop(agent_id, None)

    def get_agent_colony(self, agent_id: str) -> Optional[Colony]:
        """Find which colony an agent belongs to."""
        cid = self._agent_colony_map.get(agent_id)
        if cid:
            return self._colonies.get(cid)
        return None

    # ── Resource monitoring ────────────────────────────────────────────────

    def get_resource_allocation(self) -> Dict[str, Dict[str, Any]]:
        """Return resource usage per colony."""
        result: Dict[str, Dict[str, Any]] = {}
        for cid, colony in self._colonies.items():
            result[cid] = {
                "agent_count": colony.agent_count,
                "max_agents": colony.config.max_agents,
                "task_count": colony.task_count,
                "utilization_pct": round(colony.agent_count / colony.config.max_agents * 100, 1)
                if colony.config.max_agents > 0
                else 0.0,
                "status": colony.status.value,
            }
        return result

    # ── Health scoring ─────────────────────────────────────────────────────

    def compute_all_health(self) -> Dict[str, ColonyHealth]:
        """Compute health for every colony."""
        return {cid: colony.compute_health() for cid, colony in self._colonies.items()}

    def get_unhealthy_colonies(self, threshold: float = 0.5) -> List[Colony]:
        """Return colonies below the health threshold."""
        unhealthy = []
        for colony in self._colonies.values():
            health = colony.compute_health()
            if health.overall_score < threshold:
                unhealthy.append(colony)
        return unhealthy

    # ── Inter-colony communication ─────────────────────────────────────────

    def route_inter_colony_message(self, source_colony_id: str, target_colony_id: str, message: Dict[str, Any]) -> str:
        """Route a message from one colony to another."""
        target = self._colonies.get(target_colony_id)
        if target is None:
            raise ColonyNotFoundError(target_colony_id)
        source = self._colonies.get(source_colony_id)
        if source is None:
            raise ColonyNotFoundError(source_colony_id)
        return source.send_inter_colony(target_colony_id, message)

    def get_pending_inter_colony(self, colony_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve pending inter-colony messages for a colony."""
        colony = self.get_colony_or_raise(colony_id)
        return colony.receive_inter_colony(limit=limit)

    # ── Scaling ────────────────────────────────────────────────────────────

    async def scale_colony(self, colony_id: str, scale: ColonyScale) -> Colony:
        """Change a colony's scale preset, updating its config."""
        colony = self.get_colony_or_raise(colony_id)
        preset = SCALE_PRESETS.get(scale)
        if preset is None:
            raise ValueError(f"Unknown scale preset: {scale}")
        colony.scale = scale
        colony.config.scale = scale
        colony.config.max_agents = preset["max_agents"]
        colony.config.hands = preset["hands"]
        logger.info("Colony %s scaled to %s (max_agents=%d)", colony_id, scale.value, preset["max_agents"])
        return colony

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def colony_count(self) -> int:
        return len(self._colonies)

    @property
    def total_agents(self) -> int:
        return sum(c.agent_count for c in self._colonies.values())
