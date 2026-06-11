"""Colony configuration models for the Multi-Colony Ecosystem.

This module defines the core configuration data models for agent colonies,
including colony types, security levels, and agent-level configuration
with LLM provider failover chains.

Key Models:
    - ColonyConfig: Full colony configuration
    - AgentConfig: Per-agent configuration with LLM failover
    - ColonyType: Enum for colony specializations
    - SecurityLevel: Enum for security clearance levels
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ColonyType(str, Enum):
    """Colony specialization types.

    Each colony type determines the skill set, tool access, and agent
    composition of the colony.
    """

    CODING = "coding"
    RESEARCH = "research"
    TRADING = "trading"
    OPS = "ops"
    CREATIVE = "creative"


class SecurityLevel(str, Enum):
    """Security clearance level for colonies and agents.

    Controls what resources and operations a colony/agent can access.

    Levels:
        SANDBOXED: Isolated execution, no external network or file access.
        ELEVATED: Limited network access, read-only file system.
        PRIVILEGED: Full system access, unrestricted operations.
    """

    SANDBOXED = "sandboxed"
    ELEVATED = "elevated"
    PRIVILEGED = "privileged"


# Default LLM provider failover chain ordered by preference
DEFAULT_LLM_FAILOVER_CHAIN: list[str] = [
    "openai",
    "anthropic",
    "google",
    "deepseek",
    "groq",
    "ollama",
    "local",
]


class AgentConfig(BaseModel):
    """Configuration for an individual agent within a colony.

    Attributes:
        agent_id: Unique identifier for the agent.
        name: Human-readable name for the agent.
        role: The agent's role within the colony (e.g., 'coder', 'reviewer').
        llm_providers: Ordered list of LLM provider failover chain.
            The agent will try providers in order until one succeeds.
        model_name: Preferred model name for the primary LLM provider.
        temperature: Sampling temperature for LLM responses.
        max_tokens: Maximum tokens for LLM responses.
        system_prompt: Optional system prompt override for this agent.
        tool_access: List of tool names this agent is allowed to use.
        memory_budget_mb: Memory budget in megabytes for this agent.
        security_level: Security clearance level for this agent.
        metadata: Additional metadata for the agent.
    """

    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "unnamed-agent"
    role: str = "worker"
    llm_providers: list[str] = Field(
        default_factory=lambda: list(DEFAULT_LLM_FAILOVER_CHAIN),
        description="Ordered LLM provider failover chain.",
    )
    model_name: str = "gpt-4o"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    system_prompt: str | None = None
    tool_access: list[str] = Field(default_factory=list)
    memory_budget_mb: int = Field(default=256, ge=16, le=32768)
    security_level: SecurityLevel = SecurityLevel.SANDBOXED
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("llm_providers")
    @classmethod
    def validate_llm_providers(cls, v: list[str]) -> list[str]:
        """Ensure at least one LLM provider is specified."""
        if not v:
            raise ValueError("At least one LLM provider must be specified.")
        return v


class ColonyConfig(BaseModel):
    """Configuration for an agent colony.

    A colony is a group of specialized agents that collaborate on tasks
    within a specific domain (e.g., coding, research, trading).

    Attributes:
        colony_id: Unique identifier for the colony.
        name: Human-readable name for the colony.
        colony_type: The specialization type of the colony.
        max_agents: Maximum number of agents that can be spawned.
        memory_budget: Total memory budget in MB for the colony.
        tool_access: List of tools available to all agents in the colony.
        security_level: Default security level for agents in this colony.
        agent_configs: List of agent configurations for initial agents.
        llm_failover_chain: Default LLM failover chain for colony agents.
        tags: Tags for categorizing and filtering colonies.
        metadata: Additional metadata for the colony.
    """

    colony_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "unnamed-colony"
    colony_type: ColonyType = ColonyType.CODING
    max_agents: int = Field(default=10, ge=1, le=1000)
    memory_budget: int = Field(default=2048, ge=256, le=262144, description="Memory budget in MB")
    tool_access: list[str] = Field(default_factory=list)
    security_level: SecurityLevel = SecurityLevel.SANDBOXED
    agent_configs: list[AgentConfig] = Field(default_factory=list)
    llm_failover_chain: list[str] = Field(
        default_factory=lambda: list(DEFAULT_LLM_FAILOVER_CHAIN),
    )
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("max_agents")
    @classmethod
    def validate_max_agents(cls, v: int) -> int:
        """Ensure max_agents is a positive integer."""
        if v < 1:
            raise ValueError("max_agents must be at least 1.")
        return v

    def get_default_agent_config(self) -> AgentConfig:
        """Generate a default agent config based on colony settings.

        Returns:
            An AgentConfig with defaults inherited from the colony.
        """
        return AgentConfig(
            llm_providers=list(self.llm_failover_chain),
            tool_access=list(self.tool_access),
            security_level=self.security_level,
        )
