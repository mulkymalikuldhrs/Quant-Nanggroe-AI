"""Planner agent - from AI-Manus PlanActFlow pattern.

Specializes in task decomposition, planning, scheduling, and
dependency analysis. Creates structured execution plans that can
be handed off to ExecutorAgent instances or a ColonyAgent.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from ai_multicolony.types.colony import ColonyTask
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.agents.planner.prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_DECOMPOSITION_PROMPT,
    PLANNER_REPLAN_PROMPT,
    PLANNER_VERIFICATION_PROMPT,
)

logger = get_logger(__name__)


class PlannerAgent(BaseAgent):
    """Planner agent for task decomposition and plan creation.

    From AI-Manus PlanActFlow pattern. Analyzes tasks, breaks them
    into subtasks, and creates execution plans with dependency tracking.

    State-specific behavior:
    - IDLE: Ready to accept planning tasks
    - RUNNING: Actively decomposing or replanning
    - THINKING: Analyzing task structure and dependencies
    - PAUSED: Waiting for external input or clarification
    - ERROR: Recovery attempted by simplifying the plan
    """

    # Track planning history for replanning
    _plan_history: list[dict[str, Any]]

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.PLANNER,
                name="planner-agent",
                description="Task decomposition and planning specialist",
                tools=["memory", "search"],
                system_prompt=PLANNER_SYSTEM_PROMPT,
                temperature=0.3,  # Slightly higher for creative planning
                capabilities=AgentCapabilities(
                    planning=True,
                    web_search=True,
                    memory_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = PLANNER_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["memory", "search"]

        super().__init__(config=config, **kwargs)
        self._plan_history = []

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names PlannerAgent requires.

        Returns:
            Tools needed for planning operations.
        """
        return ["memory", "search"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Planner agent."""
        return self.config.system_prompt or PLANNER_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "planner_agent_running",
            agent_id=self.agent_id,
            plans_created=len(self._plan_history),
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state — attempt plan simplification."""
        logger.warning(
            "planner_agent_error",
            agent_id=self.agent_id,
            error_count=self.error_count,
        )
        # Store error context for recovery
        memory = self._get_memory_manager()
        memory.add_entry(
            agent_id=self.agent_id,
            content=f"Planner entered error state. Plans created so far: {len(self._plan_history)}",
            memory_type=MemoryType.WORKING,
            importance=0.8,
            source="agent",
        )

    # ------------------------------------------------------------------
    # Core planning methods
    # ------------------------------------------------------------------

    async def plan(self, task: str) -> list[ColonyTask]:
        """Create a plan for the given task.

        Uses the LLM to decompose the task into structured subtasks,
        then parses the response into ColonyTask objects.

        Args:
            task: The task to plan for.

        Returns:
            List of ColonyTask subtasks ordered by execution priority.
        """
        result = await self.run(task)

        # Parse the plan from the response
        subtasks = self._parse_plan(result, task)

        # Store plan in history for replanning
        self._plan_history.append({
            "task": task,
            "subtasks": len(subtasks),
            "result_preview": result[:500],
        })

        # Store plan in memory
        memory = self._get_memory_manager()
        memory.add_entry(
            agent_id=self.agent_id,
            content=f"Plan created for '{task}': {len(subtasks)} subtasks",
            memory_type=MemoryType.LONG_TERM,
            importance=0.7,
            source="planner",
        )

        return subtasks

    async def plan_with_decomposition(self, task: str) -> list[ColonyTask]:
        """Create a plan using explicit decomposition prompting.

        Uses the decomposition prompt template for more structured output.

        Args:
            task: The task to plan for.

        Returns:
            List of ColonyTask subtasks.
        """
        prompt = PLANNER_DECOMPOSITION_PROMPT.format(task=task)
        result = await self.run(prompt)
        return self._parse_plan(result, task)

    async def replan(self, original_plan: str, issues: str) -> list[ColonyTask]:
        """Re-plan based on issues encountered during execution.

        Args:
            original_plan: The original plan text.
            issues: Description of issues encountered.

        Returns:
            Revised list of subtasks.
        """
        replan_prompt = PLANNER_REPLAN_PROMPT.format(
            original_plan=original_plan,
            issues=issues,
        )

        # Store replan attempt in history
        self._plan_history.append({
            "task": f"replan: {issues[:100]}",
            "subtasks": 0,
            "result_preview": "",
        })

        return await self.plan(replan_prompt)

    async def verify_plan(self, plan_text: str) -> dict[str, Any]:
        """Verify a plan is complete and executable.

        Args:
            plan_text: The plan text to verify.

        Returns:
            Dictionary with 'valid' (bool) and 'issues' (list[str]).
        """
        verification_prompt = PLANNER_VERIFICATION_PROMPT.format(plan=plan_text)

        provider = self._get_llm_provider()
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a plan verification assistant."},
                {"role": "user", "content": verification_prompt},
            ],
            max_tokens=500,
            temperature=0.0,
        )

        is_valid = "PASS" in response.content.upper()
        issues: list[str] = []
        if not is_valid:
            # Extract issues from the response
            for line in response.content.split("\n"):
                line = line.strip()
                if line.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.")):
                    issues.append(line.lstrip("-*1234567890. "))

        return {"valid": is_valid, "issues": issues, "raw": response.content}

    # ------------------------------------------------------------------
    # Plan parsing
    # ------------------------------------------------------------------

    def _parse_plan(self, plan_text: str, parent_task: str) -> list[ColonyTask]:
        """Parse a plan text into ColonyTask objects.

        Supports multiple output formats:
        - Markdown-style with ### Subtask headers
        - Numbered lists with descriptions
        - JSON arrays (auto-detected)

        Args:
            plan_text: The plan text from the LLM.
            parent_task: The original task description.

        Returns:
            List of parsed subtasks.
        """
        # Try JSON parsing first
        subtasks = self._try_parse_json_plan(plan_text, parent_task)
        if subtasks:
            return subtasks

        # Fall back to markdown parsing
        subtasks = self._parse_markdown_plan(plan_text, parent_task)
        if subtasks:
            return subtasks

        # Fall back to line-by-line parsing
        subtasks = self._parse_line_plan(plan_text, parent_task)
        if subtasks:
            return subtasks

        # If all parsing fails, create a single task
        return [ColonyTask(
            title=parent_task,
            description=plan_text,
            priority=5,
            status="pending",
        )]

    def _try_parse_json_plan(self, plan_text: str, parent_task: str) -> list[ColonyTask]:
        """Try to parse a JSON array plan.

        Args:
            plan_text: The plan text that might contain JSON.
            parent_task: The original task description.

        Returns:
            List of parsed subtasks, or empty list if JSON parsing fails.
        """
        # Find JSON array in the text
        start = plan_text.find("[")
        end = plan_text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []

        try:
            items = json.loads(plan_text[start:end + 1])
            if not isinstance(items, list):
                return []

            subtasks: list[ColonyTask] = []
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    subtasks.append(ColonyTask(
                        title=item.get("title", item.get("name", f"Subtask {i + 1}")),
                        description=item.get("description", ""),
                        priority=item.get("priority", i + 1),
                        status="pending",
                        assigned_hand=item.get("agent") if item.get("agent") else None,
                    ))
                elif isinstance(item, str):
                    subtasks.append(ColonyTask(
                        title=item,
                        description="",
                        priority=i + 1,
                        status="pending",
                    ))
            return subtasks
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_markdown_plan(self, plan_text: str, parent_task: str) -> list[ColonyTask]:
        """Parse a markdown-style plan.

        Args:
            plan_text: The plan text with markdown formatting.
            parent_task: The original task description.

        Returns:
            List of parsed subtasks.
        """
        subtasks: list[ColonyTask] = []
        lines = plan_text.split("\n")
        current_task: Optional[dict[str, Any]] = None
        priority = 1

        for line in lines:
            line = line.strip()
            if line.startswith("### Subtask") or line.startswith("## Subtask"):
                # Save previous task
                if current_task:
                    subtasks.append(ColonyTask(
                        title=current_task.get("title", "Untitled"),
                        description=current_task.get("description", ""),
                        priority=current_task.get("priority", priority),
                        status="pending",
                        assigned_hand=current_task.get("assigned_hand"),
                    ))
                    priority += 1

                # Start new task
                title = line.split(":", 1)[1].strip() if ":" in line else line.lstrip("# ")
                current_task = {"title": title, "description": ""}

            elif current_task and line.startswith("- Description:"):
                current_task["description"] = line.split(":", 1)[1].strip()
            elif current_task and line.startswith("- Agent:"):
                current_task["assigned_hand"] = line.split(":", 1)[1].strip()
            elif current_task and line.startswith("- Priority:"):
                try:
                    current_task["priority"] = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            elif current_task and line.startswith("- Dependencies:"):
                deps = line.split(":", 1)[1].strip()
                if deps.lower() not in ("none", ""):
                    current_task["dependencies"] = [d.strip() for d in deps.split(",")]

        # Don't forget the last task
        if current_task:
            subtasks.append(ColonyTask(
                title=current_task.get("title", "Untitled"),
                description=current_task.get("description", ""),
                priority=current_task.get("priority", priority),
                status="pending",
                assigned_hand=current_task.get("assigned_hand"),
            ))

        return subtasks

    def _parse_line_plan(self, plan_text: str, parent_task: str) -> list[ColonyTask]:
        """Parse a simple line-by-line plan.

        Args:
            plan_text: The plan text with one subtask per line.
            parent_task: The original task description.

        Returns:
            List of parsed subtasks.
        """
        subtasks: list[ColonyTask] = []
        for i, line in enumerate(plan_text.split("\n")):
            line = line.strip()
            # Match numbered items like "1. Do something"
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                # Remove leading numbers/bullets
                cleaned = line.lstrip("0123456789.-* )")
                if cleaned:
                    subtasks.append(ColonyTask(
                        title=cleaned[:100],
                        description=cleaned,
                        priority=i + 1,
                        status="pending",
                    ))
        return subtasks

    # ------------------------------------------------------------------
    # Plan history
    # ------------------------------------------------------------------

    def get_plan_history(self) -> list[dict[str, Any]]:
        """Get the history of plans created by this agent.

        Returns:
            List of plan history entries.
        """
        return list(self._plan_history)

    def clear_plan_history(self) -> None:
        """Clear the plan history."""
        self._plan_history.clear()
