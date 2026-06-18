"""Tool registry with decorator-based registration for the AI MultiColony Ecosystem.

Merges AI-Manus @tool decorator pattern with Nanobot ToolRegistry tag-based lookup
and OpenManus tool management. Provides:
- Register tools by class or instance
- Decorator-based registration with @tool
- Tag-based lookup (from Nanobot)
- Type-based lookup
- OpenAI schema generation for all registered tools
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Optional, Type

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for managing and discovering tools.

    Supports:
    - Register tools by class or instance
    - Decorator-based registration with @tool
    - Tag-based lookup (from Nanobot)
    - Type-based lookup
    - OpenAI schema generation for all registered tools
    """

    _instance: Optional[ToolRegistry] = None

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._tool_classes: dict[str, Type[BaseTool]] = {}
        self._tags: dict[str, set[str]] = {}

    @classmethod
    def get_instance(cls) -> ToolRegistry:
        """Get the global singleton registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the global registry (for testing)."""
        cls._instance = None

    def register(
        self,
        tool_cls: Optional[Type[BaseTool]] = None,
        name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Register a tool class or instance.

        Can be used as a decorator or called directly:

            @registry.register(tags=["shell", "execution"])
            class ShellTool(BaseTool):
                ...

        Or:

            registry.register(ShellTool, name="shell", tags=["shell"])

        Args:
            tool_cls: The tool class to register.
            name: Optional override name.
            tags: Additional tags for lookup.
            config: Optional configuration for the tool instance.

        Returns:
            The original class (when used as decorator) or None.
        """
        if tool_cls is None:
            def decorator(cls: Type[BaseTool]) -> Type[BaseTool]:
                self._register_class(cls, name=name, tags=tags, config=config)
                return cls
            return decorator

        if isinstance(tool_cls, type):
            self._register_class(tool_cls, name=name, tags=tags, config=config)
            return tool_cls
        else:
            raise TypeError(f"Expected a class, got {type(tool_cls)}")

    def _register_class(
        self,
        tool_cls: Type[BaseTool],
        name: Optional[str] = None,
        tags: Optional[list[str]] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        """Register a tool class internally."""
        try:
            instance = tool_cls(config=config)
            tool_name = name or instance.name
        except Exception as e:
            logger.error("tool_registration_error", cls=tool_cls.__name__, error=str(e))
            raise

        self._tools[tool_name] = instance
        self._tool_classes[tool_name] = tool_cls

        all_tags = set(instance.tags)
        if tags:
            all_tags.update(tags)

        for tag in all_tags:
            if tag not in self._tags:
                self._tags[tag] = set()
            self._tags[tag].add(tool_name)

        logger.debug("tool_registered", name=tool_name, tags=list(all_tags))

    def register_instance(self, tool_instance: BaseTool, tags: Optional[list[str]] = None) -> None:
        """Register a pre-created tool instance.

        Args:
            tool_instance: The tool instance to register.
            tags: Additional tags for lookup.
        """
        name = tool_instance.name
        self._tools[name] = tool_instance

        all_tags = set(tool_instance.tags)
        if tags:
            all_tags.update(tags)

        for tag in all_tags:
            if tag not in self._tags:
                self._tags[tag] = set()
            self._tags[tag].add(name)

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tool_type: ToolType = ToolType.SHELL,
        tags: Optional[list[str]] = None,
        parameters: Optional[list[ToolParameter]] = None,
    ) -> None:
        """Register a plain function as a tool.

        Convenience method that wraps a function in a BaseTool subclass.

        Args:
            func: The function to register.
            name: Tool name (defaults to function name).
            description: Tool description (defaults to docstring).
            tool_type: The tool type.
            tags: Tags for discovery.
            parameters: Parameter definitions.
        """
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or ""
        tool_tags = tags or []
        tool_params = parameters or []

        class FunctionTool(BaseTool):
            _func: Callable = func
            _def: ToolDefinition = ToolDefinition(
                name=tool_name,
                description=tool_description,
                tool_type=tool_type,
                parameters=tool_params,
                tags=tool_tags,
            )

            @property
            def definition(self) -> ToolDefinition:
                return self._def

            async def execute(self, tool_call: ToolCall) -> ToolResult:
                try:
                    if inspect.iscoroutinefunction(self._func):
                        result = await self._func(**tool_call.arguments)
                    else:
                        result = self._func(**tool_call.arguments)
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.tool_name,
                        success=True,
                        output=str(result),
                    )
                except Exception as e:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.tool_name,
                        success=False,
                        error=str(e),
                    )

        FunctionTool.__name__ = f"{tool_name.title()}Tool"
        FunctionTool.__qualname__ = f"{tool_name.title()}Tool"
        self._register_class(FunctionTool)

    def get(self, name: str) -> BaseTool:
        """Get a tool by name.

        Args:
            name: The registered tool name.

        Returns:
            The tool instance.

        Raises:
            KeyError: If the tool is not found.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
        return self._tools[name]

    def get_by_tag(self, tag: str) -> list[BaseTool]:
        """Get all tools with a specific tag.

        Args:
            tag: The tag to search for.

        Returns:
            List of tool instances with the tag.
        """
        tool_names = self._tags.get(tag, set())
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_by_type(self, tool_type: ToolType) -> list[BaseTool]:
        """Get all tools of a specific type.

        Args:
            tool_type: The tool type to filter by.

        Returns:
            List of tool instances of the given type.
        """
        return [t for t in self._tools.values() if t.tool_type == tool_type]

    def list_all(self) -> dict[str, dict[str, Any]]:
        """List all registered tools with their metadata.

        Returns:
            Dictionary of tool name -> info dict.
        """
        result = {}
        for name, tool_instance in self._tools.items():
            result[name] = {
                "name": name,
                "description": tool_instance.description,
                "tool_type": tool_instance.tool_type.value,
                "tags": tool_instance.tags,
                "version": tool_instance.definition.version,
            }
        return result

    def get_openai_schemas(self, tool_names: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """Get OpenAI function calling schemas for tools.

        Args:
            tool_names: Optional list of tool names. If None, returns all.

        Returns:
            List of OpenAI function schemas.
        """
        if tool_names:
            tools = [self._tools[n] for n in tool_names if n in self._tools]
        else:
            tools = list(self._tools.values())
        return [t.get_openai_schema() for t in tools]

    def unregister(self, name: str) -> None:
        """Unregister a tool by name.

        Args:
            name: The tool name to unregister.
        """
        if name in self._tools:
            tool_instance = self._tools[name]
            for tag in tool_instance.tags:
                if tag in self._tags:
                    self._tags[tag].discard(name)
                    if not self._tags[tag]:
                        del self._tags[tag]
            del self._tools[name]
            self._tool_classes.pop(name, None)

    def clear(self) -> None:
        """Remove all registered tools."""
        self._tools.clear()
        self._tool_classes.clear()
        self._tags.clear()

    @property
    def tool_count(self) -> int:
        """Number of registered tools."""
        return len(self._tools)

    @property
    def tool_names(self) -> list[str]:
        """Names of all registered tools."""
        return list(self._tools.keys())

    @property
    def all_tags(self) -> list[str]:
        """All registered tags."""
        return list(self._tags.keys())

    async def execute(self, tool_name: str, arguments: dict[str, Any], agent_id: Optional[str] = None) -> ToolResult:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments for the tool.
            agent_id: Optional agent ID making the call.

        Returns:
            ToolResult from the execution.
        """
        tool_instance = self.get(tool_name)
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            agent_id=agent_id,
        )
        return await tool_instance.safe_execute(tool_call)


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    tool_type: ToolType = ToolType.SHELL,
    tags: Optional[list[str]] = None,
    parameters: Optional[list[ToolParameter]] = None,
) -> Callable:
    """Decorator to define a simple function-based tool.

    This is a convenience decorator for creating tools from plain functions
    without needing to subclass BaseTool.

    Usage:
        @tool(name="greet", description="Say hello", tool_type=ToolType.SHELL)
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

    Args:
        name: Tool name (defaults to function name).
        description: Tool description (defaults to docstring).
        tool_type: The tool type.
        tags: Tags for discovery.
        parameters: Parameter definitions.

    Returns:
        Decorated function that is also a BaseTool.
    """

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or ""
        tool_tags = tags or []
        tool_params = parameters or []

        class FunctionTool(BaseTool):
            _func: Callable = func
            _definition: ToolDefinition = ToolDefinition(
                name=tool_name,
                description=tool_description,
                tool_type=tool_type,
                parameters=tool_params,
                tags=tool_tags,
            )

            @property
            def definition(self) -> ToolDefinition:
                return self._definition

            async def execute(self, tool_call: ToolCall) -> ToolResult:
                try:
                    if inspect.iscoroutinefunction(self._func):
                        result = await self._func(**tool_call.arguments)
                    else:
                        result = self._func(**tool_call.arguments)
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.tool_name,
                        success=True,
                        output=str(result),
                    )
                except Exception as e:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.tool_name,
                        success=False,
                        error=str(e),
                    )

        FunctionTool.__name__ = f"{tool_name.title()}Tool"
        FunctionTool.__qualname__ = f"{tool_name.title()}Tool"

        # Attach metadata to the function for discovery
        func._tool_cls = FunctionTool
        func._tool_name = tool_name
        func._tool_tags = tool_tags

        return func

    return decorator
