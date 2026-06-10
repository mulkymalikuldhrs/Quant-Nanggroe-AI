"""
Agent Execution Loop - Core agent run loop extracted from suna AgentPress.

Adapted from suna's AgentRunner and ThreadManager for Quant-Nanggroe-AI.
Provides the main execution loop that:
1. Initializes the agent with tools, memory, and MCP connections
2. Runs iterative LLM calls with tool execution
3. Handles streaming responses, auto-continuation, and cancellation
4. Manages context window compression and prompt caching
"""

import asyncio
import json
import time
from typing import Optional, Dict, List, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import logging

from quant_nanggroe_ai.agents.agentpress.tool_registry import ToolRegistry
from quant_nanggroe_ai.agents.agentpress.tool import Tool, ToolResult, SchemaType
from quant_nanggroe_ai.agents.agentpress.error_processor import ErrorProcessor

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Status of an agent run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class TerminationReason(str, Enum):
    """Reason the agent loop terminated."""
    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    CANCELLED = "cancelled"
    ERROR = "error"
    CREDIT_EXCEEDED = "credit_exceeded"
    AGENT_TERMINATED = "agent_terminated"


@dataclass
class AgentConfig:
    """Configuration for an agent run.

    Attributes:
        thread_id: Unique identifier for this conversation thread
        model_name: LLM model identifier (e.g., 'gpt-4', 'claude-3-opus')
        system_prompt: System prompt dict for the LLM
        max_iterations: Maximum number of agent loop iterations
        temperature: LLM sampling temperature
        max_tokens: Maximum tokens for LLM response
        tool_choice: Tool selection mode ('auto', 'required', 'none')
        native_max_auto_continues: Max auto-continues for native tool calling
        project_id: Project identifier for sandbox/context isolation
        account_id: Account identifier for billing/access control
        agent_config: Agent-specific configuration dict
        xml_tool_calling: Whether to use XML tool calling format
        native_tool_calling: Whether to use native (OpenAI-style) tool calling
    """
    thread_id: str = ""
    model_name: str = "gpt-4"
    system_prompt: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 50
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    tool_choice: str = "auto"
    native_max_auto_continues: int = 25
    project_id: Optional[str] = None
    account_id: Optional[str] = None
    agent_config: Optional[Dict[str, Any]] = None
    xml_tool_calling: bool = False
    native_tool_calling: bool = True


@dataclass
class LoopStats:
    """Statistics from an agent loop execution.

    Attributes:
        total_iterations: Number of loop iterations completed
        total_llm_calls: Number of LLM API calls made
        total_tool_calls: Number of tool executions performed
        total_tokens_used: Total tokens consumed
        total_execution_time_ms: Total wall-clock time in ms
        termination_reason: Why the loop terminated
    """
    total_iterations: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_tokens_used: int = 0
    total_execution_time_ms: float = 0.0
    termination_reason: Optional[TerminationReason] = None


class AgentLoop:
    """Main agent execution loop adapted from suna AgentPress.

    Orchestrates the iterative process of:
    1. Building prompts with tool schemas and memory context
    2. Calling the LLM
    3. Parsing tool calls from the response
    4. Executing tools and feeding results back
    5. Continuing until completion or termination condition

    Adapted from suna's AgentRunner + ThreadManager for the
    Quant-Nanggroe-AI trading platform.

    Usage:
        loop = AgentLoop(config=AgentConfig(model_name="gpt-4"))
        loop.tool_registry.register_tool(MarketDataTool)
        async for event in loop.run():
            handle_event(event)
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.tool_registry = ToolRegistry()
        self.status = AgentStatus.PENDING
        self.stats = LoopStats()
        self._cancellation_event: Optional[asyncio.Event] = None
        self._memory_context: Optional[Dict[str, Any]] = None
        self._messages: List[Dict[str, Any]] = []
        self._turn_number = 0

    def add_tool(self, tool_class: type, function_names: Optional[List[str]] = None, **kwargs):
        """Register a tool with the agent.

        Args:
            tool_class: Tool class to register
            function_names: Optional specific function names to enable
            **kwargs: Arguments to pass to tool constructor
        """
        self.tool_registry.register_tool(tool_class, function_names, **kwargs)

    def set_memory_context(self, context: Optional[Dict[str, Any]]):
        """Set memory context for prompt injection.

        Args:
            context: Memory context dict (typically from MemoryStore.get_context_for_prompt)
        """
        self._memory_context = context

    def set_messages(self, messages: List[Dict[str, Any]]):
        """Set the conversation message history.

        Args:
            messages: List of message dicts in LLM format
        """
        self._messages = list(messages)

    async def run(
        self,
        cancellation_event: Optional[asyncio.Event] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the agent loop.

        Yields event dicts with type field:
        - {"type": "assistant", "content": ...} — LLM text response
        - {"type": "tool_call", "name": ..., "args": ...} — Tool being called
        - {"type": "tool_result", "name": ..., "result": ...} — Tool execution result
        - {"type": "status", "status": "running|completed|stopped|error", ...} — Status updates
        - {"type": "usage", "prompt_tokens": ..., "completion_tokens": ...} — Token usage

        Args:
            cancellation_event: Optional event to signal loop cancellation

        Yields:
            Event dicts describing loop progress
        """
        self._cancellation_event = cancellation_event
        self.status = AgentStatus.RUNNING
        run_start = time.time()

        try:
            # Build system prompt
            system_message = self.config.system_prompt or self._build_default_system_prompt()

            yield {"type": "status", "status": "running", "message": "Agent loop started"}

            iteration_count = 0
            continue_execution = True

            while continue_execution and iteration_count < self.config.max_iterations:
                self._turn_number += 1
                iteration_count += 1
                self.stats.total_iterations = iteration_count

                # Check cancellation
                if cancellation_event and cancellation_event.is_set():
                    self.stats.termination_reason = TerminationReason.CANCELLED
                    yield {
                        "type": "status",
                        "status": "stopped",
                        "message": "Agent execution cancelled"
                    }
                    break

                # Prepare messages for LLM call
                prepared_messages = self._prepare_messages(system_message)

                # Get tool schemas
                tool_schemas = None
                if self.config.native_tool_calling:
                    tool_schemas = self.tool_registry.get_openapi_schemas()

                # Make LLM call
                try:
                    llm_response = await self._call_llm(
                        prepared_messages,
                        tool_schemas=tool_schemas,
                    )
                    self.stats.total_llm_calls += 1
                except Exception as e:
                    processed = ErrorProcessor.process_system_error(
                        e, context={"thread_id": self.config.thread_id}
                    )
                    self.stats.termination_reason = TerminationReason.ERROR
                    yield {
                        "type": "status",
                        "status": "error",
                        "message": str(e),
                    }
                    break

                # Process response
                if isinstance(llm_response, dict):
                    if llm_response.get("status") == "error":
                        self.stats.termination_reason = TerminationReason.ERROR
                        yield llm_response
                        break

                    # Check for tool calls
                    tool_calls = llm_response.get("tool_calls", [])
                    content = llm_response.get("content", "")

                    # Track usage
                    usage = llm_response.get("usage", {})
                    if usage:
                        self.stats.total_tokens_used += usage.get("total_tokens", 0)
                        yield {
                            "type": "usage",
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                        }

                    # Yield assistant message
                    if content:
                        yield {"type": "assistant", "content": content}

                    # Process tool calls
                    if tool_calls:
                        self._messages.append(llm_response)

                        for tool_call in tool_calls:
                            func_data = tool_call.get("function", {})
                            tool_name = func_data.get("name", "")
                            tool_args_str = func_data.get("arguments", "{}")

                            try:
                                tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                            except json.JSONDecodeError:
                                tool_args = {}

                            yield {
                                "type": "tool_call",
                                "name": tool_name,
                                "args": tool_args,
                            }

                            # Execute tool
                            result = await self._execute_tool(tool_name, tool_args)
                            self.stats.total_tool_calls += 1

                            yield {
                                "type": "tool_result",
                                "name": tool_name,
                                "result": result,
                            }

                            # Add tool result to messages
                            self._messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.get("id", ""),
                                "content": result.output if isinstance(result, ToolResult) else str(result),
                            })
                    else:
                        # No tool calls — agent finished responding
                        if content:
                            self._messages.append({"role": "assistant", "content": content})
                        continue_execution = False
                        self.stats.termination_reason = TerminationReason.COMPLETED
                else:
                    logger.warning(f"Unexpected LLM response type: {type(llm_response)}")
                    continue_execution = False

            # Set termination reason if loop ended by max iterations
            if iteration_count >= self.config.max_iterations and continue_execution:
                self.stats.termination_reason = TerminationReason.MAX_ITERATIONS
                yield {
                    "type": "status",
                    "status": "stopped",
                    "message": f"Max iterations ({self.config.max_iterations}) reached"
                }

        except Exception as e:
            self.stats.termination_reason = TerminationReason.ERROR
            yield {
                "type": "status",
                "status": "error",
                "message": str(e),
            }
        finally:
            self.status = AgentStatus.COMPLETED if self.stats.termination_reason == TerminationReason.COMPLETED else AgentStatus.STOPPED
            self.stats.total_execution_time_ms = (time.time() - run_start) * 1000

            yield {
                "type": "status",
                "status": self.status.value,
                "message": f"Agent loop ended: {self.stats.termination_reason.value if self.stats.termination_reason else 'unknown'}",
                "stats": {
                    "iterations": self.stats.total_iterations,
                    "llm_calls": self.stats.total_llm_calls,
                    "tool_calls": self.stats.total_tool_calls,
                    "tokens": self.stats.total_tokens_used,
                    "time_ms": self.stats.total_execution_time_ms,
                },
            }

    def _prepare_messages(self, system_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare messages for LLM call, injecting memory context.

        Args:
            system_message: System prompt message

        Returns:
            Complete list of messages ready for LLM API
        """
        messages = []
        if self._memory_context:
            messages.append(self._memory_context)
        messages.extend(self._messages)
        return [system_message] + messages

    def _build_default_system_prompt(self) -> Dict[str, Any]:
        """Build a default system prompt for trading agents.

        Returns:
            System message dict
        """
        tool_names = self.tool_registry.get_tool_names()
        tool_list = ", ".join(tool_names) if tool_names else "none"

        content = (
            "You are a quantitative trading agent powered by Quant-Nanggroe-AI. "
            "Use your available tools to analyze markets, manage risk, and execute trades.\n\n"
            f"Available tools: {tool_list}\n\n"
            "Always consider risk management before executing any trade. "
            "Use the ask tool when you need user input, and the complete tool when done."
        )
        return {"role": "system", "content": content}

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Call the LLM API.

        Uses litellm for provider-agnostic API access, with a
        synchronous fallback for testing.

        Args:
            messages: Prepared message list
            tool_schemas: Optional tool schemas for function calling

        Returns:
            LLM response dict
        """
        try:
            import litellm

            kwargs = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "stream": False,
            }

            if self.config.max_tokens:
                kwargs["max_tokens"] = self.config.max_tokens

            if tool_schemas and self.config.native_tool_calling:
                kwargs["tools"] = tool_schemas
                kwargs["tool_choice"] = self.config.tool_choice

            response = await litellm.acompletion(**kwargs)

            message = response.choices[0].message
            result = {
                "role": "assistant",
                "content": message.content or "",
            }

            if hasattr(message, "tool_calls") and message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ]

            if hasattr(response, "usage") and response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return result

        except ImportError:
            logger.warning("litellm not installed; returning stub response")
            return {
                "role": "assistant",
                "content": "litellm is not installed. Install with: pip install litellm",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """Execute a registered tool by name.

        Args:
            tool_name: Name of the tool function to call
            args: Arguments to pass to the tool

        Returns:
            ToolResult from execution
        """
        tool_info = self.tool_registry.get_tool(tool_name)
        if not tool_info:
            return ToolResult(success=False, output=f"Tool '{tool_name}' not found in registry")

        instance = tool_info.get("instance")
        if not instance:
            return ToolResult(success=False, output=f"Tool '{tool_name}' has no instance")

        try:
            method = getattr(instance, tool_name, None)
            if not method:
                return ToolResult(success=False, output=f"Method '{tool_name}' not found on tool instance")

            result = method(**args) if args else method()

            # Handle async tools
            if asyncio.iscoroutine(result):
                result = await result

            if isinstance(result, ToolResult):
                return result

            return ToolResult(success=True, output=str(result))

        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return ToolResult(success=False, output=f"Tool execution error: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current loop statistics.

        Returns:
            Dict with loop statistics
        """
        return {
            "status": self.status.value,
            "turn_number": self._turn_number,
            "registered_tools": len(self.tool_registry.tools),
            "total_iterations": self.stats.total_iterations,
            "total_llm_calls": self.stats.total_llm_calls,
            "total_tool_calls": self.stats.total_tool_calls,
            "total_tokens_used": self.stats.total_tokens_used,
            "total_execution_time_ms": self.stats.total_execution_time_ms,
            "termination_reason": self.stats.termination_reason.value if self.stats.termination_reason else None,
        }
