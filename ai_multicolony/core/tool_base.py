"""Base tool abstract class for the AI MultiColony Ecosystem.

Merges OpenManus BaseTool/ToolResult patterns with AI-Manus BaseTool ABC
and Nanobot tool type system. Every tool in the ecosystem must subclass
BaseTool and implement the ``definition`` property and ``execute`` method.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType


class BaseTool(ABC):
    """Abstract base class for all tools.

    Subclasses must implement:
    - definition: ToolDefinition property
    - execute: The actual tool execution logic

    Following the OpenManus BaseTool pattern with AI-Manus tool_type support.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._id = str(uuid.uuid4())

    @property
    def id(self) -> str:
        """Unique instance ID for this tool."""
        return self._id

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Get the tool definition for registration and LLM schema generation."""
        ...

    @property
    def name(self) -> str:
        """Get the tool name."""
        return self.definition.name

    @property
    def description(self) -> str:
        """Get the tool description."""
        return self.definition.description

    @property
    def tool_type(self) -> ToolType:
        """Get the tool type."""
        return self.definition.tool_type

    @property
    def tags(self) -> list[str]:
        """Get the tool tags."""
        return self.definition.tags

    @abstractmethod
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute the tool with the given call parameters.

        Args:
            tool_call: The tool call containing arguments.

        Returns:
            ToolResult with the execution result.
        """
        ...

    async def safe_execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute the tool with error handling wrapper.

        Args:
            tool_call: The tool call containing arguments.

        Returns:
            ToolResult with success or error information.
        """
        start_time = time.time()
        try:
            # Validate arguments before execution
            validation_errors = self.validate_arguments(tool_call.arguments)
            if validation_errors:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.tool_name,
                    success=False,
                    error=f"Validation errors: {'; '.join(validation_errors)}",
                    execution_time=time.time() - start_time,
                )

            result = await self.execute(tool_call)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.tool_name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    def validate_arguments(self, arguments: dict[str, Any]) -> list[str]:
        """Validate tool arguments against parameter definitions.

        Args:
            arguments: The arguments to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []
        param_map = {p.name: p for p in self.definition.parameters}

        # Check required parameters
        for param in self.definition.parameters:
            if param.required and param.name not in arguments:
                if param.default is None:
                    errors.append(f"Missing required parameter: {param.name}")

        # Check for unknown parameters
        for key in arguments:
            if key not in param_map:
                errors.append(f"Unknown parameter: {key}")

        # Validate enum values
        for param in self.definition.parameters:
            if param.name in arguments and param.enum:
                val = arguments[param.name]
                if val not in param.enum:
                    errors.append(
                        f"Parameter '{param.name}' must be one of {param.enum}, "
                        f"got '{val}'"
                    )

        return errors

    def get_openai_schema(self) -> dict[str, Any]:
        """Get the OpenAI function calling schema for this tool."""
        return self.definition.to_openai_schema()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, type={self.tool_type.value})"
