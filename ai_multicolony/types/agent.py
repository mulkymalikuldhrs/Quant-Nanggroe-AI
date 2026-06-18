"""Agent type definitions for the AI MultiColony Ecosystem.

Defines AgentState, AgentRole, AgentConfig, AgentOutput, and AgentCapabilities
for the full agent lifecycle.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Possible states of an agent."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"
    WAITING = "waiting"
    THINKING = "thinking"


class AgentRole(str, Enum):
    """Roles that an agent can fulfill."""

    MANUS = "manus"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CODER = "coder"
    BROWSER = "browser"
    VOICE = "voice"
    SECURITY = "security"
    RESEARCHER = "researcher"
    COLONY = "colony"
    SUPERVISOR = "supervisor"
    WORKER = "worker"


class AgentCapabilities(BaseModel):
    """Capabilities that an agent possesses.

    Used to declare what an agent can do so that the colony scheduler
    can assign appropriate tasks.
    """

    code_generation: bool = Field(default=False, description="Can generate source code")
    code_execution: bool = Field(default=False, description="Can execute code in a sandbox")
    web_browsing: bool = Field(default=False, description="Can browse the web")
    file_operations: bool = Field(default=False, description="Can read/write files")
    shell_execution: bool = Field(default=False, description="Can execute shell commands")
    web_search: bool = Field(default=False, description="Can search the web")
    voice_input: bool = Field(default=False, description="Can process voice input")
    voice_output: bool = Field(default=False, description="Can produce voice output")
    memory_management: bool = Field(default=False, description="Can manage memory pages")
    planning: bool = Field(default=False, description="Can plan and decompose tasks")
    security_analysis: bool = Field(default=False, description="Can perform security analysis")
    research: bool = Field(default=False, description="Can conduct research")
    colony_management: bool = Field(default=False, description="Can manage colony operations")
    mcp_protocol: bool = Field(default=False, description="Can use MCP protocol")
    docker_management: bool = Field(default=False, description="Can manage Docker containers")

    def to_list(self) -> list[str]:
        """Convert enabled capabilities to a list of strings."""
        return [key for key, val in self.model_dump().items() if val]

    @classmethod
    def from_list(cls, capabilities: list[str]) -> AgentCapabilities:
        """Create from a list of capability strings."""
        data = {c: True for c in capabilities}
        return cls(**data)


class AgentConfig(BaseModel):
    """Configuration for an agent instance."""

    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="unnamed-agent")
    role: AgentRole = Field(default=AgentRole.MANUS)
    model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=4096)
    max_iterations: int = Field(default=10)
    timeout: int = Field(default=300)
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    tools: list[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    description: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[str] = None
    colony_id: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


class AgentOutput(BaseModel):
    """Structured output from an agent execution.

    Captures the result, metrics, and metadata from a completed
    agent run for downstream processing and auditing.
    """

    agent_id: str
    task: str = ""
    result: str = ""
    success: bool = True
    error: Optional[str] = None
    iterations: int = 0
    tokens_used: int = 0
    cost_incurred: float = 0.0
    duration: float = 0.0
    tool_calls: int = 0
    subagents_spawned: int = 0
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class AgentStatus(BaseModel):
    """Runtime status of an agent."""

    agent_id: str
    name: str
    role: AgentRole
    state: AgentState = AgentState.IDLE
    current_task: Optional[str] = None
    iterations: int = 0
    tokens_used: int = 0
    cost_incurred: float = 0.0
    error_count: int = 0
    last_action: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    subagents: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class SubagentSpawn(BaseModel):
    """Request to spawn a subagent."""

    role: AgentRole
    task: str
    tools: list[str] = Field(default_factory=list)
    model: Optional[str] = None
    timeout: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
