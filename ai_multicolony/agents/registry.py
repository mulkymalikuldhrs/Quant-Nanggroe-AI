"""Agent registry – manages agent types, instances, and discovery.

The :class:`AgentRegistry` is the central bookkeeping service for the
AI-MultiColony ecosystem.  It tracks every live agent instance, supports
capability-based search, colony membership queries, health monitoring, and
A2A capability advertisement.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Type

from .base import BaseAgent, EventBus
from .manus import ManusAgent
from .planner import PlannerAgent
from .executor import ExecutorAgent
from .coder import CoderAgent
from .browser import BrowserAgent
from .voice import VoiceAgent
from .security import SecurityAgent
from .researcher import ResearcherAgent
from .colony import ColonyAgent
from ..types import AgentInfo, AgentSpec, AgentType, AgentState, AutonomyLevel, EventType

logger = logging.getLogger(__name__)

AGENT_TYPES: Dict[AgentType, Type[BaseAgent]] = {
    AgentType.MANUS: ManusAgent,
    AgentType.PLANNER: PlannerAgent,
    AgentType.EXECUTOR: ExecutorAgent,
    AgentType.CODER: CoderAgent,
    AgentType.BROWSER: BrowserAgent,
    AgentType.VOICE: VoiceAgent,
    AgentType.SECURITY: SecurityAgent,
    AgentType.RESEARCHER: ResearcherAgent,
    AgentType.COLONY: ColonyAgent,
}


class AgentRegistry:
    """Central registry for agent types and instances.

    Features
    --------
    * **Register / unregister** agents with automatic type counting.
    * **Capability-based search** – find agents whose declared capabilities
      match a query.
    * **Colony membership tracking** – group agents by colony.
    * **Health monitoring** – retrieve health snapshots for all or filtered
      agents.
    * **A2A capability advertisement** – publish capability advertisements
      over the event bus so that other agents can discover peers.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus or EventBus()
        self._agents: Dict[str, BaseAgent] = {}
        self._type_counts: Dict[AgentType, int] = {}
        self._capabilities: Dict[str, Set[str]] = {}
        self._colony_members: Dict[str, Set[str]] = {}

    # ── Type management ──

    def register_type(self, agent_type: AgentType, agent_class: Type[BaseAgent]) -> None:
        """Register or replace the class for an agent type."""
        AGENT_TYPES[agent_type] = agent_class

    # ── Instance lifecycle ──

    def create_agent(
        self,
        agent_type: AgentType,
        spec: Optional[AgentSpec] = None,
        tools: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """Create a new agent instance and register it.

        Parameters
        ----------
        agent_type:
            The type of agent to create.
        spec:
            Optional agent specification (id, autonomy, colony, etc.).
        tools:
            Optional pre-bound tool mapping.

        Returns
        -------
        BaseAgent
            The newly created agent.
        """
        agent_class = AGENT_TYPES.get(agent_type)
        if agent_class is None:
            raise ValueError(f"Unknown agent type: {agent_type}")
        spec = spec or AgentSpec(agent_type=agent_type)
        agent = agent_class(spec=spec, event_bus=self._event_bus, tools=tools)
        self._agents[agent.agent_id] = agent
        self._type_counts[agent_type] = self._type_counts.get(agent_type, 0) + 1

        # Track capabilities
        try:
            caps = agent.capabilities()
            self._capabilities[agent.agent_id] = set(caps)
        except Exception:
            self._capabilities[agent.agent_id] = set()

        # Track colony membership
        if agent.colony_id:
            if agent.colony_id not in self._colony_members:
                self._colony_members[agent.colony_id] = set()
            self._colony_members[agent.colony_id].add(agent.agent_id)

        # A2A capability advertisement
        self._advertise_capabilities(agent)

        return agent

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent by ID.

        Removes it from type counts, capability index, and colony membership.
        """
        agent = self._agents.pop(agent_id, None)
        if agent is None:
            return
        # Type count
        if agent.agent_type in self._type_counts:
            self._type_counts[agent.agent_type] = max(0, self._type_counts[agent.agent_type] - 1)
        # Capabilities
        self._capabilities.pop(agent_id, None)
        # Colony
        if agent.colony_id and agent.colony_id in self._colony_members:
            self._colony_members[agent.colony_id].discard(agent_id)
            if not self._colony_members[agent.colony_id]:
                del self._colony_members[agent.colony_id]

    def remove_agent(self, agent_id: str) -> None:
        """Alias for :meth:`unregister_agent` (backward compat)."""
        self.unregister_agent(agent_id)

    # ── Queries ──

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Look up an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        agent_type: Optional[AgentType] = None,
        state: Optional[AgentState] = None,
    ) -> List[BaseAgent]:
        """List agents, optionally filtered by type and/or state."""
        agents = list(self._agents.values())
        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        if state:
            agents = [a for a in agents if a.state == state]
        return agents

    def list_agent_info(self, agent_type: Optional[AgentType] = None) -> List[AgentInfo]:
        """Return :class:`AgentInfo` snapshots for all or filtered agents."""
        return [a.info for a in self.list_agents(agent_type=agent_type)]

    def get_agents_by_colony(self, colony_id: str) -> List[BaseAgent]:
        """Return all agents belonging to *colony_id*."""
        return [a for a in self._agents.values() if a.colony_id == colony_id]

    def get_type_count(self, agent_type: AgentType) -> int:
        """Number of registered agents of *agent_type*."""
        return self._type_counts.get(agent_type, 0)

    @property
    def total_agents(self) -> int:
        """Total number of registered agent instances."""
        return len(self._agents)

    # ── Capability-based search ──

    def search_by_capability(self, capability: str, colony_id: Optional[str] = None) -> List[BaseAgent]:
        """Find agents that declare *capability*.

        Parameters
        ----------
        capability:
            A capability string to match.
        colony_id:
            If provided, restrict results to agents in this colony.

        Returns
        -------
        list[BaseAgent]
            Matching agents sorted by health score (best first).
        """
        results: List[BaseAgent] = []
        for agent_id, caps in self._capabilities.items():
            if capability in caps:
                agent = self._agents.get(agent_id)
                if agent is None:
                    continue
                if colony_id and agent.colony_id != colony_id:
                    continue
                results.append(agent)
        results.sort(key=lambda a: a.health_score, reverse=True)
        return results

    def search_by_capabilities(self, capabilities: List[str], colony_id: Optional[str] = None) -> List[BaseAgent]:
        """Find agents that declare **all** of the given capabilities."""
        if not capabilities:
            return []
        result_sets = [
            set(a.agent_id for a in self.search_by_capability(c, colony_id))
            for c in capabilities
        ]
        # Intersection
        common_ids = result_sets[0]
        for s in result_sets[1:]:
            common_ids &= s
        agents = [self._agents[aid] for aid in common_ids if aid in self._agents]
        agents.sort(key=lambda a: a.health_score, reverse=True)
        return agents

    # ── Colony membership ──

    def get_colony_ids(self) -> List[str]:
        """Return all known colony IDs."""
        return list(self._colony_members.keys())

    def get_colony_agent_count(self, colony_id: str) -> int:
        """Number of agents in a colony."""
        return len(self._colony_members.get(colony_id, set()))

    # ── Health monitoring ──

    async def get_health_report(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Return a detailed health report for a single agent."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return None
        return await agent.health_check()

    async def get_all_health_reports(self) -> Dict[str, Dict[str, Any]]:
        """Return health reports for all registered agents."""
        reports: Dict[str, Dict[str, Any]] = {}
        for agent_id, agent in self._agents.items():
            reports[agent_id] = await agent.health_check()
        return reports

    def get_unhealthy_agents(self, threshold: float = 0.7) -> List[BaseAgent]:
        """Return agents with health score below *threshold*."""
        return [a for a in self._agents.values() if a.health_score < threshold]

    # ── A2A capability advertisement ──

    def _advertise_capabilities(self, agent: BaseAgent) -> None:
        """Publish an A2A capability advertisement for *agent*."""
        try:
            caps = agent.capabilities()
            # We fire-and-forget; event bus may not be running in sync context
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._event_bus.publish_typed(
                    EventType.A2A_MESSAGE,
                    "registry",
                    {
                        "agent_id": agent.agent_id,
                        "agent_type": agent.agent_type.value,
                        "colony_id": agent.colony_id,
                        "capabilities": caps,
                        "advertisement": True,
                    },
                ))
            except RuntimeError:
                # No running loop – skip async publish
                pass
        except Exception as e:
            logger.debug(f"Capability advertisement skipped for {agent.agent_id}: {e}")

    # ── Cleanup ──

    def clear(self) -> None:
        """Remove all registered agents and reset counters."""
        self._agents.clear()
        self._type_counts.clear()
        self._capabilities.clear()
        self._colony_members.clear()

    @property
    def event_bus(self) -> EventBus:
        """The event bus attached to this registry."""
        return self._event_bus
