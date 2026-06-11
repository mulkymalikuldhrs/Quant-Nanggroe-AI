"""Agent processing loop for the AI MultiColony Ecosystem.

From Nanobot AgentLoop pattern with bus integration and
OpenManus tool call processing. Provides a reusable loop engine
that can drive any agent through its think-act-observe cycle.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.event_bus import EventBus
from ai_multicolony.core.llm_provider import LLMProvider, LLMResponse
from ai_multicolony.core.memory_manager import MemoryManager
from ai_multicolony.core.tool_registry import ToolRegistry
from ai_multicolony.exceptions import AgentError, AgentTimeoutError
from ai_multicolony.types.events import Action, ActionType, Observation, ObservationType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.types.tools import ToolResult

logger = get_logger(__name__)


class LoopState(str, Enum):
    """State of the agent loop."""

    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_TOOL = "waiting_tool"
    WAITING_LLM = "waiting_llm"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class LoopConfig:
    """Configuration for the agent loop."""

    max_iterations: int = 10
    timeout: float = 300.0
    tool_timeout: float = 60.0
    llm_timeout: float = 120.0
    retry_on_error: bool = True
    max_retries: int = 3
    pause_between_iterations: float = 0.1
    condenser_type: Optional[str] = None


@dataclass
class LoopResult:
    """Result from an agent loop execution."""

    success: bool = True
    final_response: str = ""
    iterations: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    tool_calls_made: int = 0
    errors: list[str] = field(default_factory=list)
    duration: float = 0.0


class AgentLoop:
    """Agent processing loop with bus integration.

    From Nanobot AgentLoop pattern with:
    - Structured iteration with state tracking
    - Tool call processing
    - Event emission to bus
    - Memory condensation between iterations
    - Configurable timeouts and retries
    """

    def __init__(
        self,
        agent_id: str,
        config: Optional[LoopConfig] = None,
        event_bus: Optional[EventBus] = None,
        llm_provider: Optional[LLMProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory_manager: Optional[MemoryManager] = None,
    ) -> None:
        self.agent_id = agent_id
        self.config = config or LoopConfig()
        self._event_bus = event_bus or EventBus.get_instance()
        self._llm_provider = llm_provider
        self._tool_registry = tool_registry or ToolRegistry.get_instance()
        self._memory_manager = memory_manager or MemoryManager()
        self._state = LoopState.IDLE
        self._messages: list[Message] = []
        self._iteration = 0
        self._tool_calls_made = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._errors: list[str] = []
        self._hooks: dict[str, list[Callable]] = {
            "pre_iteration": [],
            "post_iteration": [],
            "on_tool_call": [],
            "on_error": [],
        }

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def iteration(self) -> int:
        return self._iteration

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set the LLM provider."""
        self._llm_provider = provider

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self._messages.append(message)

    def set_messages(self, messages: list[Message]) -> None:
        """Set the conversation messages."""
        self._messages = list(messages)

    def add_hook(self, hook_name: str, callback: Callable) -> None:
        """Add a lifecycle hook callback.

        Args:
            hook_name: One of 'pre_iteration', 'post_iteration', 'on_tool_call', 'on_error'.
            callback: Callable to invoke at the hook point.
        """
        if hook_name in self._hooks:
            self._hooks[hook_name].append(callback)

    async def _run_hooks(self, hook_name: str, **kwargs: Any) -> None:
        """Run all callbacks for a given hook.

        Args:
            hook_name: The hook to run.
            **kwargs: Arguments passed to callbacks.
        """
        for callback in self._hooks.get(hook_name, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(**kwargs)
                else:
                    callback(**kwargs)
            except Exception as e:
                logger.warning("hook_error", hook=hook_name, error=str(e))

    async def run(self, task: str, system_prompt: Optional[str] = None) -> LoopResult:
        """Run the agent loop.

        Args:
            task: The task to execute.
            system_prompt: Optional system prompt.

        Returns:
            LoopResult with execution details.
        """
        start_time = time.time()
        self._state = LoopState.PROCESSING
        self._iteration = 0
        self._tool_calls_made = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._errors = []

        # Set up initial messages
        self._messages = []
        if system_prompt:
            self._messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))
        self._messages.append(Message(role=MessageRole.USER, content=task))

        final_response = ""

        try:
            while self._iteration < self.config.max_iterations:
                # Check timeout
                if time.time() - start_time > self.config.timeout:
                    raise AgentTimeoutError(
                        f"Loop timeout after {time.time() - start_time:.1f}s",
                        agent_id=self.agent_id,
                        timeout=self.config.timeout,
                    )

                self._iteration += 1

                # Pre-iteration hook
                await self._run_hooks("pre_iteration", iteration=self._iteration, messages=self._messages)

                self._state = LoopState.WAITING_LLM

                # Get LLM response
                response = await self._get_llm_response()

                self._total_tokens += response.usage.total_tokens
                self._total_cost += response.cost

                # Add assistant message
                self._messages.append(Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls if response.tool_calls else None,
                ))

                # Process tool calls or finish
                if response.tool_calls:
                    self._state = LoopState.WAITING_TOOL
                    tool_result = await self._process_tool_calls(response)
                    final_response = tool_result
                    self._tool_calls_made += len(response.tool_calls)
                else:
                    final_response = response.content
                    self._state = LoopState.COMPLETED

                    # Post-iteration hook
                    await self._run_hooks("post_iteration", iteration=self._iteration, response=final_response)
                    break

                # Post-iteration hook
                await self._run_hooks("post_iteration", iteration=self._iteration, response=final_response)

                # Pause between iterations
                if self.config.pause_between_iterations > 0:
                    await asyncio.sleep(self.config.pause_between_iterations)

            # Check if we hit max iterations
            if self._state != LoopState.COMPLETED:
                self._state = LoopState.COMPLETED

        except AgentTimeoutError:
            self._state = LoopState.ERROR
            self._errors.append("Timeout exceeded")
            raise
        except Exception as e:
            self._state = LoopState.ERROR
            self._errors.append(str(e))
            await self._run_hooks("on_error", error=e)
            raise AgentError(str(e), agent_id=self.agent_id) from e

        duration = time.time() - start_time
        return LoopResult(
            success=self._state == LoopState.COMPLETED,
            final_response=final_response,
            iterations=self._iteration,
            total_tokens=self._total_tokens,
            total_cost=self._total_cost,
            tool_calls_made=self._tool_calls_made,
            errors=self._errors,
            duration=duration,
        )

    async def _get_llm_response(self) -> LLMResponse:
        """Get a response from the LLM."""
        if not self._llm_provider:
            raise AgentError("LLM provider not set", agent_id=self.agent_id)

        llm_messages = [m.to_dict() for m in self._messages]

        # Condense messages if needed
        try:
            if len(self._messages) > 20:
                condensed = self._messages[:2] + self._messages[-10:]
                llm_messages = [m.to_dict() for m in condensed]
        except Exception:
            logger.exception("unhandled_error")
            pass

        # Get available tools
        tools = self._tool_registry.get_openai_schemas()

        response = await self._llm_provider.chat(
            messages=llm_messages,
            tools=tools if tools else None,
        )

        # Emit event
        action = Action(
            action_type=ActionType.THINK,
            agent_id=self.agent_id,
            thought=response.content[:200],
        )
        await self._event_bus.publish_action(action)

        return response

    async def _process_tool_calls(self, response: LLMResponse) -> str:
        """Process tool calls from LLM response."""
        results: list[str] = []

        for tc in response.tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            arguments_str = func.get("arguments", "{}")

            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}

            try:
                # on_tool_call hook
                await self._run_hooks("on_tool_call", tool_name=tool_name, arguments=arguments)

                tool_result: ToolResult = await self._tool_registry.execute(
                    tool_name=tool_name,
                    arguments=arguments,
                    agent_id=self.agent_id,
                )

                # Add tool result to messages
                self._messages.append(Message(
                    role=MessageRole.TOOL,
                    content=tool_result.output if tool_result.success else f"Error: {tool_result.error}",
                    name=tool_name,
                    tool_call_id=tc.get("id", ""),
                ))

                # Emit observation
                obs = Observation(
                    observation_type=ObservationType.SUCCESS if tool_result.success else ObservationType.ERROR,
                    agent_id=self.agent_id,
                    action_id=tc.get("id", ""),
                    content=tool_result.output[:500] if tool_result.success else (tool_result.error or "Unknown error"),
                    success=tool_result.success,
                    error=tool_result.error if not tool_result.success else None,
                )
                await self._event_bus.publish_observation(obs)

                results.append(f"[{tool_name}] {'Success' if tool_result.success else 'Error'}: "
                             f"{tool_result.output[:100] if tool_result.success else tool_result.error}")

            except Exception as e:
                self._errors.append(f"Tool '{tool_name}' failed: {e}")
                self._messages.append(Message(
                    role=MessageRole.TOOL,
                    content=f"Error executing tool: {e}",
                    name=tool_name,
                    tool_call_id=tc.get("id", ""),
                ))
                await self._run_hooks("on_error", error=e)

        return "\n".join(results)

    def pause(self) -> None:
        """Pause the loop."""
        self._state = LoopState.PAUSED

    def resume(self) -> None:
        """Resume the loop."""
        self._state = LoopState.PROCESSING

    def reset(self) -> None:
        """Reset the loop state."""
        self._state = LoopState.IDLE
        self._messages = []
        self._iteration = 0
        self._tool_calls_made = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._errors = []

    def get_stats(self) -> dict[str, Any]:
        """Get loop statistics."""
        return {
            "state": self._state.value,
            "iteration": self._iteration,
            "max_iterations": self.config.max_iterations,
            "tool_calls_made": self._tool_calls_made,
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost,
            "message_count": len(self._messages),
            "error_count": len(self._errors),
        }
