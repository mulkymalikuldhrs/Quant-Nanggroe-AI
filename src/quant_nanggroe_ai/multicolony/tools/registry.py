"""MCP tool registry for the Multi-Colony Ecosystem.

This module provides a registry for MCP (Model Context Protocol) tools,
enabling tool discovery, registration, and invocation following the
MCP specification.

Tools are external capabilities that agents can invoke through the MCP
protocol, such as browser automation, code execution, and API access.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ToolType(str, Enum):
    """Types of MCP tools."""

    BROWSER = "browser"
    CODE_EXEC = "code_exec"
    API = "api"
    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    CUSTOM = "custom"


class ToolParameter(BaseModel):
    """A parameter definition for an MCP tool.

    Attributes:
        name: Parameter name.
        type: Parameter type (e.g., 'string', 'number', 'boolean').
        description: Parameter description.
        required: Whether the parameter is required.
        default: Default value if not provided.
    """

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None


class ToolMetadata(BaseModel):
    """Metadata for a registered MCP tool.

    Attributes:
        tool_id: Unique identifier for the tool.
        name: Tool name (must be unique).
        description: What the tool does.
        tool_type: Type of the tool.
        parameters: List of tool parameters.
        return_type: Return type description.
        security_level: Required security level to use this tool.
        version: Tool version.
        status: Current tool status.
        invocation_count: Number of times the tool has been invoked.
        avg_invocation_time_ms: Average invocation time in milliseconds.
        error_count: Number of invocation errors.
        registered_at: When the tool was registered.
    """

    tool_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    tool_type: ToolType = ToolType.CUSTOM
    parameters: list[ToolParameter] = Field(default_factory=list)
    return_type: str = "any"
    security_level: str = "sandboxed"
    version: str = "1.0.0"
    status: str = "active"
    invocation_count: int = 0
    avg_invocation_time_ms: float = 0.0
    error_count: int = 0
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolInvocation(BaseModel):
    """Record of a tool invocation.

    Attributes:
        invocation_id: Unique identifier for this invocation.
        tool_id: ID of the invoked tool.
        tool_name: Name of the invoked tool.
        agent_id: ID of the invoking agent.
        arguments: Arguments provided to the tool.
        result: Result returned by the tool.
        success: Whether the invocation succeeded.
        error_message: Error details if invocation failed.
        invocation_time_ms: Invocation time in milliseconds.
        timestamp: When the invocation occurred.
    """

    invocation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str
    tool_name: str
    agent_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    success: bool = True
    error_message: str | None = None
    invocation_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolRegistry:
    """Registry for MCP tools with discovery and invocation.

    The tool registry manages the lifecycle of MCP tools, providing
    methods for registration, discovery, and invocation.

    Example::

        registry = ToolRegistry()

        # Register a tool
        registry.register(
            name="web_search",
            fn=search_web,
            description="Search the web for information",
            tool_type=ToolType.API,
        )

        # Discover tools
        tools = registry.discover(category="api")

        # Invoke a tool
        result = await registry.invoke("web_search", arguments={"query": "AI agents"})
    """

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: dict[str, ToolMetadata] = {}
        self._functions: dict[str, Callable] = {}
        self._invocation_history: list[ToolInvocation] = []
        self._log = logger.bind(component="tool_registry")

    def register(
        self,
        name: str,
        fn: Callable,
        description: str = "",
        tool_type: ToolType = ToolType.CUSTOM,
        parameters: list[ToolParameter] | None = None,
        return_type: str = "any",
        security_level: str = "sandboxed",
        version: str = "1.0.0",
    ) -> ToolMetadata:
        """Register a new MCP tool.

        Args:
            name: Unique tool name.
            fn: The tool invocation function (sync or async).
            description: What the tool does.
            tool_type: Type of the tool.
            parameters: List of tool parameters.
            return_type: Return type description.
            security_level: Required security level.
            version: Tool version.

        Returns:
            The registered tool metadata.

        Raises:
            ToolAlreadyRegisteredError: If a tool with the same name exists.
        """
        # Check for duplicate
        for existing in self._tools.values():
            if existing.name == name:
                raise ToolAlreadyRegisteredError(
                    f"Tool '{name}' is already registered."
                )

        metadata = ToolMetadata(
            name=name,
            description=description,
            tool_type=tool_type,
            parameters=parameters or [],
            return_type=return_type,
            security_level=security_level,
            version=version,
        )

        self._tools[metadata.tool_id] = metadata
        self._functions[metadata.tool_id] = fn

        self._log.info(
            "tool_registered",
            tool_id=metadata.tool_id,
            name=name,
            tool_type=tool_type.value,
        )

        return metadata

    def unregister(self, tool_id: str) -> None:
        """Unregister a tool.

        Args:
            tool_id: ID of the tool to unregister.

        Raises:
            ToolNotFoundError: If the tool is not found.
        """
        if tool_id not in self._tools:
            raise ToolNotFoundError(f"Tool {tool_id} not found.")

        metadata = self._tools.pop(tool_id)
        self._functions.pop(tool_id, None)

        self._log.info(
            "tool_unregistered",
            tool_id=tool_id,
            name=metadata.name,
        )

    def discover(
        self,
        tool_type: ToolType | None = None,
        security_level: str | None = None,
        query: str | None = None,
    ) -> list[ToolMetadata]:
        """Discover tools matching given criteria.

        Args:
            tool_type: Filter by tool type.
            security_level: Filter by security level.
            query: Search in name and description.

        Returns:
            A list of matching tool metadata objects.
        """
        tools = list(self._tools.values())

        if tool_type is not None:
            tools = [t for t in tools if t.tool_type == tool_type]

        if security_level is not None:
            tools = [t for t in tools if t.security_level == security_level]

        if query is not None:
            query_lower = query.lower()
            tools = [
                t for t in tools
                if query_lower in t.name.lower()
                or query_lower in t.description.lower()
            ]

        return tools

    async def invoke(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ) -> ToolInvocation:
        """Invoke an MCP tool by name.

        Args:
            tool_name: Name of the tool to invoke.
            arguments: Arguments to pass to the tool.
            agent_id: ID of the invoking agent.

        Returns:
            A tool invocation record.

        Raises:
            ToolNotFoundError: If the tool is not found.
            ToolInvocationError: If the invocation fails.
        """
        # Resolve tool by name
        metadata = self._resolve_tool(tool_name)
        if metadata is None:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found.")

        fn = self._functions.get(metadata.tool_id)
        if fn is None:
            raise ToolInvocationError(
                f"No invocation function for tool '{metadata.name}'."
            )

        invocation = ToolInvocation(
            tool_id=metadata.tool_id,
            tool_name=metadata.name,
            agent_id=agent_id,
            arguments=arguments or {},
        )

        import time

        start_time = time.monotonic()

        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(**(arguments or {}))
            else:
                result = fn(**(arguments or {}))

            invocation.result = result
            invocation.success = True

        except Exception as exc:
            invocation.success = False
            invocation.error_message = str(exc)
            metadata.error_count += 1

            self._log.error(
                "tool_invocation_failed",
                tool_id=metadata.tool_id,
                name=metadata.name,
                error=str(exc),
            )
            raise ToolInvocationError(
                f"Tool '{metadata.name}' invocation failed: {exc}"
            ) from exc

        finally:
            invocation.invocation_time_ms = (time.monotonic() - start_time) * 1000
            metadata.invocation_count += 1

            # Update average invocation time
            if metadata.invocation_count > 0:
                metadata.avg_invocation_time_ms = (
                    (metadata.avg_invocation_time_ms * (metadata.invocation_count - 1))
                    + invocation.invocation_time_ms
                ) / metadata.invocation_count

            self._invocation_history.append(invocation)

        self._log.info(
            "tool_invoked",
            tool_id=metadata.tool_id,
            name=metadata.name,
            invocation_time_ms=invocation.invocation_time_ms,
        )

        return invocation

    def list_tools(self) -> list[ToolMetadata]:
        """List all registered tools.

        Returns:
            A list of all tool metadata objects.
        """
        return list(self._tools.values())

    def get_tool(self, tool_name: str) -> ToolMetadata:
        """Get a tool's metadata by name.

        Args:
            tool_name: Name of the tool.

        Returns:
            The tool metadata.

        Raises:
            ToolNotFoundError: If the tool is not found.
        """
        metadata = self._resolve_tool(tool_name)
        if metadata is None:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found.")
        return metadata

    def get_invocation_history(
        self,
        tool_name: str | None = None,
        agent_id: str | None = None,
        limit: int | None = None,
    ) -> list[ToolInvocation]:
        """Get tool invocation history.

        Args:
            tool_name: Filter by tool name.
            agent_id: Filter by agent ID.
            limit: Maximum number of records.

        Returns:
            A list of tool invocation records.
        """
        history = list(reversed(self._invocation_history))

        if tool_name is not None:
            history = [h for h in history if h.tool_name == tool_name]
        if agent_id is not None:
            history = [h for h in history if h.agent_id == agent_id]
        if limit is not None:
            history = history[:limit]

        return history

    def _resolve_tool(self, tool_name: str) -> ToolMetadata | None:
        """Resolve a tool by name.

        Args:
            tool_name: Tool name to resolve.

        Returns:
            The tool metadata, or None if not found.
        """
        for metadata in self._tools.values():
            if metadata.name == tool_name:
                return metadata
        return None


class ToolAlreadyRegisteredError(Exception):
    """Raised when attempting to register a duplicate tool."""


class ToolNotFoundError(Exception):
    """Raised when a tool is not found in the registry."""


class ToolInvocationError(Exception):
    """Raised when a tool invocation fails."""
