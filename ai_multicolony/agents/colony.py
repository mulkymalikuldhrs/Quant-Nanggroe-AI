"""Colony agent – colony coordination, oversight, and hand management.

Implements colony overseer logic with 7 hand types, task delegation via A2A,
heartbeat monitoring, and resource balancing across the colony.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .base import BaseAgent
from ..types import (
    AgentSpec,
    AgentType,
    AgentState,
    AutonomyLevel,
    ColonyConfig,
    HandType,
    Task,
    TaskResult,
)
from ..colony.hands import Hand, HandManager

logger = logging.getLogger(__name__)


class ColonyMetrics:
    """Tracks colony-level metrics for monitoring and balancing."""

    def __init__(self):
        self.total_tasks_delegated: int = 0
        self.total_tasks_completed: int = 0
        self.total_tasks_failed: int = 0
        self.heartbeat_misses: int = 0
        self.rebalance_count: int = 0
        self.last_heartbeat_check: Optional[datetime] = None

    @property
    def task_success_rate(self) -> float:
        total = self.total_tasks_completed + self.total_tasks_failed
        if total == 0:
            return 1.0
        return self.total_tasks_completed / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks_delegated": self.total_tasks_delegated,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_failed": self.total_tasks_failed,
            "task_success_rate": self.task_success_rate,
            "heartbeat_misses": self.heartbeat_misses,
            "rebalance_count": self.rebalance_count,
        }


class ColonyAgent(BaseAgent):
    """Colony coordination agent – manages colony lifecycle and agent assignment.

    Features
    --------
    * **Colony overseer logic** – track agent health, coordinate tasks.
    * **Hand management** – organize agents into 7 specialist hands.
    * **Task delegation** – assign tasks to the best hand/agent via A2A.
    * **Heartbeat monitoring** – detect unresponsive agents.
    * **Resource balancing** – redistribute agents across hands.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.COLONY, autonomy_level=2)
        if spec.agent_type != AgentType.COLONY:
            spec.agent_type = AgentType.COLONY
        super().__init__(spec=spec, **kwargs)
        self._managed_agents: Dict[str, BaseAgent] = {}
        self._colony_config: Optional[ColonyConfig] = None
        self._hand_manager = HandManager()
        self._metrics = ColonyMetrics()
        self._heartbeat_timeouts: Dict[str, datetime] = {}
        self._delegation_history: List[Dict[str, Any]] = []

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Execute colony coordination task based on ``payload.action``."""
        action = task.payload.get("action", "status")
        if action == "status":
            return await self._colony_status(task)
        elif action == "assign":
            return await self._assign_task(task)
        elif action == "delegate":
            return await self._delegate_task(task)
        elif action == "rebalance":
            return await self._rebalance(task)
        elif action == "heartbeat_check":
            return await self._heartbeat_check(task)
        elif action == "add_agent":
            return self._add_agent_action(task)
        elif action == "remove_agent":
            return self._remove_agent_action(task)
        elif action == "hand_status":
            return self._hand_status()
        elif action == "configure":
            return self._configure_colony(task)
        else:
            return {"action": action, "result": f"Unknown colony action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle A2A messages for colony coordination."""
        msg_type = message.get("message_type", "")
        if msg_type == "agent_registration":
            payload = message.get("payload", {})
            return {"registered": True, "colony_id": self.colony_id}
        elif msg_type == "task_request":
            return await self._handle_task_request(message.get("payload", {}))
        elif msg_type == "heartbeat":
            agent_id = message.get("payload", {}).get("agent_id", "")
            self._heartbeat_timeouts[agent_id] = datetime.now(timezone.utc)
            return {"acknowledged": True}
        elif msg_type == "agent_health":
            agent_id = message.get("payload", {}).get("agent_id", "")
            health = message.get("payload", {}).get("health_score", 1.0)
            return {"tracked": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare colony capabilities."""
        return [
            "colony_management", "task_delegation", "hand_management",
            "heartbeat_monitoring", "resource_balancing", "agent_coordination",
            "a2a_delegation",
        ]

    # ── Colony status ──

    async def _colony_status(self, task: Task) -> Dict[str, Any]:
        """Return comprehensive colony status."""
        hand_status = self._hand_manager.get_all_status()
        return {
            "action": "status",
            "colony_id": self.colony_id,
            "agent_count": len(self._managed_agents),
            "agents": list(self._managed_agents.keys()),
            "hands": hand_status,
            "metrics": self._metrics.to_dict(),
            "config": self._colony_config.model_dump() if self._colony_config else None,
        }

    # ── Hand management ──

    def _hand_status(self) -> Dict[str, Any]:
        """Return status of all 7 hands."""
        return {
            "action": "hand_status",
            "hands": self._hand_manager.get_all_status(),
            "available_hands": [h.hand_type.value for h in self._hand_manager.get_available_hands()],
        }

    # ── Task delegation ──

    async def _assign_task(self, task: Task) -> Dict[str, Any]:
        """Assign a task to a specific agent.

        Payload fields:
        * ``target_agent`` – agent ID to assign the task to.
        * ``task_description`` – description of the task.
        """
        target_agent = task.payload.get("target_agent", "")
        task_description = task.payload.get("task_description", "")

        self._metrics.total_tasks_delegated += 1

        # Delegate via A2A
        if target_agent in self._managed_agents:
            agent = self._managed_agents[target_agent]
            message_id = await self.send_message(
                target_agent,
                "task_delegation",
                {"task_id": task.task_id, "description": task_description},
            )
            self._delegation_history.append({
                "task_id": task.task_id,
                "target_agent": target_agent,
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self._metrics.total_tasks_completed += 1
            return {"action": "assign", "target_agent": target_agent, "assigned": True}

        self._metrics.total_tasks_failed += 1
        return {"action": "assign", "target_agent": target_agent, "assigned": False, "error": "agent_not_found"}

    async def _delegate_task(self, task: Task) -> Dict[str, Any]:
        """Delegate a task to the best hand/agent automatically.

        Selects the appropriate hand based on task type, then picks the
        least-loaded agent within that hand.
        """
        task_type = task.payload.get("task_type", "compute")
        task_description = task.payload.get("description", task.description)

        # Map task type to hand type
        hand_type = self._map_task_to_hand(task_type)
        hand = self._hand_manager.get_hand(hand_type)

        if not hand.is_available:
            # Try to find any available hand
            available = self._hand_manager.get_available_hands()
            if available:
                hand = available[0]
            else:
                self._metrics.total_tasks_failed += 1
                return {"action": "delegate", "success": False, "error": "no_available_agents"}

        # Pick least-loaded agent in hand
        target_agent_id = hand._agents[0] if hand._agents else None

        self._metrics.total_tasks_delegated += 1

        if target_agent_id and target_agent_id in self._managed_agents:
            message_id = await self.send_message(
                target_agent_id,
                "task_delegation",
                {"task_id": task.task_id, "description": task_description, "hand": hand_type.value},
            )
            self._delegation_history.append({
                "task_id": task.task_id,
                "hand": hand_type.value,
                "target_agent": target_agent_id,
                "message_id": message_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self._metrics.total_tasks_completed += 1
            return {
                "action": "delegate",
                "success": True,
                "hand": hand_type.value,
                "target_agent": target_agent_id,
            }

        self._metrics.total_tasks_failed += 1
        return {"action": "delegate", "success": False, "error": "no_agent_in_hand"}

    async def _handle_task_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming task request from A2A."""
        task_type = payload.get("task_type", "compute")
        task_id = payload.get("task_id", str(uuid.uuid4().hex[:12]))
        hand_type = self._map_task_to_hand(task_type)
        hand = self._hand_manager.get_hand(hand_type)
        return {
            "accepted": hand.is_available,
            "hand": hand_type.value,
            "task_id": task_id,
        }

    def _map_task_to_hand(self, task_type: str) -> HandType:
        """Map a task type string to a HandType."""
        mapping = {
            "security": HandType.SECURITY,
            "code": HandType.CODE,
            "research": HandType.RESEARCH,
            "browser": HandType.BROWSER,
            "voice": HandType.VOICE,
            "compute": HandType.COMPUTE,
            "integration": HandType.INTEGRATION,
            "execute": HandType.COMPUTE,
            "plan": HandType.CODE,
            "scan": HandType.SECURITY,
        }
        return mapping.get(task_type, HandType.COMPUTE)

    # ── Rebalancing ──

    async def _rebalance(self, task: Task) -> Dict[str, Any]:
        """Rebalance agents across hands based on workload.

        Moves agents from under-utilized hands to over-utilized ones.
        """
        hand_status = self._hand_manager.get_all_status()
        agents_moved = 0

        # Find over/under utilized hands
        over_loaded: List[str] = []
        under_loaded: List[str] = []

        for hand_type, status in hand_status.items():
            pending = status.get("pending_tasks", 0)
            agent_count = status.get("agent_count", 0)
            if pending > agent_count * 2:
                over_loaded.append(hand_type)
            elif agent_count > 0 and pending == 0:
                under_loaded.append(hand_type)

        # Move one agent from under-loaded to over-loaded
        if under_loaded and over_loaded:
            source_type = under_loaded[0]
            target_type = over_loaded[0]

            source_hand = self._hand_manager.get_hand(HandType(source_type))
            target_hand = self._hand_manager.get_hand(HandType(target_type))

            if source_hand._agents and target_hand.agent_count < target_hand.max_replicas:
                agent_id = source_hand._agents[-1]
                source_hand.remove_agent(agent_id)
                target_hand.add_agent(agent_id)
                agents_moved = 1

        self._metrics.rebalance_count += 1

        return {
            "action": "rebalance",
            "agents_moved": agents_moved,
            "over_loaded": over_loaded,
            "under_loaded": under_loaded,
            "reason": "workload_balancing",
        }

    # ── Heartbeat monitoring ──

    async def _heartbeat_check(self, task: Task) -> Dict[str, Any]:
        """Check heartbeats of all managed agents.

        Identifies agents that haven't sent a heartbeat within the expected
        interval and flags them as potentially unresponsive.
        """
        timeout_seconds = 60  # 60 seconds without heartbeat = unresponsive
        now = datetime.now(timezone.utc)
        unresponsive: List[str] = []

        for agent_id, agent in self._managed_agents.items():
            last_hb = agent._last_heartbeat
            if last_hb is None:
                unresponsive.append(agent_id)
            elif (now - last_hb).total_seconds() > timeout_seconds:
                unresponsive.append(agent_id)

        self._metrics.heartbeat_misses += len(unresponsive)
        self._metrics.last_heartbeat_check = now

        return {
            "action": "heartbeat_check",
            "total_agents": len(self._managed_agents),
            "unresponsive": unresponsive,
            "unresponsive_count": len(unresponsive),
            "healthy_count": len(self._managed_agents) - len(unresponsive),
        }

    # ── Agent management ──

    def _add_agent_action(self, task: Task) -> Dict[str, Any]:
        """Add an agent to the colony and assign to a hand."""
        agent_id = task.payload.get("agent_id", "")
        hand_type_str = task.payload.get("hand_type", "compute")
        agent = task.payload.get("agent")

        if agent:
            self.add_agent(agent)
            hand_type = HandType(hand_type_str) if hand_type_str in [h.value for h in HandType] else HandType.COMPUTE
            self._hand_manager.assign_agent(hand_type, agent_id or agent.agent_id)

        return {"action": "add_agent", "agent_id": agent_id, "added": True}

    def _remove_agent_action(self, task: Task) -> Dict[str, Any]:
        """Remove an agent from the colony."""
        agent_id = task.payload.get("agent_id", "")
        self.remove_agent(agent_id)
        return {"action": "remove_agent", "agent_id": agent_id, "removed": True}

    def add_agent(self, agent: BaseAgent) -> None:
        """Add an agent to the colony's managed agents."""
        self._managed_agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the colony."""
        self._managed_agents.pop(agent_id, None)
        # Remove from hands
        for hand_type in HandType:
            hand = self._hand_manager.get_hand(hand_type)
            hand.remove_agent(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Look up a managed agent by ID."""
        return self._managed_agents.get(agent_id)

    # ── Configuration ──

    def _configure_colony(self, task: Task) -> Dict[str, Any]:
        """Apply colony configuration."""
        config_data = task.payload.get("config", {})
        if config_data:
            self._colony_config = ColonyConfig(**config_data)
        return {"action": "configure", "configured": True}

    # ── Accessors ──

    @property
    def metrics(self) -> ColonyMetrics:
        """Colony-level metrics."""
        return self._metrics

    @property
    def hand_manager(self) -> HandManager:
        """The hand manager for this colony."""
        return self._hand_manager

    @property
    def managed_agent_count(self) -> int:
        """Number of managed agents."""
        return len(self._managed_agents)
