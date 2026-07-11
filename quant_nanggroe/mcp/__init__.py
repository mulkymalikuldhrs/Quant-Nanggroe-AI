"""MCP (Model Context Protocol) Integration Layer for Quant Nanggroe AI.

Implements the MCP specification for tool communication between AI agents
and trading engine capabilities. This is the CRITICAL integration layer
identified as the #1 adoption priority in the comprehensive benchmark.

The MCP layer provides:
- JSON-RPC 2.0 protocol for tool communication
- Tool discovery, listing, and execution
- Trading-specific tools (market data, orders, risk, factors, backtest, portfolio)
- Server implementation for tool registration
- Client for connecting to multiple MCP servers
- SSE transport for streaming results
- Health check and capability discovery

Quick Start:
    # Server side
    from quant_nanggroe.mcp import MCPServer, register_all_trading_tools

    server = MCPServer(name="quant-nanggroe", version="0.2.0")
    register_all_trading_tools(server)

    # Client side
    from quant_nanggroe.mcp import LocalMCPClient

    client = LocalMCPClient(server)
    tools = client.list_tools()
    result = client.call_tool("market_data.get_ticker", {"symbol": "BTC/USDT"})

Architecture:
    protocol.py  → JSON-RPC 2.0 types, messages, helpers
    server.py    → MCPServer, ToolHandler, FunctionToolHandler
    tools.py     → Trading-specific tool definitions and implementations
    client.py    → MCPClient (multi-server), LocalMCPClient (in-process)
"""

from quant_nanggroe.mcp.client import (
    ConnectionState,
    LocalMCPClient,
    MCPClient,
    ServerConnection,
)
from quant_nanggroe.mcp.protocol import (
    CallToolParams,
    CallToolResult,
    HealthCheckResult,
    InitializeParams,
    InitializeResult,
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCSuccessResponse,
    JSONRPCVersion,
    ListToolsResult,
    MCPErrorCodes,
    ServerCapabilities,
    ServerInfo,
    SSEEvent,
    ToolCallResult,
    ToolDefinition,
    ToolInputSchema,
    ToolOutputSchema,
    make_error_response,
    make_notification,
    make_request,
    make_success_response,
)
from quant_nanggroe.mcp.server import (
    FunctionToolHandler,
    MCPServer,
    ToolHandler,
)
from quant_nanggroe.mcp.tools import (
    BACKTEST_RUN,
    BACKTEST_WALK_FORWARD,
    FACTORS_COMPUTE,
    FACTORS_GET_META,
    FACTORS_HEALTH,
    FACTORS_LIST,
    MARKET_DATA_GET_MARKET_DATA,
    MARKET_DATA_GET_OHLCV,
    MARKET_DATA_GET_ORDERBOOK,
    MARKET_DATA_GET_TICKER,
    ORDERS_CANCEL_ORDER,
    ORDERS_GET_ORDER_STATUS,
    ORDERS_PLACE_ORDER,
    PORTFOLIO_GET,
    PORTFOLIO_GET_PERFORMANCE,
    PORTFOLIO_GET_POSITION,
    PORTFOLIO_GET_POSITIONS,
    RISK_ASSESS_TRADE,
    RISK_COMPUTE_DRAWDOWN,
    RISK_COMPUTE_VAR,
    TRADING_TOOLS,
    get_trading_tool_categories,
    get_trading_tool_names,
    register_all_trading_tools,
)

__all__ = [
    # Protocol
    "JSONRPCVersion",
    "MCPErrorCodes",
    "JSONRPCError",
    "JSONRPCRequest",
    "JSONRPCNotification",
    "JSONRPCSuccessResponse",
    "JSONRPCErrorResponse",
    "JSONRPCResponse",
    "ToolInputSchema",
    "ToolOutputSchema",
    "ToolDefinition",
    "ToolCallResult",
    "CallToolParams",
    "CallToolResult",
    "ServerCapabilities",
    "ServerInfo",
    "InitializeParams",
    "InitializeResult",
    "ListToolsResult",
    "HealthCheckResult",
    "SSEEvent",
    "make_request",
    "make_success_response",
    "make_error_response",
    "make_notification",
    # Server
    "ToolHandler",
    "FunctionToolHandler",
    "MCPServer",
    # Tools
    "MARKET_DATA_GET_OHLCV",
    "MARKET_DATA_GET_TICKER",
    "MARKET_DATA_GET_ORDERBOOK",
    "MARKET_DATA_GET_MARKET_DATA",
    "ORDERS_PLACE_ORDER",
    "ORDERS_CANCEL_ORDER",
    "ORDERS_GET_ORDER_STATUS",
    "RISK_ASSESS_TRADE",
    "RISK_COMPUTE_VAR",
    "RISK_COMPUTE_DRAWDOWN",
    "FACTORS_LIST",
    "FACTORS_COMPUTE",
    "FACTORS_GET_META",
    "FACTORS_HEALTH",
    "BACKTEST_RUN",
    "BACKTEST_WALK_FORWARD",
    "PORTFOLIO_GET",
    "PORTFOLIO_GET_POSITIONS",
    "PORTFOLIO_GET_POSITION",
    "PORTFOLIO_GET_PERFORMANCE",
    "TRADING_TOOLS",
    "register_all_trading_tools",
    "get_trading_tool_names",
    "get_trading_tool_categories",
    # Client
    "ConnectionState",
    "ServerConnection",
    "MCPClient",
    "LocalMCPClient",
]
