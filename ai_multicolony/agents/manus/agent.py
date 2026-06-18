"""Manus agent - ToolCallAgent pattern from OpenManus.

The most versatile agent type, capable of using any registered tool
to accomplish tasks through iterative tool calling with planning,
reflection, and error recovery.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from pydantic import Field

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from ai_multicolony.types.events import Action, ActionType, Observation, ObservationType
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.agents.manus.prompts import (
    MANUS_SYSTEM_PROMPT,
    MANUS_ERROR_RECOVERY_PROMPT,
    MANUS_PLANNING_PROMPT,
    MANUS_REFLECTION_PROMPT,
)

logger = get_logger(__name__)


class ToolCallAgent(BaseAgent):
    """Agent that can invoke tools, manage conversation, and handle tool calls from LLM.

    Extends BaseAgent with the OpenManus ToolCallAgent pattern:
    - Structured tool call handling with validation
    - Post-tool-call reflection phase
    - Error recovery with retry logic
    - Tool call result summarization
    - State-specific behavior (PAUSED blocks execution, ERROR triggers recovery)
    """

    # Track consecutive tool failures for recovery decisions
    _consecutive_tool_failures: int = 0
    _max_consecutive_failures: int = 3
    _total_tool_calls: int = 0
    _successful_tool_calls: int = 0

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.MANUS,
                name="toolcall-agent",
                description="Agent with structured tool calling, reflection, and error recovery",
                tools=["shell", "file", "search", "code", "browser", "memory"],
                system_prompt=MANUS_SYSTEM_PROMPT,
                capabilities=AgentCapabilities(
                    code_generation=True,
                    code_execution=True,
                    web_browsing=True,
                    file_operations=True,
                    shell_execution=True,
                    web_search=True,
                    memory_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = MANUS_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["shell", "file", "search", "code", "browser", "memory"]

        super().__init__(config=config, **kwargs)
        self._consecutive_tool_failures = 0
        self._total_tool_calls = 0
        self._successful_tool_calls = 0

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names this agent requires.

        Returns:
            Minimal set of tools needed for ToolCallAgent to function.
        """
        return ["shell", "file", "search", "memory"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent type."""
        return self.config.system_prompt or MANUS_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "toolcall_agent_running",
            agent_id=self.agent_id,
            iteration=self.iteration_count,
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state — trigger recovery."""
        logger.warning(
            "toolcall_agent_error",
            agent_id=self.agent_id,
            consecutive_failures=self._consecutive_tool_failures,
        )
        # Store error context in memory for future recovery
        memory = self._get_memory_manager()
        memory.add_entry(
            agent_id=self.agent_id,
            content=f"Error state entered after {self._consecutive_tool_failures} consecutive tool failures",
            memory_type=MemoryType.WORKING,
            importance=0.9,
            source="agent",
        )

    def _on_enter_paused(self) -> None:
        """Hook called when entering PAUSED state."""
        logger.info("toolcall_agent_paused", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # Execution loop override
    # ------------------------------------------------------------------

    async def _execute_loop(self) -> str:
        """Execute the agent loop with planning, reflection, and error recovery.

        Extends the base loop with:
        - Initial planning phase before first action
        - Post-tool-call reflection
        - Error recovery with retries
        - State-specific behavior (PAUSED waits, ERROR attempts recovery)
        """
        max_iter = self.config.max_iterations
        last_response = ""
        planned = False

        while self.iteration_count < max_iter:
            # ---- State-specific behavior ----
            if self.state == AgentState.PAUSED:
                self._on_enter_paused()
                await asyncio.sleep(0.1)
                continue

            if self.state == AgentState.TERMINATED:
                break

            if self.state == AgentState.ERROR:
                # Attempt recovery: if we haven't exceeded failures, try to continue
                if self._consecutive_tool_failures < self._max_consecutive_failures:
                    logger.info("attempting_error_recovery", agent_id=self.agent_id)
                    try:
                        self._transition_to(AgentState.RUNNING)
                    except Exception:
                        break
                else:
                    return f"Agent halted: {self._consecutive_tool_failures} consecutive tool failures"

            self.iteration_count += 1

            # ---- Planning phase (first iteration) ----
            if not planned:
                self._on_enter_running()
                planned = True
                # Inject planning prompt into conversation
                self.messages.append(Message(
                    role=MessageRole.ASSISTANT,
                    content=MANUS_PLANNING_PROMPT,
                ))

            try:
                # Get LLM response
                self._transition_to(AgentState.THINKING)
                response = await self._call_llm()
                self._transition_to(AgentState.RUNNING)
                self._on_enter_running()

                # Process tool calls if any
                if response.tool_calls:
                    last_response = await self._process_tool_calls_with_recovery(response)
                else:
                    last_response = response.content
                    if self._is_done(response.content):
                        break

                # Update token tracking
                self.tokens_used += response.usage.total_tokens
                self.cost_incurred += response.cost

            except Exception as e:
                self.error_count += 1
                self._consecutive_tool_failures += 1
                self._on_enter_error()
                if self.error_count >= 5:
                    return f"Agent failed after {self.error_count} errors: {e}"
                last_response = f"Error in iteration {self.iteration_count}: {e}"

        if self.iteration_count >= max_iter:
            return last_response or "Max iterations reached"

        return last_response

    # ------------------------------------------------------------------
    # Tool call processing with recovery
    # ------------------------------------------------------------------

    async def _process_tool_calls_with_recovery(self, response: Any) -> str:
        """Process tool calls with error recovery and reflection.

        Extends the base _process_tool_calls with:
        - Consecutive failure tracking
        - Error recovery prompt injection on failures
        - Post-tool-call reflection

        Args:
            response: The LLM response containing tool calls.

        Returns:
            Summary of tool execution results.
        """
        registry = self._get_tool_registry()
        results: list[str] = []
        had_failure = False

        for tc in response.tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            arguments_str = func.get("arguments", "{}")

            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}

            self._total_tool_calls += 1

            # Execute the tool
            tool_result = await registry.execute(
                tool_name=tool_name,
                arguments=arguments,
                agent_id=self.agent_id,
            )

            # Track success/failure
            if tool_result.success:
                self._successful_tool_calls += 1
                self._consecutive_tool_failures = 0  # Reset on success
                results.append(f"[{tool_name}] Success: {tool_result.output[:200]}")
            else:
                had_failure = True
                self._consecutive_tool_failures += 1
                results.append(f"[{tool_name}] Error: {tool_result.error}")

            # Add tool result to messages
            self.messages.append(Message(
                role=MessageRole.TOOL,
                content=tool_result.output if tool_result.success else f"Error: {tool_result.error}",
                name=tool_name,
                tool_call_id=tc.get("id", ""),
            ))

            # Emit observation event
            bus = self._get_event_bus()
            obs = Observation(
                observation_type=ObservationType.SUCCESS if tool_result.success else ObservationType.ERROR,
                agent_id=self.agent_id,
                action_id=tc.get("id", ""),
                content=tool_result.output[:500] if tool_result.success else (tool_result.error or "Unknown error"),
                success=tool_result.success,
                error=tool_result.error if not tool_result.success else None,
            )
            await bus.publish_observation(obs)

            # Store in memory
            memory = self._get_memory_manager()
            memory.add_entry(
                agent_id=self.agent_id,
                content=f"Tool {tool_name}: {tool_result.output[:200]}",
                memory_type=MemoryType.TOOL_HISTORY,
                importance=0.3 if tool_result.success else 0.7,
                source="tool",
            )

        # Inject reflection prompt after tool results
        self.messages.append(Message(
            role=MessageRole.ASSISTANT,
            content=MANUS_REFLECTION_PROMPT,
        ))

        # Inject error recovery prompt if there were failures
        if had_failure and self._consecutive_tool_failures > 1:
            self.messages.append(Message(
                role=MessageRole.USER,
                content=MANUS_ERROR_RECOVERY_PROMPT,
            ))

        return "\n".join(results)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_tool_stats(self) -> dict[str, Any]:
        """Get tool call statistics.

        Returns:
            Dictionary with tool call metrics.
        """
        return {
            "total_tool_calls": self._total_tool_calls,
            "successful_tool_calls": self._successful_tool_calls,
            "failed_tool_calls": self._total_tool_calls - self._successful_tool_calls,
            "consecutive_failures": self._consecutive_tool_failures,
            "success_rate": (
                self._successful_tool_calls / self._total_tool_calls
                if self._total_tool_calls > 0
                else 0.0
            ),
        }


class ManusAgent(ToolCallAgent):
    """Manus agent following the OpenManus ToolCallAgent pattern.

    This is the primary general-purpose agent that can use any tool
    to accomplish tasks through iterative tool calling and reflection.
    Inherits all ToolCallAgent capabilities with Manus-specific defaults.
    """

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.MANUS,
                name="manus-agent",
                description="Versatile agent using ToolCallAgent pattern with any registered tools",
                tools=["shell", "file", "search", "code", "browser", "memory"],
                system_prompt=MANUS_SYSTEM_PROMPT,
                capabilities=AgentCapabilities(
                    code_generation=True,
                    code_execution=True,
                    web_browsing=True,
                    file_operations=True,
                    shell_execution=True,
                    web_search=True,
                    memory_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = MANUS_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["shell", "file", "search", "code", "browser", "memory"]

        super().__init__(config=config, **kwargs)

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names ManusAgent requires.

        Returns:
            Tools needed for ManusAgent's general-purpose operation.
        """
        return ["shell", "file", "search", "code", "browser", "memory"]
