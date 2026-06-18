"""Tool type definitions for the AI MultiColony Ecosystem.

Merges AI-Manus tool_type pattern, Nanobot ToolRegistry tags, and
OpenManus BaseTool/ToolResult Pydantic models.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Types of tools available in the system."""

    SHELL = "shell"
    FILE = "file"
    BROWSER = "browser"
    SEARCH = "search"
    CODE = "code"
    MCP = "mcp"
    DOCKER = "docker"
    VOICE = "voice"
    MEMORY = "memory"
    CHANNEL = "channel"


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[list[str]] = None
    examples: Optional[list[Any]] = None

    model_config = {"arbitrary_types_allowed": True}


class ToolCall(BaseModel):
    """A call to a tool by an agent.

    Represents the LLM's request to invoke a tool.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    timeout: Optional[int] = None

    model_config = {"arbitrary_types_allowed": True}

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.tool_name,
                "arguments": str(self.arguments),
            },
        }


class ToolResult(BaseModel):
    """Result of a tool execution.

    Following OpenManus ToolResult pattern.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_call_id: str = ""
    tool_name: str = ""
    success: bool = True
    output: str = ""
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    model_config = {"arbitrary_types_allowed": True}

    def to_message(self) -> dict[str, Any]:
        """Convert to an OpenAI tool message format."""
        content = self.output if self.success else f"Error: {self.error}"
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": content,
        }


class ToolDefinition(BaseModel):
    """Complete definition of a tool for registration and LLM function calling."""

    name: str
    description: str
    tool_type: ToolType
    parameters: list[ToolParameter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    requires_permission: Optional[str] = None
    timeout: int = 60
    examples: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.examples:
                prop["examples"] = param.examples
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
