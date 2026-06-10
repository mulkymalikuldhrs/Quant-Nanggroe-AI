"""
MCP Configuration — Model Context Protocol Server Configuration
================================================================
Merged from ai-manus main/mcp_config.py and tmp branch, adapted for
Quant-Nanggroe-AI.

Provides:
  - MCPTransport: Enum for MCP transport types (stdio, sse, streamable-http)
  - MCPServerConfig: Configuration for a single MCP server
  - MCPConfig: Configuration model containing all server configurations
  - load_mcp_config: Load MCP configuration from file
  - get_default_mcp_config: Get default MCP configuration for the trading platform

Adapted from:
  - ai-manus/backend/app/domain/models/mcp_config.py
  - ai-manus/tmp branch event models
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MCP Configuration Models
# ══════════════════════════════════════════════════════════════════════


class MCPTransport(str, Enum):
    """MCP transport types."""
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"


class MCPServerConfig(BaseModel):
    """
    Configuration for a single MCP server.

    Supports two transport modes:
      - stdio: Run a local command and communicate via stdin/stdout
      - sse / streamable-http: Connect to an HTTP endpoint

    Fields:
        command: Command to run (for stdio transport).
        args: Command arguments (for stdio transport).
        url: Server URL (for HTTP-based transports).
        headers: HTTP headers to include (for HTTP-based transports).
        transport: The transport type (required).
        enabled: Whether this server is active.
        description: Human-readable description.
        env: Environment variables to pass to the command.
    """

    # For stdio transport
    command: Optional[str] = None
    args: Optional[list[str]] = None

    # For HTTP-based transports
    url: Optional[str] = None
    headers: Optional[dict[str, str]] = None

    # Common fields
    transport: MCPTransport
    enabled: bool = Field(default=True)
    description: Optional[str] = None
    env: Optional[dict[str, str]] = None

    @field_validator("url")
    @classmethod
    def validate_url_for_http_transport(
        cls, v: Optional[str], info: Any
    ) -> Optional[str]:
        """Validate URL is required for HTTP-based transports."""
        if info.data.get("transport") in (MCPTransport.SSE, MCPTransport.STREAMABLE_HTTP):
            if not v:
                raise ValueError("URL is required for HTTP-based transports")
        return v

    @field_validator("command")
    @classmethod
    def validate_command_for_stdio(
        cls, v: Optional[str], info: Any
    ) -> Optional[str]:
        """Validate command is required for stdio transport."""
        if info.data.get("transport") == MCPTransport.STDIO:
            if not v:
                raise ValueError("Command is required for stdio transport")
        return v

    model_config = {"extra": "allow"}


class MCPConfig(BaseModel):
    """
    MCP configuration model containing all server configurations.

    Follows the standard MCP configuration format where mcpServers
    maps server names to their configurations.

    Example JSON::

        {
            "mcpServers": {
                "market-data": {
                    "transport": "sse",
                    "url": "http://localhost:8080/mcp",
                    "enabled": true,
                    "description": "Market data MCP server"
                },
                "trading-executor": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["-m", "quant_nanggroe_ai.mcp_server"],
                    "enabled": true
                }
            }
        }
    """

    mcpServers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def get_enabled_servers(self) -> dict[str, MCPServerConfig]:
        """Return only the enabled MCP servers."""
        return {
            name: config
            for name, config in self.mcpServers.items()
            if config.enabled
        }

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get configuration for a specific server by name."""
        return self.mcpServers.get(name)

    def add_server(self, name: str, config: MCPServerConfig) -> None:
        """Add or update a server configuration."""
        self.mcpServers[name] = config

    def remove_server(self, name: str) -> bool:
        """Remove a server configuration. Returns True if found and removed."""
        if name in self.mcpServers:
            del self.mcpServers[name]
            return True
        return False


# ══════════════════════════════════════════════════════════════════════
# Configuration Loading
# ══════════════════════════════════════════════════════════════════════


def load_mcp_config(config_path: str | Path) -> MCPConfig:
    """
    Load MCP configuration from a JSON file.

    Args:
        config_path: Path to the MCP configuration JSON file.

    Returns:
        Parsed MCPConfig object.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        json.JSONDecodeError: If the file is not valid JSON.
        pydantic.ValidationError: If the config doesn't match the schema.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"MCP config file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    config = MCPConfig.model_validate(data)
    logger.info("Loaded MCP config with %d servers from %s", len(config.mcpServers), path)
    return config


def save_mcp_config(config: MCPConfig, config_path: str | Path) -> None:
    """
    Save MCP configuration to a JSON file.

    Args:
        config: The MCPConfig object to save.
        config_path: Path to write the JSON file.
    """
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write(config.model_dump_json(indent=2))
        f.write("\n")

    logger.info("Saved MCP config with %d servers to %s", len(config.mcpServers), path)


def get_default_mcp_config() -> MCPConfig:
    """
    Get default MCP configuration for the Quant-Nanggroe-AI trading platform.

    Returns:
        MCPConfig with default server configurations for the platform's
        built-in MCP tools (market_data, trading, risk, backtest, research).
    """
    return MCPConfig(
        mcpServers={
            "market-data": MCPServerConfig(
                transport=MCPTransport.SSE,
                url="http://localhost:8000/api/v1/mcp/market-data",
                enabled=True,
                description="Market data MCP server — OHLCV, prices, batch fetch",
            ),
            "trading": MCPServerConfig(
                transport=MCPTransport.SSE,
                url="http://localhost:8000/api/v1/mcp/trading",
                enabled=True,
                description="Trading MCP server — orders, positions, account",
            ),
            "risk": MCPServerConfig(
                transport=MCPTransport.SSE,
                url="http://localhost:8000/api/v1/mcp/risk",
                enabled=True,
                description="Risk management MCP server — checkpoints, status",
            ),
            "backtest": MCPServerConfig(
                transport=MCPTransport.SSE,
                url="http://localhost:8000/api/v1/mcp/backtest",
                enabled=True,
                description="Backtest MCP server — run backtests, results",
            ),
            "research": MCPServerConfig(
                transport=MCPTransport.SSE,
                url="http://localhost:8000/api/v1/mcp/research",
                enabled=True,
                description="Research MCP server — sentiment, memory, search",
            ),
        }
    )


# ══════════════════════════════════════════════════════════════════════
# MCP Tool Event Types (from tmp branch agent_events.py)
# ══════════════════════════════════════════════════════════════════════


class MCPToolEventType(str, Enum):
    """Event types for MCP tool interactions."""
    TOOL_CALLING = "calling"
    TOOL_CALLED = "called"
    TOOL_ERROR = "error"


class MCPToolEvent(BaseModel):
    """
    Event record for an MCP tool interaction.

    Used for tracking and auditing tool calls through the MCP protocol.
    """
    event_type: MCPToolEventType
    tool_name: str
    function_name: str
    function_args: dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: str = ""

    model_config = {"arbitrary_types_allowed": True}
