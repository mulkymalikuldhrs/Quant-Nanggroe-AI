"""AI-MultiColony exception hierarchy.

All exceptions inherit from ``MultiColonyError`` so callers can catch
the base class or any specialised sub-class.

Hierarchy::

    MultiColonyError
    ├── AgentError
    │   ├── AgentNotFoundError
    │   ├── AgentTimeoutError
    │   └── AgentStateError
    ├── ColonyError
    │   ├── ColonyNotFoundError
    │   └── ColonyFullError
    ├── ToolError
    │   ├── ToolNotFoundError
    │   └── ToolPermissionError
    ├── MemoryError
    │   └── MemoryCompactionError
    ├── MCPError
    │   └── MCPProtocolError
    └── SecurityError
        └── PermissionDeniedError
"""

from __future__ import annotations


class MultiColonyError(Exception):
    """Base exception for all ai_multicolony errors."""

    def __init__(self, message: str = "", code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ── Agent Errors ──────────────────────────────────────────────────────────────


class AgentError(MultiColonyError):
    """Agent-related errors."""

    def __init__(self, message: str = "", code: str = "AGENT_ERROR"):
        super().__init__(message, code)


class AgentNotFoundError(AgentError):
    """Requested agent does not exist."""

    def __init__(self, agent_id: str = ""):
        self.agent_id = agent_id
        super().__init__(f"Agent {agent_id} not found", "AGENT_NOT_FOUND")


class AgentTimeoutError(AgentError):
    """Agent execution exceeded its time limit."""

    def __init__(self, message: str = "Agent execution timed out", timeout_ms: int = 0):
        self.timeout_ms = timeout_ms
        super().__init__(message, "AGENT_TIMEOUT")


class AgentStateError(AgentError):
    """Invalid agent state transition."""

    def __init__(self, message: str = "Invalid agent state transition"):
        super().__init__(message, "AGENT_STATE")


# ── Colony Errors ─────────────────────────────────────────────────────────────


class ColonyError(MultiColonyError):
    """Colony management errors."""

    def __init__(self, message: str = "", code: str = "COLONY_ERROR"):
        super().__init__(message, code)


class ColonyNotFoundError(ColonyError):
    """Requested colony does not exist."""

    def __init__(self, colony_id: str = ""):
        self.colony_id = colony_id
        super().__init__(f"Colony {colony_id} not found", "COLONY_NOT_FOUND")


class ColonyFullError(ColonyError):
    """Colony has reached its maximum agent capacity."""

    def __init__(self, colony_id: str = "", max_agents: int = 0):
        self.colony_id = colony_id
        self.max_agents = max_agents
        super().__init__(
            f"Colony {colony_id} is full (max {max_agents} agents)",
            "COLONY_FULL",
        )


# ── Tool Errors ───────────────────────────────────────────────────────────────


class ToolError(MultiColonyError):
    """Tool-related errors."""

    def __init__(self, message: str = "", code: str = "TOOL_ERROR"):
        super().__init__(message, code)


class ToolNotFoundError(ToolError):
    """Requested tool does not exist."""

    def __init__(self, tool_name: str = ""):
        self.tool_name = tool_name
        super().__init__(f"Tool {tool_name} not found", "TOOL_NOT_FOUND")


class ToolPermissionError(ToolError):
    """Insufficient autonomy level for tool invocation."""

    def __init__(
        self,
        tool: str = "",
        required_level: int = 0,
        current_level: int = 0,
    ):
        self.tool = tool
        self.required_level = required_level
        self.current_level = current_level
        super().__init__(
            f"Permission denied: autonomy level {current_level} insufficient "
            f"for tool {tool} (requires level {required_level})",
            "TOOL_PERMISSION",
        )


class ToolTimeoutError(ToolError):
    """Tool execution exceeded its time limit."""

    def __init__(self, tool: str = "", timeout_ms: int = 0):
        self.tool = tool
        self.timeout_ms = timeout_ms
        super().__init__(f"Tool {tool} timed out after {timeout_ms}ms", "TOOL_TIMEOUT")


class ToolRateLimitError(ToolError):
    """Tool rate limit exceeded."""

    def __init__(self, tool: str = "", retry_after: float = 0):
        self.tool = tool
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for tool {tool}", "TOOL_RATE_LIMIT")


class ToolUnavailableError(ToolError):
    """Tool circuit breaker open – tool unavailable."""

    def __init__(self, tool: str = ""):
        self.tool = tool
        super().__init__(f"Tool {tool} is unavailable (circuit breaker open)", "TOOL_UNAVAILABLE")


# ── Memory Errors ─────────────────────────────────────────────────────────────


class MemoryError(MultiColonyError):
    """Memory system errors."""

    def __init__(self, message: str = "", code: str = "MEMORY_ERROR"):
        super().__init__(message, code)


class MemoryCompactionError(MemoryError):
    """Memory compaction failure."""

    def __init__(self, message: str = "Memory compaction failed"):
        super().__init__(message, "MEMORY_COMPACTION")


# ── MCP Errors ────────────────────────────────────────────────────────────────


class MCPError(MultiColonyError):
    """MCP protocol errors."""

    def __init__(self, message: str = "", code: str = "MCP_ERROR"):
        super().__init__(message, code)


class MCPProtocolError(MCPError):
    """Invalid MCP request format or protocol violation."""

    def __init__(self, message: str = "Invalid MCP request"):
        super().__init__(message, "MCP_PROTOCOL")


# ── Security Errors ───────────────────────────────────────────────────────────


class SecurityError(MultiColonyError):
    """Security-related errors."""

    def __init__(self, message: str = "", code: str = "SECURITY_ERROR"):
        super().__init__(message, code)


class AuthenticationError(SecurityError):
    """Authentication failure."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_FAILED")


class PermissionDeniedError(SecurityError):
    """Agent lacks the required permission / autonomy level."""

    def __init__(
        self,
        message: str = "Permission denied",
        agent_id: str = "",
        required_level: int = 0,
        current_level: int = 0,
    ):
        self.agent_id = agent_id
        self.required_level = required_level
        self.current_level = current_level
        super().__init__(message, "PERMISSION_DENIED")


# ── Event Bus Errors ─────────────────────────────────────────────────────────


class EventBusError(MultiColonyError):
    """Event bus related errors."""

    def __init__(self, message: str = "", code: str = "EVENT_BUS_ERROR"):
        super().__init__(message, code)


# ── LLM Errors ────────────────────────────────────────────────────────────────


class LLMError(MultiColonyError):
    """LLM provider errors."""

    def __init__(self, message: str = "", code: str = "LLM_ERROR"):
        super().__init__(message, code)


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    def __init__(self, message: str = "LLM rate limit exceeded", retry_after: float = 0):
        self.retry_after = retry_after
        super().__init__(message, "LLM_RATE_LIMIT")


class LLMTokensExceededError(LLMError):
    """LLM token limit exceeded."""

    def __init__(self, message: str = "Token limit exceeded", tokens_requested: int = 0, tokens_limit: int = 0):
        self.tokens_requested = tokens_requested
        self.tokens_limit = tokens_limit
        super().__init__(message, "LLM_TOKENS_EXCEEDED")


# ── Channel Errors ────────────────────────────────────────────────────────────


class ChannelError(MultiColonyError):
    """Channel/messaging errors."""

    def __init__(self, message: str = "", code: str = "CHANNEL_ERROR"):
        super().__init__(message, code)


# ── Sandbox Errors ────────────────────────────────────────────────────────────


class SandboxError(MultiColonyError):
    """Sandbox execution errors."""

    def __init__(self, message: str = "", code: str = "SANDBOX_ERROR"):
        super().__init__(message, code)


# ── Tool Execution Errors ─────────────────────────────────────────────────────


class ToolExecutionError(ToolError):
    """Generic tool execution failure."""

    def __init__(self, message: str = "Tool execution failed", tool: str = ""):
        self.tool = tool
        super().__init__(message, "TOOL_EXECUTION")
