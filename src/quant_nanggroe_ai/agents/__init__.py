"""
Agent Layer Package — LangGraph-based multi-agent trading system
================================================================

Modules:
  - graph: LangGraph trading graph orchestration
  - state: Shared agent state (AgentState)
  - nodes: Individual agent node implementations
  - council: Trading council (9-agent CrewAI, bull/bear debate, risk debate)
  - tools: Agent-accessible tools (market data, execution, backtest, etc.)
  - mcp_protocol: Model Context Protocol for external tool interface
  - mcp_config: MCP server configuration (from ai-manus)
  - a2a_protocol: Agent-to-Agent communication bus
  - dspy_optimizer: DSPy-based prompt optimization
  - pydantic_validator: PydanticAI-style output validation
  - agentpress: AgentPress framework (from suna) — Tool base class, ToolRegistry,
      XML/Native tool parsers, MCP Registry, ContextManager, ErrorProcessor
  - memory: Memory system (from suna) — MemoryStore, MemoryExtractor
  - sandbox: Sandbox execution (from suna) — Isolated code execution
  - scheduler: Scheduler/triggers (from suna) — Scheduled tasks, webhooks, events
"""

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.agents.graph import build_trading_graph, get_trading_graph, set_app, get_app

__all__ = [
    "AgentState",
    "build_trading_graph",
    "get_trading_graph",
    "set_app",
    "get_app",
]
