"""
MCP Protocol — Model Context Protocol for Tool Interface
==========================================================
Allows external AI models to interact with the Quant-Nanggroe-AI
trading system through a standardized tool interface.

The MCP protocol provides a clean boundary between AI model reasoning
and trading system execution. External models discover available tools
via ``list_tools``, inspect their schemas via ``get_tool_schema``, and
invoke them via ``call_tool``.

Built-in MCP tools wrap the existing agent tool layer:
  - MarketDataMCPTool   → MarketDataTool (OHLCV, prices, market data)
  - TradingMCPTool      → ExecutionTool (orders, positions, account)
  - RiskMCPTool         → ConstitutionalRiskGuard (risk status, checks)
  - BacktestMCPTool     → BacktestTool (backtests, results)
  - ResearchMCPTool     → SentimentTool + memory (research, search)

All tools return structured dicts that conform to the MCP response
specification: ``{"status": "success"|"error", "data": ..., "error": ...}``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

from quant_nanggroe_ai.exceptions import (
    AgentError,
    DataError,
    EngineError,
    ExecutionError,
    QuantNanggroeAIError,
    RiskError,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MCP Protocol Types
# ══════════════════════════════════════════════════════════════════════


class MCPToolMetadata(BaseModel):
    """Metadata about an MCP tool, following JSON Schema conventions."""

    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)


class MCPToolResult(BaseModel):
    """
    Standardized result envelope for MCP tool invocations.

    Every ``call_tool`` returns this structure so that consumers can
    uniformly handle success and error cases.
    """

    status: str  # "success" | "error"
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    error_code: str | None = None
    execution_time_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MCPToolCallRecord(BaseModel):
    """Audit record for a single tool invocation."""

    tool_name: str
    arguments: dict[str, Any]
    result_status: str
    execution_time_ms: float
    timestamp: str
    caller_id: str | None = None


# ══════════════════════════════════════════════════════════════════════
# MCPTool — Base class for MCP-compatible tools
# ══════════════════════════════════════════════════════════════════════


class MCPTool(ABC):
    """
    Base class for all MCP-compatible tools.

    Subclasses must implement:
      - ``name`` property: unique tool identifier
      - ``description`` property: human-readable description
      - ``input_schema`` property: JSON Schema for the tool's input
      - ``execute(**kwargs)`` method: actual tool logic

    The ``execute`` method should return a plain dict. The base class
    wraps it in an ``MCPToolResult`` envelope, measures execution time,
    and handles exceptions gracefully.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool (e.g. 'market_data.get_ohlcv')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """
        JSON Schema describing the tool's input parameters.

        Must follow JSON Schema draft-07 conventions with ``type``,
        ``properties``, ``required``, etc.
        """

    @property
    def output_schema(self) -> dict[str, Any]:
        """
        JSON Schema describing the tool's output.

        Optional — defaults to an empty schema (any output accepted).
        """
        return {}

    @property
    def version(self) -> str:
        """Tool version string."""
        return "1.0.0"

    @property
    def tags(self) -> list[str]:
        """Tags for tool categorization and filtering."""
        return []

    def get_metadata(self) -> MCPToolMetadata:
        """
        Return full metadata for this tool.

        Returns:
            MCPToolMetadata with name, description, schema, version, tags.
        """
        return MCPToolMetadata(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            version=self.version,
            tags=self.tags,
        )

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the tool with the given keyword arguments.

        Args:
            **kwargs: Tool-specific parameters validated against input_schema.

        Returns:
            Dict with the tool's result data.

        Raises:
            Exception: Any exception is caught and wrapped in MCPToolResult.
        """

    async def safe_execute(self, **kwargs: Any) -> MCPToolResult:
        """
        Execute the tool and wrap the result in a standardised envelope.

        Measures wall-clock execution time, catches all exceptions, and
        returns an ``MCPToolResult`` regardless of success or failure.

        Args:
            **kwargs: Tool-specific parameters.

        Returns:
            MCPToolResult with status "success" or "error".
        """
        start = time.monotonic()
        try:
            data = await self.execute(**kwargs)
            elapsed_ms = (time.monotonic() - start) * 1000.0
            return MCPToolResult(
                status="success",
                data=data,
                execution_time_ms=round(elapsed_ms, 2),
            )
        except QuantNanggroeAIError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            logger.error("MCP tool %s failed: [%s] %s", self.name, exc.code, exc.message)
            return MCPToolResult(
                status="error",
                error=exc.message,
                error_code=exc.code,
                execution_time_ms=round(elapsed_ms, 2),
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            logger.exception("MCP tool %s failed with unexpected error", self.name)
            return MCPToolResult(
                status="error",
                error=str(exc),
                error_code="UNEXPECTED_ERROR",
                execution_time_ms=round(elapsed_ms, 2),
            )


# ══════════════════════════════════════════════════════════════════════
# Built-in MCP Tools
# ══════════════════════════════════════════════════════════════════════


class MarketDataMCPTool(MCPTool):
    """
    MCP tool for market data access — OHLCV, current prices, batch fetch.

    Wraps ``quant_nanggroe_ai.agents.tools.market_data.MarketDataTool``
    and exposes its methods through the MCP protocol.
    """

    @property
    def name(self) -> str:
        return "market_data"

    @property
    def description(self) -> str:
        return (
            "Access market data including OHLCV candles, current prices, "
            "and batch price fetches for stocks, crypto, and forex."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_ohlcv", "get_current_price", "get_multiple_prices"],
                    "description": "The market data action to perform.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol (e.g. 'AAPL', 'BTC/USDT', 'EURUSD=X').",
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of symbols for batch price fetch.",
                },
                "timeframe": {
                    "type": "string",
                    "enum": ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"],
                    "default": "1d",
                    "description": "Candle interval.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 200,
                    "description": "Number of candles to return.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["market-data", "ohlcv", "prices", "read-only"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a market data action.

        Args:
            action: One of 'get_ohlcv', 'get_current_price', 'get_multiple_prices'.
            symbol: Ticker symbol (required for get_ohlcv, get_current_price).
            symbols: List of tickers (required for get_multiple_prices).
            timeframe: Candle interval (default '1d').
            limit: Number of candles (default 200).

        Returns:
            Market data dict from the underlying tool.

        Raises:
            AgentError: If required parameters are missing or the action is invalid.
        """
        from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool

        action = kwargs.get("action")
        if not action:
            raise AgentError("'action' is required for market_data tool")

        tool = MarketDataTool()

        if action == "get_ohlcv":
            symbol = kwargs.get("symbol")
            if not symbol:
                raise AgentError("'symbol' is required for get_ohlcv action")
            timeframe = kwargs.get("timeframe", "1d")
            limit = int(kwargs.get("limit", 200))
            return await tool.get_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)

        elif action == "get_current_price":
            symbol = kwargs.get("symbol")
            if not symbol:
                raise AgentError("'symbol' is required for get_current_price action")
            return await tool.get_current_price(symbol=symbol)

        elif action == "get_multiple_prices":
            symbols = kwargs.get("symbols")
            if not symbols or not isinstance(symbols, list):
                raise AgentError("'symbols' (list) is required for get_multiple_prices action")
            return await tool.get_multiple_prices(symbols=symbols)

        else:
            raise AgentError(f"Unknown market_data action: '{action}'")


class TradingMCPTool(MCPTool):
    """
    MCP tool for trade execution — place orders, manage positions, account.

    Wraps ``quant_nanggroe_ai.agents.tools.execution.ExecutionTool``
    through the MCP protocol.
    """

    @property
    def name(self) -> str:
        return "trading"

    @property
    def description(self) -> str:
        return (
            "Execute trades, cancel orders, query order status, and "
            "retrieve account summaries. Supports MARKET and LIMIT orders."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "execute_order",
                        "cancel_order",
                        "get_order_status",
                        "get_open_orders",
                        "get_account_summary",
                    ],
                    "description": "The trading action to perform.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol for the order.",
                },
                "side": {
                    "type": "string",
                    "enum": ["BUY", "SELL", "LONG", "SHORT"],
                    "description": "Order direction.",
                },
                "quantity": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Number of shares/units to trade.",
                },
                "order_type": {
                    "type": "string",
                    "enum": ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"],
                    "default": "MARKET",
                    "description": "Order type.",
                },
                "price": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Limit price (required for LIMIT orders).",
                },
                "stop_loss": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Stop-loss price.",
                },
                "take_profit": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Take-profit price.",
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID for cancel/status queries.",
                },
                "symbol_type": {
                    "type": "string",
                    "enum": ["stock", "crypto", "forex"],
                    "default": "stock",
                    "description": "Asset type for account summary.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["trading", "execution", "orders", "write"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a trading action.

        Args:
            action: One of the supported trading actions.
            symbol: Ticker symbol (for execute_order).
            side: Order direction (for execute_order).
            quantity: Trade size (for execute_order).
            order_type: Order type string (default MARKET).
            price: Limit price.
            stop_loss: Stop-loss price.
            take_profit: Take-profit price.
            order_id: Order identifier (for cancel/status).
            symbol_type: Asset class (for account summary).

        Returns:
            Trading result dict from the underlying ExecutionTool.

        Raises:
            AgentError: If required parameters are missing.
        """
        from quant_nanggroe_ai.agents.tools.execution import ExecutionTool

        action = kwargs.get("action")
        if not action:
            raise AgentError("'action' is required for trading tool")

        tool = ExecutionTool()

        if action == "execute_order":
            symbol = kwargs.get("symbol")
            side = kwargs.get("side")
            quantity = kwargs.get("quantity")
            if not symbol or not side or quantity is None:
                raise AgentError(
                    "'symbol', 'side', and 'quantity' are required for execute_order"
                )
            return await tool.execute_order(
                symbol=symbol,
                side=str(side),
                quantity=float(quantity),
                order_type=str(kwargs.get("order_type", "MARKET")),
                price=float(kwargs["price"]) if "price" in kwargs else None,
                stop_loss=float(kwargs["stop_loss"]) if "stop_loss" in kwargs else None,
                take_profit=float(kwargs["take_profit"]) if "take_profit" in kwargs else None,
            )

        elif action == "cancel_order":
            order_id = kwargs.get("order_id")
            if not order_id:
                raise AgentError("'order_id' is required for cancel_order")
            return await tool.cancel_order(order_id=str(order_id))

        elif action == "get_order_status":
            order_id = kwargs.get("order_id")
            if not order_id:
                raise AgentError("'order_id' is required for get_order_status")
            return await tool.get_order_status(order_id=str(order_id))

        elif action == "get_open_orders":
            symbol = kwargs.get("symbol")
            orders = await tool.get_open_orders(symbol=symbol)
            return {"orders": orders, "count": len(orders)}

        elif action == "get_account_summary":
            symbol_type = kwargs.get("symbol_type", "stock")
            return await tool.get_account_summary(symbol_type=str(symbol_type))

        else:
            raise AgentError(f"Unknown trading action: '{action}'")


class RiskMCPTool(MCPTool):
    """
    MCP tool for risk management — check risk status, portfolio risk.

    Wraps ``quant_nanggroe_ai.engine.risk_guard.ConstitutionalRiskGuard``
    through the MCP protocol, providing risk checkpoint evaluation and
    status queries.
    """

    @property
    def name(self) -> str:
        return "risk"

    @property
    def description(self) -> str:
        return (
            "Check risk status, evaluate trades through the 9-checkpoint "
            "system, query daily/weekly PnL limits, and review risk constitution."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "check_trade",
                        "get_status",
                        "get_constitution",
                        "reset_daily",
                        "reset_weekly",
                    ],
                    "description": "The risk action to perform.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol for trade check.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["BUY", "SELL", "LONG", "SHORT"],
                    "description": "Trade direction for risk check.",
                },
                "lot_size": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Position size for risk evaluation.",
                },
                "entry": {
                    "type": "number",
                    "description": "Entry price for risk evaluation.",
                },
                "stop_loss": {
                    "type": "number",
                    "description": "Stop-loss price.",
                },
                "take_profit": {
                    "type": "number",
                    "description": "Take-profit price.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["risk", "risk-guard", "read-only", "safety"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a risk management action.

        Args:
            action: One of the supported risk actions.
            symbol, direction, lot_size, entry, stop_loss, take_profit:
                Parameters for the 'check_trade' action.

        Returns:
            Risk evaluation dict.

        Raises:
            AgentError: If required parameters are missing.
        """
        from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard

        action = kwargs.get("action")
        if not action:
            raise AgentError("'action' is required for risk tool")

        guard = ConstitutionalRiskGuard()

        if action == "check_trade":
            symbol = kwargs.get("symbol")
            direction = kwargs.get("direction")
            lot_size = kwargs.get("lot_size")
            entry = kwargs.get("entry")
            if not symbol or not direction or lot_size is None or entry is None:
                raise AgentError(
                    "'symbol', 'direction', 'lot_size', and 'entry' "
                    "are required for check_trade"
                )
            result = guard.check_trade(
                symbol=str(symbol),
                direction=str(direction),
                lot_size=float(lot_size),
                entry=float(entry),
                stop_loss=float(kwargs["stop_loss"]) if "stop_loss" in kwargs else None,
                take_profit=float(kwargs["take_profit"]) if "take_profit" in kwargs else None,
            )
            return {
                "verdict": result.verdict,
                "risk_pct": result.risk_pct,
                "checkpoints": {k: v.model_dump() for k, v in result.checkpoints.items()},
                "veto_count_total": result.veto_count_total,
                "approval_count_total": result.approval_count_total,
                "timestamp": result.timestamp.isoformat(),
            }

        elif action == "get_status":
            return guard.get_status()

        elif action == "get_constitution":
            return guard.get_constitution().model_dump()

        elif action == "reset_daily":
            guard.reset_daily()
            return {"status": "daily_counters_reset"}

        elif action == "reset_weekly":
            guard.reset_weekly()
            return {"status": "weekly_counters_reset"}

        else:
            raise AgentError(f"Unknown risk action: '{action}'")


class BacktestMCPTool(MCPTool):
    """
    MCP tool for backtesting — run backtests, retrieve results.

    Wraps ``quant_nanggroe_ai.agents.tools.backtest.BacktestTool``
    through the MCP protocol.
    """

    @property
    def name(self) -> str:
        return "backtest"

    @property
    def description(self) -> str:
        return (
            "Run strategy backtests (SMA crossover, RSI mean-revert, or "
            "custom), retrieve stored results, and list past backtests."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["run", "get_results", "list"],
                    "description": "The backtest action to perform.",
                },
                "strategy": {
                    "type": "string",
                    "description": "Strategy name (e.g. 'sma_crossover', 'rsi_mean_revert').",
                },
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol to backtest.",
                },
                "timeframe": {
                    "type": "string",
                    "default": "1d",
                    "description": "Candle interval.",
                },
                "start_date": {
                    "type": "string",
                    "default": "2023-01-01",
                    "description": "Backtest start date (YYYY-MM-DD).",
                },
                "end_date": {
                    "type": "string",
                    "default": "2024-01-01",
                    "description": "Backtest end date (YYYY-MM-DD).",
                },
                "initial_capital": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "default": 10000.0,
                    "description": "Starting capital.",
                },
                "commission": {
                    "type": "number",
                    "minimum": 0,
                    "default": 0.001,
                    "description": "Commission rate per trade.",
                },
                "slippage_bps": {
                    "type": "number",
                    "minimum": 0,
                    "default": 5.0,
                    "description": "Slippage in basis points.",
                },
                "strategy_params": {
                    "type": "object",
                    "description": "Additional strategy parameters.",
                },
                "backtest_id": {
                    "type": "string",
                    "description": "Backtest ID for result retrieval.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["backtest", "simulation", "read-only"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a backtest action.

        Args:
            action: 'run', 'get_results', or 'list'.
            strategy, symbol, etc.: Parameters for 'run' action.
            backtest_id: ID for 'get_results' action.

        Returns:
            Backtest result or summary dict.

        Raises:
            AgentError: If required parameters are missing.
        """
        from quant_nanggroe_ai.agents.tools.backtest import BacktestTool
        from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool

        action = kwargs.get("action")
        if not action:
            raise AgentError("'action' is required for backtest tool")

        # Each invocation creates a fresh tool with a market data source.
        # In production, a shared MarketDataTool would be injected via MCPServer.
        mdt = MarketDataTool()
        tool = BacktestTool(market_data_tool=mdt)

        if action == "run":
            strategy = kwargs.get("strategy")
            symbol = kwargs.get("symbol")
            if not strategy or not symbol:
                raise AgentError("'strategy' and 'symbol' are required for run action")
            return await tool.run_backtest(
                strategy=str(strategy),
                symbol=str(symbol),
                timeframe=str(kwargs.get("timeframe", "1d")),
                start_date=str(kwargs.get("start_date", "2023-01-01")),
                end_date=str(kwargs.get("end_date", "2024-01-01")),
                initial_capital=float(kwargs.get("initial_capital", 10000.0)),
                commission=float(kwargs.get("commission", 0.001)),
                slippage_bps=float(kwargs.get("slippage_bps", 5.0)),
                strategy_params=kwargs.get("strategy_params"),
            )

        elif action == "get_results":
            backtest_id = kwargs.get("backtest_id")
            if not backtest_id:
                raise AgentError("'backtest_id' is required for get_results action")
            return await tool.get_backtest_results(backtest_id=str(backtest_id))

        elif action == "list":
            results = await tool.list_backtests()
            return {"backtests": results, "count": len(results)}

        else:
            raise AgentError(f"Unknown backtest action: '{action}'")


class ResearchMCPTool(MCPTool):
    """
    MCP tool for research and memory — sentiment analysis, search.

    Wraps ``quant_nanggroe_ai.agents.tools.sentiment.SentimentTool``
    and provides an in-memory research memory store for cross-session
    knowledge persistence.
    """

    def __init__(self) -> None:
        self._memory: dict[str, dict[str, Any]] = {}
        self._memory_timestamps: dict[str, float] = {}

    @property
    def name(self) -> str:
        return "research"

    @property
    def description(self) -> str:
        return (
            "Conduct research via sentiment analysis, store and retrieve "
            "research notes in memory, and search across stored entries."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "analyze_sentiment",
                        "memory_store",
                        "memory_retrieve",
                        "memory_search",
                        "memory_list",
                        "memory_delete",
                    ],
                    "description": "The research action to perform.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol for sentiment analysis.",
                },
                "key": {
                    "type": "string",
                    "description": "Memory key for store/retrieve/delete.",
                },
                "value": {
                    "type": "object",
                    "description": "Value to store in memory.",
                },
                "query": {
                    "type": "string",
                    "description": "Search query for memory_search.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for memory entry.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["research", "sentiment", "memory", "search"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute a research action.

        Args:
            action: The research action to perform.
            symbol: Ticker for sentiment analysis.
            key: Memory key for store/retrieve/delete.
            value: Data to store.
            query: Search text for memory search.
            tags: Tags for the memory entry.

        Returns:
            Research result dict.

        Raises:
            AgentError: If required parameters are missing.
        """
        action = kwargs.get("action")
        if not action:
            raise AgentError("'action' is required for research tool")

        if action == "analyze_sentiment":
            from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool

            symbol = kwargs.get("symbol")
            if not symbol:
                raise AgentError("'symbol' is required for analyze_sentiment")
            tool = SentimentTool()
            return await tool.analyze(symbol=str(symbol))

        elif action == "memory_store":
            key = kwargs.get("key")
            value = kwargs.get("value")
            if not key or value is None:
                raise AgentError("'key' and 'value' are required for memory_store")
            tags = kwargs.get("tags", [])
            entry = {
                "value": value,
                "tags": tags,
                "stored_at": datetime.now(timezone.utc).isoformat(),
            }
            self._memory[str(key)] = entry
            self._memory_timestamps[str(key)] = time.monotonic()
            return {"status": "stored", "key": str(key)}

        elif action == "memory_retrieve":
            key = kwargs.get("key")
            if not key:
                raise AgentError("'key' is required for memory_retrieve")
            entry = self._memory.get(str(key))
            if entry is None:
                return {"status": "not_found", "key": str(key)}
            return {"status": "found", "key": str(key), **entry}

        elif action == "memory_search":
            query = kwargs.get("query", "")
            query_lower = query.lower()
            results: list[dict[str, Any]] = []
            for mem_key, entry in self._memory.items():
                # Search in key and value text
                searchable = f"{mem_key} {str(entry.get('value', ''))} {' '.join(entry.get('tags', []))}".lower()
                if query_lower in searchable:
                    results.append({"key": mem_key, **entry})
            return {
                "results": results,
                "count": len(results),
                "query": query,
            }

        elif action == "memory_list":
            entries = [
                {"key": k, "tags": v.get("tags", []), "stored_at": v.get("stored_at")}
                for k, v in self._memory.items()
            ]
            return {"entries": entries, "count": len(entries)}

        elif action == "memory_delete":
            key = kwargs.get("key")
            if not key:
                raise AgentError("'key' is required for memory_delete")
            if str(key) in self._memory:
                del self._memory[str(key)]
                self._memory_timestamps.pop(str(key), None)
                return {"status": "deleted", "key": str(key)}
            return {"status": "not_found", "key": str(key)}

        else:
            raise AgentError(f"Unknown research action: '{action}'")


# ══════════════════════════════════════════════════════════════════════
# MCPServer — Serves tools via MCP protocol
# ══════════════════════════════════════════════════════════════════════


class MCPServer:
    """
    MCP Server — Central registry and dispatcher for MCP tools.

    The server maintains a registry of ``MCPTool`` instances and provides:
      - ``register_tool``: Add a tool to the registry
      - ``list_tools``: Discover all available tools
      - ``call_tool``: Invoke a tool by name with arguments
      - ``get_tool_schema``: Retrieve a tool's JSON Schema

    Includes an audit log of all tool invocations and supports optional
    middleware (pre/post hooks) for cross-cutting concerns like logging,
    rate-limiting, and authentication.

    Usage::

        server = MCPServer()
        server.register_tool(MarketDataMCPTool())
        server.register_tool(TradingMCPTool())

        # Discover tools
        tools = server.list_tools()

        # Invoke a tool
        result = await server.call_tool(
            "market_data",
            action="get_ohlcv",
            symbol="AAPL",
            timeframe="1d",
        )
    """

    def __init__(
        self,
        max_audit_records: int = 1000,
        middleware: list[Callable[..., Coroutine[Any, Any, None]]] | None = None,
    ) -> None:
        """
        Initialize the MCP Server.

        Args:
            max_audit_records: Maximum number of audit records to retain
                (oldest are evicted when the limit is reached).
            middleware: Optional list of async middleware callables that
                are invoked before each tool call. Each receives the
                tool_name and kwargs.
        """
        self._tools: dict[str, MCPTool] = {}
        self._audit_log: list[MCPToolCallRecord] = []
        self._max_audit = max_audit_records
        self._middleware = middleware or []
        self._caller_id: str | None = None

    # ── Tool registration ────────────────────────────────────────────

    def register_tool(self, tool: MCPTool) -> None:
        """
        Register an MCP tool with the server.

        If a tool with the same name already exists, it is replaced.

        Args:
            tool: An MCPTool instance to register.

        Raises:
            TypeError: If *tool* is not an MCPTool subclass.
        """
        if not isinstance(tool, MCPTool):
            raise TypeError(f"Expected MCPTool instance, got {type(tool).__name__}")
        self._tools[tool.name] = tool
        logger.info("MCP tool registered: %s", tool.name)

    def unregister_tool(self, name: str) -> bool:
        """
        Remove a tool from the registry by name.

        Args:
            name: The tool name to unregister.

        Returns:
            True if the tool was found and removed, False otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("MCP tool unregistered: %s", name)
            return True
        return False

    # ── Tool discovery ───────────────────────────────────────────────

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all registered tools with their metadata.

        Returns:
            List of dicts, each containing 'name', 'description',
            'input_schema', 'output_schema', 'version', and 'tags'.
        """
        return [
            {
                "name": meta.name,
                "description": meta.description,
                "input_schema": meta.input_schema,
                "output_schema": meta.output_schema,
                "version": meta.version,
                "tags": meta.tags,
            }
            for meta in (
                self._tools[name].get_metadata() for name in sorted(self._tools)
            )
        ]

    def get_tool_schema(self, name: str) -> dict[str, Any]:
        """
        Retrieve the JSON Schema for a specific tool's input.

        Args:
            name: The tool name.

        Returns:
            Dict with 'name', 'input_schema', 'output_schema', 'version'.

        Raises:
            AgentError: If the tool is not registered.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise AgentError(f"MCP tool not found: '{name}'")
        meta = tool.get_metadata()
        return {
            "name": meta.name,
            "input_schema": meta.input_schema,
            "output_schema": meta.output_schema,
            "version": meta.version,
        }

    # ── Tool invocation ──────────────────────────────────────────────

    async def call_tool(self, name: str, **kwargs: Any) -> MCPToolResult:
        """
        Invoke a registered tool by name.

        Runs any registered middleware, then delegates to the tool's
        ``safe_execute`` method, and records the call in the audit log.

        Args:
            name: The registered tool name.
            **kwargs: Arguments to pass to the tool's ``execute`` method.

        Returns:
            MCPToolResult envelope with status, data, and timing.

        Raises:
            AgentError: If the tool is not registered.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise AgentError(f"MCP tool not found: '{name}'")

        # Run middleware
        for mw in self._middleware:
            try:
                await mw(tool_name=name, **kwargs)
            except Exception as exc:
                logger.warning("Middleware error for tool %s: %s", name, exc)

        # Execute
        result = await tool.safe_execute(**kwargs)

        # Audit record
        record = MCPToolCallRecord(
            tool_name=name,
            arguments=kwargs,
            result_status=result.status,
            execution_time_ms=result.execution_time_ms,
            timestamp=result.timestamp,
            caller_id=self._caller_id,
        )
        self._audit_log.append(record)
        # Evict oldest if at capacity
        if len(self._audit_log) > self._max_audit:
            self._audit_log = self._audit_log[-self._max_audit:]

        return result

    # ── Caller context ───────────────────────────────────────────────

    def set_caller(self, caller_id: str | None) -> None:
        """
        Set the caller identity for audit logging.

        Args:
            caller_id: Identifier for the calling model/agent.
        """
        self._caller_id = caller_id

    # ── Audit log ────────────────────────────────────────────────────

    def get_audit_log(
        self,
        tool_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve audit log entries, optionally filtered by tool name.

        Args:
            tool_name: If provided, only return entries for this tool.
            limit: Maximum number of entries to return (most recent first).

        Returns:
            List of audit record dicts.
        """
        records = self._audit_log
        if tool_name is not None:
            records = [r for r in records if r.tool_name == tool_name]
        # Return most recent first
        records = list(reversed(records[-limit:]))
        return [r.model_dump() for r in records]

    # ── Convenience: register all built-in tools ─────────────────────

    def register_default_tools(self) -> None:
        """
        Register all built-in MCP tools: market_data, trading, risk,
        backtest, and research.

        This is a convenience method for quick setup. Individual tools
        can still be registered or unregistered afterwards.
        """
        self.register_tool(MarketDataMCPTool())
        self.register_tool(TradingMCPTool())
        self.register_tool(RiskMCPTool())
        self.register_tool(BacktestMCPTool())
        self.register_tool(ResearchMCPTool())
        logger.info("All default MCP tools registered")


# ══════════════════════════════════════════════════════════════════════
# Module-level helpers
# ══════════════════════════════════════════════════════════════════════

# Singleton MCPServer for application-wide use
_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    """
    Return the module-level MCPServer singleton.

    Lazily creates and populates the server with default tools on
    first access.

    Returns:
        The shared MCPServer instance.
    """
    global _server
    if _server is None:
        _server = MCPServer()
        _server.register_default_tools()
    return _server


def reset_mcp_server() -> None:
    """Reset the module-level MCPServer singleton (useful for testing)."""
    global _server
    _server = None
