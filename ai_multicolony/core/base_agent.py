"""Merged BaseAgent for the AI MultiColony Ecosystem.

Combines the best patterns from:
- OpenHands: Agent ABC with state machine, event emission
- OpenManus: Pydantic-based agent with ToolCallAgent pattern
- AI-Manus: Protocol-based domain interfaces with BaseAgent ABC
- Nanobot: AgentLoop with bus integration, subagent spawning

This is a Pydantic BaseModel that provides:
- State machine (IDLE, RUNNING, PAUSED, ERROR, TERMINATED, WAITING, THINKING)
- Tool registration and invocation
- LLM provider integration
- Event bus emission
- Subagent spawning
- Memory/context management
- AgentOutput generation
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field, PrivateAttr

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.event_bus import EventBus
from ai_multicolony.core.llm_provider import LLMProvider, LLMResponse
from ai_multicolony.core.memory_manager import MemoryManager
from ai_multicolony.core.tool_registry import ToolRegistry
from ai_multicolony.exceptions import AgentError, AgentStateError, AgentTimeoutError
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentOutput, AgentRole, AgentState, AgentStatus, SubagentSpawn
from ai_multicolony.types.events import Action, ActionType, Event, EventType, Observation, ObservationType
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.types.tools import ToolCall, ToolResult

logger = get_logger(__name__)


class BaseAgent(BaseModel):
    """Base agent class for all agents in the ecosystem.

    Pydantic BaseModel (from OpenManus pattern) providing:
    - State machine (IDLE, RUNNING, PAUSED, ERROR, TERMINATED, WAITING, THINKING)
    - Tool registration and invocation
    - LLM provider integration
    - Event bus emission
    - Subagent spawning
    - Memory/context management
    """

    # Identity
    config: AgentConfig = Field(default_factory=AgentConfig)

    # State
    state: AgentState = Field(default=AgentState.IDLE)
    current_task: Optional[str] = None

    # Conversation
    messages: list[Message] = Field(default_factory=list)

    # Results tracking
    last_result: Optional[str] = None
    iteration_count: int = 0
    error_count: int = 0
    tokens_used: int = 0
    cost_incurred: float = 0.0

    # Timing
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    # Subagents
    subagent_ids: list[str] = Field(default_factory=list)

    # Internal (not serialized by Pydantic)
    _event_bus: Optional[EventBus] = PrivateAttr(default=None)
    _llm_provider: Optional[LLMProvider] = PrivateAttr(default=None)
    _tool_registry: Optional[ToolRegistry] = PrivateAttr(default=None)
    _memory_manager: Optional[MemoryManager] = PrivateAttr(default=None)

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.config.name == "unnamed-agent":
            self.config.name = f"{self.config.role.value}-agent"

    @property
    def agent_id(self) -> str:
        """Get the agent's unique ID."""
        return self.config.agent_id

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self.config.name

    @property
    def role(self) -> AgentRole:
        """Get the agent's role."""
        return self.config.role

    @property
    def capabilities(self) -> AgentCapabilities:
        """Get the agent's capabilities."""
        return self.config.capabilities

    # === Dependency Injection ===

    def set_event_bus(self, bus: EventBus) -> None:
        """Set the event bus for this agent."""
        self._event_bus = bus

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set the LLM provider for this agent."""
        self._llm_provider = provider

    def set_tool_registry(self, registry: ToolRegistry) -> None:
        """Set the tool registry for this agent."""
        self._tool_registry = registry

    def set_memory_manager(self, manager: MemoryManager) -> None:
        """Set the memory manager for this agent."""
        self._memory_manager = manager

    def _get_event_bus(self) -> EventBus:
        """Get event bus, creating a default if not set."""
        if self._event_bus is None:
            self._event_bus = EventBus.get_instance()
        return self._event_bus

    def _get_llm_provider(self) -> LLMProvider:
        """Get LLM provider, creating a default if not set."""
        if self._llm_provider is None:
            self._llm_provider = LLMProvider(default_model=self.config.model)
        return self._llm_provider

    def _get_tool_registry(self) -> ToolRegistry:
        """Get tool registry, creating a default if not set."""
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry.get_instance()
        return self._tool_registry

    def _get_memory_manager(self) -> MemoryManager:
        """Get memory manager, creating a default if not set."""
        if self._memory_manager is None:
            self._memory_manager = MemoryManager()
        return self._memory_manager

    # === State Machine ===

    # Valid state transitions
    VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
        AgentState.IDLE: {AgentState.RUNNING, AgentState.TERMINATED},
        AgentState.RUNNING: {AgentState.PAUSED, AgentState.ERROR, AgentState.WAITING, AgentState.THINKING, AgentState.TERMINATED, AgentState.IDLE},
        AgentState.PAUSED: {AgentState.RUNNING, AgentState.TERMINATED, AgentState.IDLE},
        AgentState.WAITING: {AgentState.RUNNING, AgentState.ERROR, AgentState.TERMINATED},
        AgentState.THINKING: {AgentState.RUNNING, AgentState.ERROR, AgentState.TERMINATED},
        AgentState.ERROR: {AgentState.RUNNING, AgentState.TERMINATED, AgentState.IDLE},
        AgentState.TERMINATED: set(),
    }

    def _transition_to(self, new_state: AgentState) -> None:
        """Transition to a new state with validation.

        Args:
            new_state: The target state.

        Raises:
            AgentStateError: If the transition is invalid.
        """
        allowed = self.VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise AgentStateError(
                f"Invalid state transition from {self.state.value} to {new_state.value}",
                agent_id=self.agent_id,
                current_state=self.state.value,
            )

        old_state = self.state
        self.state = new_state
        logger.info(
            "agent_state_transition",
            agent_id=self.agent_id,
            old_state=old_state.value,
            new_state=new_state.value,
        )

        # Emit state change event
        bus = self._get_event_bus()
        event = Event(
            event_type=EventType.LIFECYCLE,
            source=self.agent_id,
            data={"old_state": old_state.value, "new_state": new_state.value},
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(bus.publish_event(event))
        except RuntimeError:
            pass

    # === Core Agent Operations ===

    async def run(self, task: str) -> str:
        """Run the agent on a task.

        This is the main entry point for agent execution.

        Args:
            task: The task description.

        Returns:
            The final result string.

        Raises:
            AgentStateError: If the agent is in an invalid state.
            AgentTimeoutError: If the agent exceeds max iterations.
            AgentError: For other agent errors.
        """
        if self.state not in (AgentState.IDLE, AgentState.ERROR):
            raise AgentStateError(
                f"Cannot run agent in state {self.state.value}",
                agent_id=self.agent_id,
                current_state=self.state.value,
            )

        self.current_task = task
        self.started_at = time.time()
        self.iteration_count = 0
        self.error_count = 0

        # Add system prompt if configured
        if self.config.system_prompt and not any(m.role == MessageRole.SYSTEM for m in self.messages):
            self.messages.append(Message(role=MessageRole.SYSTEM, content=self.config.system_prompt))

        # Add task as user message
        self.messages.append(Message(role=MessageRole.USER, content=task))

        # Store task in memory
        memory = self._get_memory_manager()
        memory.add_entry(
            agent_id=self.agent_id,
            content=f"Task: {task}",
            memory_type=MemoryType.WORKING,
            importance=0.8,
            source="user",
        )

        try:
            self._transition_to(AgentState.RUNNING)
            result = await self._execute_loop()
            self._transition_to(AgentState.IDLE)
            self.last_result = result
            return result
        except AgentStateError:
            raise
        except AgentTimeoutError:
            self._transition_to(AgentState.ERROR)
            raise
        except Exception as e:
            self._transition_to(AgentState.ERROR)
            self.error_count += 1
            raise AgentError(str(e), agent_id=self.agent_id) from e
        finally:
            self.finished_at = time.time()
            self.current_task = None

    async def _execute_loop(self) -> str:
        """Execute the agent loop until completion or max iterations.

        Returns:
            The final result.
        """
        max_iter = self.config.max_iterations
        last_response = ""

        while self.iteration_count < max_iter:
            if self.state == AgentState.PAUSED:
                await asyncio.sleep(0.1)
                continue

            if self.state in (AgentState.TERMINATED, AgentState.ERROR):
                break

            self.iteration_count += 1

            try:
                # Get LLM response
                self._transition_to(AgentState.THINKING)
                response = await self._call_llm()
                self._transition_to(AgentState.RUNNING)

                # Process tool calls if any
                if response.tool_calls:
                    last_response = await self._process_tool_calls(response)
                else:
                    last_response = response.content
                    if self._is_done(response.content):
                        break

                # Check token budget
                self.tokens_used += response.usage.total_tokens
                self.cost_incurred += response.cost

            except AgentStateError:
                raise
            except AgentTimeoutError:
                raise
            except Exception as e:
                self.error_count += 1
                logger.error("agent_loop_error", agent_id=self.agent_id, error=str(e))
                if self.error_count >= 3:
                    return f"Agent failed after {self.error_count} errors: {e}"

        if self.iteration_count >= max_iter:
            raise AgentTimeoutError(
                f"Agent exceeded max iterations ({max_iter})",
                agent_id=self.agent_id,
                timeout=max_iter,
            )

        return last_response

    async def _call_llm(self) -> LLMResponse:
        """Call the LLM with current conversation.

        Returns:
            LLM response.
        """
        provider = self._get_llm_provider()
        registry = self._get_tool_registry()

        # Build message list for LLM
        llm_messages = [m.to_dict() for m in self.messages]

        # Get tool schemas
        tools = None
        if self.config.tools:
            tools = registry.get_openai_schemas(self.config.tools)

        response: LLMResponse = await provider.chat(
            messages=llm_messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=tools if tools else None,
        )

        # Add assistant response to messages
        self.messages.append(Message(
            role=MessageRole.ASSISTANT,
            content=response.content,
            tool_calls=response.tool_calls if response.tool_calls else None,
        ))

        # Emit action event
        bus = self._get_event_bus()
        action = Action(
            action_type=ActionType.THINK,
            agent_id=self.agent_id,
            thought=response.content[:200],
        )
        await bus.publish_action(action)

        return response

    async def _process_tool_calls(self, response: LLMResponse) -> str:
        """Process tool calls from an LLM response.

        Args:
            response: The LLM response with tool calls.

        Returns:
            Summary of tool execution results.
        """
        registry = self._get_tool_registry()
        results: list[str] = []

        for tc in response.tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            arguments_str = func.get("arguments", "{}")

            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}

            # Execute the tool
            tool_result: ToolResult = await registry.execute(
                tool_name=tool_name,
                arguments=arguments,
                agent_id=self.agent_id,
            )

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
                importance=0.3,
                source="tool",
            )

            if tool_result.success:
                results.append(f"[{tool_name}] Success: {tool_result.output[:200]}")
            else:
                results.append(f"[{tool_name}] Error: {tool_result.error}")

        return "\n".join(results)

    def _is_done(self, response: str) -> bool:
        """Check if the agent's response indicates completion.

        Args:
            response: The LLM response content.

        Returns:
            True if the agent considers itself done.
        """
        done_markers = [
            "task complete",
            "task completed",
            "i'm done",
            "finished",
            "mission accomplished",
            "all done",
        ]
        return any(marker in response.lower() for marker in done_markers)

    # === Subagent Spawning ===

    async def spawn_subagent(self, spawn: SubagentSpawn) -> str:
        """Spawn a subagent to handle a subtask.

        Args:
            spawn: The subagent spawn request.

        Returns:
            The subagent's result.
        """
        from ai_multicolony.agents.registry import AgentRegistry

        registry = AgentRegistry()
        agent_cls = registry.get(spawn.role.value)
        sub_agent = agent_cls(
            config=AgentConfig(
                role=spawn.role,
                model=spawn.model or self.config.model,
                tools=spawn.tools,
                timeout=spawn.timeout or self.config.timeout,
                parent_id=self.agent_id,
                colony_id=self.config.colony_id,
                metadata=spawn.metadata,
            )
        )

        # Inherit infrastructure
        sub_agent.set_event_bus(self._get_event_bus())
        sub_agent.set_llm_provider(self._get_llm_provider())
        sub_agent.set_tool_registry(self._get_tool_registry())
        sub_agent.set_memory_manager(self._get_memory_manager())

        self.subagent_ids.append(sub_agent.agent_id)
        logger.info("spawned_subagent", parent=self.agent_id, child=sub_agent.agent_id, role=spawn.role.value)

        result = await sub_agent.run(spawn.task)
        return result

    # === Control ===

    async def pause(self) -> None:
        """Pause the agent."""
        if self.state == AgentState.RUNNING:
            self._transition_to(AgentState.PAUSED)

    async def resume(self) -> None:
        """Resume the agent from pause."""
        if self.state == AgentState.PAUSED:
            self._transition_to(AgentState.RUNNING)

    async def terminate(self) -> None:
        """Terminate the agent."""
        if self.state != AgentState.TERMINATED:
            self._transition_to(AgentState.TERMINATED)

    def get_status(self) -> AgentStatus:
        """Get the current agent status."""
        return AgentStatus(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            state=self.state,
            current_task=self.current_task,
            iterations=self.iteration_count,
            tokens_used=self.tokens_used,
            cost_incurred=self.cost_incurred,
            error_count=self.error_count,
            last_action=self.last_result,
            started_at=self.started_at,
            finished_at=self.finished_at,
            subagents=self.subagent_ids,
        )

    def get_output(self) -> AgentOutput:
        """Get the structured output from the last agent run.

        Returns:
            AgentOutput with execution details.
        """
        duration = 0.0
        if self.started_at and self.finished_at:
            duration = self.finished_at - self.started_at

        return AgentOutput(
            agent_id=self.agent_id,
            task=self.current_task or "",
            result=self.last_result or "",
            success=self.state != AgentState.ERROR,
            error=None if self.state != AgentState.ERROR else "Agent ended in ERROR state",
            iterations=self.iteration_count,
            tokens_used=self.tokens_used,
            cost_incurred=self.cost_incurred,
            duration=duration,
            tool_calls=sum(1 for m in self.messages if m.role == MessageRole.TOOL),
            subagents_spawned=len(self.subagent_ids),
            started_at=self.started_at,
            finished_at=self.finished_at,
        )

    def reset(self) -> None:
        """Reset the agent to initial state."""
        self.state = AgentState.IDLE
        self.messages = []
        self.current_task = None
        self.last_result = None
        self.iteration_count = 0
        self.error_count = 0
        self.tokens_used = 0
        self.cost_incurred = 0.0
        self.started_at = None
        self.finished_at = None
        self.subagent_ids = []

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent type. Override in subclasses."""
        return self.config.system_prompt or "You are a helpful AI assistant."

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id[:8]}, name={self.name}, state={self.state.value})"
