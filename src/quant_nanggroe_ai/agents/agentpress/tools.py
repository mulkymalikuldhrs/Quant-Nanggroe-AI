"""
Tools Module - Unified tool management facade for AgentPress.

Adapted from suna's tool system for Quant-Nanggroe-AI.
Provides a high-level interface combining tool registration, discovery,
schema generation, and execution in a single convenient module.

This re-exports core classes from tool.py and tool_registry.py and adds:
- ToolDiscovery: Automatic tool discovery and registration
- ToolExecutor: Unified tool execution with error handling and timeout
- Trading-specific tool presets and helpers
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Type, Callable
import logging

from quant_nanggroe_ai.agents.agentpress.tool import (
    Tool,
    ToolResult,
    ToolSchema,
    ToolMetadata,
    MethodMetadata,
    SchemaType,
    openapi_schema,
    tool_metadata,
    method_metadata,
)
from quant_nanggroe_ai.agents.agentpress.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    def __init__(self, tool_name: str, message: str, original_error: Optional[Exception] = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Tool '{tool_name}' execution failed: {message}")


class ToolExecutor:
    """Unified tool execution with error handling, timeout, and retry.

    Adapted from suna's response_processor tool execution patterns for
    Quant-Nanggroe-AI. Provides a safe execution wrapper around the
    ToolRegistry with:
    - Configurable timeout per tool call
    - Automatic retry on transient failures
    - Comprehensive error reporting
    - Execution statistics tracking

    Usage:
        executor = ToolExecutor(registry)
        result = await executor.execute("get_price", {"symbol": "AAPL"})
    """

    def __init__(
        self,
        registry: ToolRegistry,
        default_timeout: float = 60.0,
        max_retries: int = 1,
        retry_delay: float = 1.0,
    ):
        self.registry = registry
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._execution_stats: Dict[str, Dict[str, Any]] = {}

    async def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """Execute a tool with timeout and error handling.

        Args:
            tool_name: Name of the tool function to call
            args: Arguments to pass to the tool
            timeout: Optional per-call timeout (overrides default)

        Returns:
            ToolResult with execution output
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()

        tool_info = self.registry.get_tool(tool_name)
        if not tool_info:
            return ToolResult(success=False, output=f"Tool '{tool_name}' not found")

        instance = tool_info.get("instance")
        if not instance:
            return ToolResult(success=False, output=f"Tool '{tool_name}' has no instance")

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                method = getattr(instance, tool_name, None)
                if not method:
                    return ToolResult(
                        success=False,
                        output=f"Method '{tool_name}' not found on tool instance"
                    )

                # Execute with timeout
                result = await asyncio.wait_for(
                    self._invoke(method, args),
                    timeout=timeout,
                )

                # Track stats
                exec_time = (time.time() - start_time) * 1000
                self._update_stats(tool_name, exec_time, success=True)

                return result

            except asyncio.TimeoutError:
                exec_time = (time.time() - start_time) * 1000
                self._update_stats(tool_name, exec_time, success=False, error="timeout")
                return ToolResult(
                    success=False,
                    output=f"Tool '{tool_name}' timed out after {timeout}s"
                )

            except Exception as e:
                last_error = e
                exec_time = (time.time() - start_time) * 1000
                self._update_stats(tool_name, exec_time, success=False, error=str(e))

                if attempt < self.max_retries:
                    logger.warning(
                        f"Tool '{tool_name}' failed (attempt {attempt + 1}), "
                        f"retrying in {self.retry_delay}s: {e}"
                    )
                    await asyncio.sleep(self.retry_delay)

        return ToolResult(
            success=False,
            output=f"Tool '{tool_name}' failed after {self.max_retries + 1} attempts: {last_error}"
        )

    async def _invoke(self, method: Callable, args: Dict[str, Any]) -> ToolResult:
        """Invoke a tool method, handling both sync and async.

        Args:
            method: Tool method to invoke
            args: Arguments dict

        Returns:
            ToolResult from execution
        """
        result = method(**args) if args else method()

        if asyncio.iscoroutine(result):
            result = await result

        if isinstance(result, ToolResult):
            return result

        return ToolResult(success=True, output=str(result))

    def _update_stats(
        self,
        tool_name: str,
        exec_time_ms: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """Update execution statistics for a tool."""
        if tool_name not in self._execution_stats:
            self._execution_stats[tool_name] = {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "total_time_ms": 0.0,
                "last_error": None,
            }

        stats = self._execution_stats[tool_name]
        stats["calls"] += 1
        stats["total_time_ms"] += exec_time_ms

        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            stats["last_error"] = error

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get execution statistics for all tools.

        Returns:
            Dict mapping tool names to their execution stats
        """
        return dict(self._execution_stats)


class ToolDiscovery:
    """Automatic tool discovery and registration.

    Adapted from suna's tool_discovery and tool_manager patterns.
    Scans for Tool subclasses and registers them with a ToolRegistry,
    supporting both explicit registration and auto-discovery.

    Usage:
        discovery = ToolDiscovery(registry)
        discovery.register_from_class(MarketDataTool)
        discovery.register_from_module(my_tools_module)
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._discovered_classes: Dict[str, Type[Tool]] = {}

    def register_from_class(
        self,
        tool_class: Type[Tool],
        function_names: Optional[List[str]] = None,
        enabled: bool = True,
        **kwargs,
    ) -> bool:
        """Register a single tool class.

        Args:
            tool_class: Tool class to register
            function_names: Optional specific function names to enable
            enabled: Whether the tool is enabled
            **kwargs: Arguments to pass to tool constructor

        Returns:
            True if registration succeeded
        """
        if not enabled:
            logger.debug(f"Skipping disabled tool: {tool_class.__name__}")
            return False

        try:
            self.registry.register_tool(tool_class, function_names, **kwargs)
            self._discovered_classes[tool_class.__name__] = tool_class
            logger.info(f"Registered tool: {tool_class.__name__}")
            return True
        except Exception as e:
            logger.error(f"Failed to register tool {tool_class.__name__}: {e}")
            return False

    def register_from_module(self, module, prefix: str = "") -> int:
        """Discover and register all Tool subclasses from a module.

        Args:
            module: Python module to scan for Tool subclasses
            prefix: Optional prefix for tool names

        Returns:
            Number of tools successfully registered
        """
        count = 0
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Tool)
                and attr is not Tool
            ):
                if self.register_from_class(attr):
                    count += 1

        logger.info(f"Discovered {count} tools from module {getattr(module, '__name__', 'unknown')}")
        return count

    def register_trading_tools(self, disabled_tools: Optional[List[str]] = None) -> int:
        """Register the standard trading platform tools.

        Args:
            disabled_tools: List of tool class names to skip

        Returns:
            Number of tools registered
        """
        disabled = set(disabled_tools or [])
        count = 0

        tool_classes = []
        try:
            from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool
            tool_classes.append(MarketDataTool)
        except ImportError:
            pass

        try:
            from quant_nanggroe_ai.agents.tools.technical import TechnicalTool
            tool_classes.append(TechnicalTool)
        except ImportError:
            pass

        try:
            from quant_nanggroe_ai.agents.tools.execution import ExecutionTool
            tool_classes.append(ExecutionTool)
        except ImportError:
            pass

        try:
            from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool
            tool_classes.append(SentimentTool)
        except ImportError:
            pass

        try:
            from quant_nanggroe_ai.agents.tools.backtest import BacktestTool
            tool_classes.append(BacktestTool)
        except ImportError:
            pass

        for cls in tool_classes:
            if cls.__name__ not in disabled:
                if self.register_from_class(cls):
                    count += 1

        logger.info(f"Registered {count} trading tools ({len(disabled)} disabled)")
        return count

    def get_discovered_tools(self) -> Dict[str, Type[Tool]]:
        """Get all discovered tool classes.

        Returns:
            Dict mapping class names to Tool classes
        """
        return dict(self._discovered_classes)
