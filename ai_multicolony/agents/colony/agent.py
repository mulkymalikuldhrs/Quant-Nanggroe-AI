"""Colony agent - from OpenFang colony + MultiColony patterns.

Orchestrates multiple agents in a colony for complex task execution,
with task routing, hand coordination, and failure recovery.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState, SubagentSpawn
from ai_multicolony.types.colony import ColonyConfig, ColonyTask, ColonyStatus, ColonyState, HandType
from ai_multicolony.agents.colony.prompts import (
    COLONY_SYSTEM_PROMPT,
    COLONY_COORDINATION_PROMPT,
    COLONY_STATUS_PROMPT,
    COLONY_TASK_ROUTING_PROMPT,
    COLONY_HAND_COORDINATION_PROMPT,
    COLONY_FAILURE_RECOVERY_PROMPT,
)

logger = get_logger(__name__)

# Default task routing table: task keyword -> agent role
_DEFAULT_ROUTING: dict[str, AgentRole] = {
    "code": AgentRole.CODER,
    "program": AgentRole.CODER,
    "debug": AgentRole.CODER,
    "implement": AgentRole.CODER,
    "browse": AgentRole.BROWSER,
    "website": AgentRole.BROWSER,
    "scrape": AgentRole.BROWSER,
    "search": AgentRole.RESEARCHER,
    "research": AgentRole.RESEARCHER,
    "investigate": AgentRole.RESEARCHER,
    "analyze": AgentRole.RESEARCHER,
    "security": AgentRole.SECURITY,
    "vulnerability": AgentRole.SECURITY,
    "audit": AgentRole.SECURITY,
    "scan": AgentRole.SECURITY,
    "voice": AgentRole.VOICE,
    "speak": AgentRole.VOICE,
    "listen": AgentRole.VOICE,
    "plan": AgentRole.PLANNER,
    "decompose": AgentRole.PLANNER,
    "execute": AgentRole.EXECUTOR,
    "run": AgentRole.EXECUTOR,
}


class ColonyAgent(BaseAgent):
    """Colony overseer agent for multi-agent coordination.

    From OpenFang colony management and MultiColony coordination.
    Orchestrates multiple agents to accomplish complex tasks through
    delegation, monitoring, and failure recovery.

    State-specific behavior:
    - IDLE: Ready for colony coordination tasks
    - RUNNING: Actively coordinating agents and managing tasks
    - THINKING: Planning task routing or analyzing status
    - WAITING: Waiting for a subagent to complete
    - PAUSED: Colony operations paused
    - ERROR: Coordination error, attempts recovery
    """

    # Colony tracking
    _task_queue: list[ColonyTask]
    _completed_tasks: list[dict[str, Any]]
    _failed_tasks: list[dict[str, Any]]
    _colony_config: Optional[ColonyConfig]
    _routing_table: dict[str, AgentRole]

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.COLONY,
                name="colony-agent",
                description="Colony overseer for multi-agent coordination",
                tools=["memory", "channel", "search"],
                system_prompt=COLONY_SYSTEM_PROMPT,
                temperature=0.2,
                max_iterations=25,  # More iterations for colony management
                capabilities=AgentCapabilities(
                    colony_management=True,
                    planning=True,
                    memory_management=True,
                    web_search=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = COLONY_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["memory", "channel", "search"]

        super().__init__(config=config, **kwargs)
        self._task_queue = []
        self._completed_tasks = []
        self._failed_tasks = []
        self._colony_config = None
        self._routing_table = dict(_DEFAULT_ROUTING)

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names ColonyAgent requires.

        Returns:
            Tools needed for colony management.
        """
        return ["memory", "channel", "search"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Colony agent."""
        return self.config.system_prompt or COLONY_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "colony_agent_running",
            agent_id=self.agent_id,
            pending=len(self._task_queue),
            completed=len(self._completed_tasks),
            failed=len(self._failed_tasks),
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state."""
        logger.warning(
            "colony_agent_error",
            agent_id=self.agent_id,
            error_count=self.error_count,
            pending=len(self._task_queue),
        )

    def _on_enter_waiting(self) -> None:
        """Hook called when entering WAITING state."""
        logger.info(
            "colony_agent_waiting",
            agent_id=self.agent_id,
            subagents=len(self.subagent_ids),
        )

    # ------------------------------------------------------------------
    # Core coordination methods
    # ------------------------------------------------------------------

    async def coordinate(self, task: str, available_hands: Optional[list[str]] = None) -> str:
        """Coordinate a colony task by delegating to specialized agents.

        Args:
            task: The task to coordinate.
            available_hands: Available hand types for delegation.

        Returns:
            Coordination result.
        """
        hands_str = ", ".join(available_hands or ["manus", "coder", "browser", "researcher"])
        prompt = COLONY_COORDINATION_PROMPT.format(
            task=task,
            hands=hands_str,
            budget="unlimited",
            deadline="none",
        )
        result = await self.run(prompt)

        self._completed_tasks.append({
            "task": task[:200],
            "type": "coordination",
            "result_preview": result[:200],
        })

        return result

    async def delegate(self, role: AgentRole, task: str, tools: Optional[list[str]] = None) -> str:
        """Delegate a task to a subagent.

        Spawns a subagent of the specified role and waits for its result.

        Args:
            role: The role of the subagent.
            task: The task to delegate.
            tools: Tools the subagent should have.

        Returns:
            The subagent's result.
        """
        spawn = SubagentSpawn(
            role=role,
            task=task,
            tools=tools or [],
        )
        return await self.spawn_subagent(spawn)

    async def route_task(self, task: str) -> AgentRole:
        """Route a task to the most appropriate agent role.

        Uses keyword matching against the routing table. Falls back
        to the LLM for complex routing decisions.

        Args:
            task: The task description.

        Returns:
            The recommended AgentRole for the task.
        """
        task_lower = task.lower()

        # Check routing table for keyword matches
        for keyword, role in self._routing_table.items():
            if keyword in task_lower:
                logger.info(
                    "task_routed",
                    agent_id=self.agent_id,
                    keyword=keyword,
                    role=role.value,
                )
                return role

        # Fall back to LLM-based routing
        available_agents = list(self._routing_table.values())
        unique_agents = list(set(available_agents))
        agent_names = [a.value for a in unique_agents]

        prompt = COLONY_TASK_ROUTING_PROMPT.format(
            task=task,
            available_agents=", ".join(agent_names),
            current_load="All agents available",
        )

        provider = self._get_llm_provider()
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a task routing assistant. Respond with only the agent type name."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=50,
            temperature=0.0,
        )

        # Parse the response for an agent role
        for role in AgentRole:
            if role.value in response.content.lower():
                return role

        # Default to manus for ambiguous tasks
        return AgentRole.MANUS

    async def delegate_auto(self, task: str) -> str:
        """Automatically route and delegate a task.

        Routes the task to the best agent type and delegates it.

        Args:
            task: The task to route and delegate.

        Returns:
            The subagent's result.
        """
        role = await self.route_task(task)
        logger.info("auto_delegating", agent_id=self.agent_id, task=task[:100], role=role.value)
        return await self.delegate(role, task)

    # ------------------------------------------------------------------
    # Status assessment
    # ------------------------------------------------------------------

    async def assess_status(self) -> str:
        """Assess the current colony status.

        Returns:
            Status assessment with recommendations.
        """
        total_cost = self.cost_incurred
        total_tokens = self.tokens_used

        prompt = COLONY_STATUS_PROMPT.format(
            active_agents=len(self.subagent_ids),
            pending_tasks=len(self._task_queue),
            completed_tasks=len(self._completed_tasks),
            errors=len(self._failed_tasks),
            total_cost=total_cost,
            total_tokens=total_tokens,
        )

        provider = self._get_llm_provider()
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a colony status assessor."},
                {"role": "user", "content": prompt},
            ],
        )

        return response.content

    def get_colony_status(self) -> ColonyStatus:
        """Get the structured colony status.

        Returns:
            ColonyStatus with current metrics.
        """
        return ColonyStatus(
            colony_id=self.config.colony_id or self.agent_id,
            name=self.name,
            state=ColonyState.ACTIVE if self.state == AgentState.RUNNING else ColonyState.IDLE,
            agent_count=len(self.subagent_ids),
            active_agents=sum(1 for _ in self.subagent_ids),  # Simplified
            pending_tasks=len(self._task_queue),
            completed_tasks=len(self._completed_tasks),
            failed_tasks=len(self._failed_tasks),
            total_cost=self.cost_incurred,
            total_tokens=self.tokens_used,
        )

    # ------------------------------------------------------------------
    # Task queue management
    # ------------------------------------------------------------------

    def add_task(self, task: ColonyTask) -> None:
        """Add a task to the colony task queue.

        Args:
            task: The colony task to add.
        """
        self._task_queue.append(task)
        logger.info(
            "task_added",
            agent_id=self.agent_id,
            task_id=task.id,
            title=task.title[:50],
        )

    def add_tasks(self, tasks: list[ColonyTask]) -> None:
        """Add multiple tasks to the colony task queue.

        Args:
            tasks: The colony tasks to add.
        """
        for task in tasks:
            self._task_queue.append(task)
        logger.info("tasks_added", agent_id=self.agent_id, count=len(tasks))

    def get_pending_tasks(self) -> list[ColonyTask]:
        """Get all pending tasks in the queue.

        Returns:
            List of pending ColonyTask objects.
        """
        return list(self._task_queue)

    def pop_next_task(self) -> Optional[ColonyTask]:
        """Pop the next task from the queue.

        Returns:
            The next ColonyTask, or None if the queue is empty.
        """
        if self._task_queue:
            return self._task_queue.pop(0)
        return None

    # ------------------------------------------------------------------
    # Failure recovery
    # ------------------------------------------------------------------

    async def recover_from_failure(
        self,
        task: str,
        failed_agent: str,
        failure_reason: str,
        partial_results: str = "",
    ) -> str:
        """Recover from a subagent failure.

        Args:
            task: The original task.
            failed_agent: The role of the failed agent.
            failure_reason: Why the agent failed.
            partial_results: Any partial results obtained.

        Returns:
            Recovery plan or re-delegation result.
        """
        prompt = COLONY_FAILURE_RECOVERY_PROMPT.format(
            task=task,
            failed_agent=failed_agent,
            failure_reason=failure_reason,
            partial_results=partial_results or "No partial results",
        )

        provider = self._get_llm_provider()
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a colony failure recovery assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
        )

        # Record failure
        self._failed_tasks.append({
            "task": task[:200],
            "failed_agent": failed_agent,
            "failure_reason": failure_reason[:200],
            "recovery_plan": response.content[:200],
        })

        return response.content

    # ------------------------------------------------------------------
    # Routing table management
    # ------------------------------------------------------------------

    def update_routing(self, keyword: str, role: AgentRole) -> None:
        """Update the task routing table.

        Args:
            keyword: Task keyword to match.
            role: Agent role to route to.
        """
        self._routing_table[keyword.lower()] = role
        logger.info("routing_updated", keyword=keyword, role=role.value)

    def get_routing_table(self) -> dict[str, str]:
        """Get the current routing table.

        Returns:
            Dictionary mapping keywords to agent role names.
        """
        return {k: v.value for k, v in self._routing_table.items()}

    # ------------------------------------------------------------------
    # Colony history
    # ------------------------------------------------------------------

    def get_completed_tasks(self) -> list[dict[str, Any]]:
        """Get the list of completed colony tasks.

        Returns:
            List of completed task entries.
        """
        return list(self._completed_tasks)

    def get_failed_tasks(self) -> list[dict[str, Any]]:
        """Get the list of failed colony tasks.

        Returns:
            List of failed task entries.
        """
        return list(self._failed_tasks)

    def clear_history(self) -> None:
        """Clear all colony history."""
        self._task_queue.clear()
        self._completed_tasks.clear()
        self._failed_tasks.clear()
