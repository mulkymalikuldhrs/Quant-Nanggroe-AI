"""Agent types — AgentState, AgentConfig, AgentContract.

These types define the agent subsystem: how agents are configured,
their current state, capabilities, and the contracts that govern
their decision scope and hard constraints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentCapability(str, Enum):
    """Agent capability classification.

    Each agent has a primary capability that determines its role
    in the multi-agent trading system.
    """

    PORTFOLIO_MANAGER = "portfolio_manager"
    QUANT = "quant"
    FUNDAMENTAL = "fundamental"
    RISK_MANAGER = "risk_manager"
    ALGO_DEV = "algo_dev"
    SMC = "smc"
    NEWS_SENTINEL = "news_sentinel"
    FLOW_WHALE = "flow_whale"
    GENERAL = "general"


class AgentStatus(str, Enum):
    """Agent health status."""

    HEALTHY = "healthy"
    RECOVERING = "recovering"
    CRITICAL = "critical"
    OFFLINE = "offline"


class AgentConfig(BaseModel):
    """Configuration for a trading agent.

    Defines the agent's identity, capability, tools, and constraints.
    """

    agent_id: str = Field(description="Unique agent identifier")
    name: str = Field(description="Human-readable agent name")
    capability: AgentCapability = Field(description="Primary agent capability")
    instructions: str = Field(default="", description="Agent system instructions")
    tools: list[str] = Field(default_factory=list, description="Available tools")
    model: str = Field(default="gpt-4", description="LLM model to use")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM temperature")
    max_iterations: int = Field(default=10, ge=1, description="Max agent loop iterations")
    enabled: bool = Field(default=True, description="Whether the agent is active")

    model_config = {"json_schema_extra": {
        "examples": [{
            "agent_id": "quant_scanner_01",
            "name": "Quant Scanner",
            "capability": "quant",
            "instructions": "Analyze technical indicators and generate signals.",
            "tools": ["market_data", "indicators"],
            "model": "gpt-4",
        }]
    }}


class AgentState(BaseModel):
    """Runtime state of a trading agent.

    Tracks the agent's current status, active context, and metrics.
    """

    agent_id: str = Field(description="Agent identifier")
    status: AgentStatus = Field(default=AgentStatus.HEALTHY, description="Current health status")
    is_active: bool = Field(default=False, description="Whether agent is currently processing")
    current_action: Optional[str] = Field(default=None, description="Current action being performed")
    last_signal_time: Optional[datetime] = Field(default=None, description="Last signal generation time")
    total_signals: int = Field(default=0, ge=0, description="Total signals generated")
    successful_signals: int = Field(default=0, ge=0, description="Signals that led to profitable trades")
    error_count: int = Field(default=0, ge=0, description="Error count since last reset")
    last_error: Optional[str] = Field(default=None, description="Last error message")
    uptime_seconds: float = Field(default=0.0, ge=0.0, description="Agent uptime in seconds")

    @property
    def signal_success_rate(self) -> float:
        """Ratio of successful signals to total signals."""
        if self.total_signals == 0:
            return 0.0
        return self.successful_signals / self.total_signals

    model_config = {"json_schema_extra": {
        "examples": [{
            "agent_id": "quant_scanner_01",
            "status": "healthy",
            "is_active": True,
            "current_action": "analyzing BTC/USDT",
            "total_signals": 150,
            "successful_signals": 98,
        }]
    }}


class AgentContract(BaseModel):
    """Contract that governs an agent's decision scope and constraints.

    Inspired by Quant-Nanggroe-AI's AgentContract which defines
    the boundaries within which an agent may operate.
    """

    agent_id: str = Field(description="Agent identifier this contract applies to")
    input_domain: list[str] = Field(
        default_factory=list,
        description="Data domains the agent may access (e.g., ['market', 'macro'])",
    )
    decision_scope: list[str] = Field(
        default_factory=list,
        description="Decisions the agent is authorized to make",
    )
    hard_constraints: list[str] = Field(
        default_factory=list,
        description="Hard constraints that can never be violated",
    )
    max_position_size: Optional[float] = Field(
        default=None,
        description="Maximum position size this agent can recommend",
    )
    max_risk_per_trade: Optional[float] = Field(
        default=None,
        description="Maximum risk per trade (fraction of portfolio)",
    )

    model_config = {"json_schema_extra": {
        "examples": [{
            "agent_id": "quant_scanner_01",
            "input_domain": ["market", "technical"],
            "decision_scope": ["signal_generation", "entry_timing"],
            "hard_constraints": [
                "No trades in NO_TRADE regime",
                "Max 2% risk per trade",
                "Must respect market structure",
            ],
        }]
    }}
