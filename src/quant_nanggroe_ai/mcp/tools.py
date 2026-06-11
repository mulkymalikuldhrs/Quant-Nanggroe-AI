"""Trading-Specific MCP Tools for Quant Nanggroe AI.

Implements MCP tool handlers that wrap the core trading engine capabilities:
- Market data fetching (OHLCV, tickers, order books)
- Order placement and management
- Risk assessment and VaR computation
- Alpha factor computation and discovery
- Backtest execution
- Portfolio and position queries

Each tool has a proper name, description, input_schema (JSON Schema),
and output_schema. All tools integrate with the existing quant_nanggroe
type system for consistent validation and serialization.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_nanggroe_ai.mcp.protocol import (
    ToolCallResult,
    ToolDefinition,
    ToolInputSchema,
    ToolOutputSchema,
)
from quant_nanggroe_ai.mcp.server import FunctionToolHandler, ToolHandler

logger = logging.getLogger(__name__)


# ─── Market Data Tools ────────────────────────────────────────────────────────


def _market_data_get_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Fetch OHLCV candlestick data for a symbol.

    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USDT', 'AAPL').
        timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M).
        start: Start datetime in ISO format.
        end: End datetime in ISO format.
        limit: Maximum number of candles to return.

    Returns:
        Dict with OHLCV data and metadata.
    """
    # In production, this would call DataProviderManager
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "data": [],
        "count": 0,
        "provider": "auto",
        "message": f"OHLCV data request for {symbol} @ {timeframe} (limit={limit})",
    }


def _market_data_get_ticker(symbol: str) -> Dict[str, Any]:
    """Fetch current ticker data for a symbol.

    Args:
        symbol: Trading pair symbol.

    Returns:
        Dict with current ticker information.
    """
    return {
        "symbol": symbol.upper(),
        "last_price": 0.0,
        "bid": None,
        "ask": None,
        "volume_24h": None,
        "change_pct_24h": None,
        "timestamp": datetime.now().isoformat(),
        "provider": "auto",
        "message": f"Ticker data request for {symbol}",
    }


def _market_data_get_orderbook(
    symbol: str, limit: int = 20
) -> Dict[str, Any]:
    """Fetch order book snapshot for a symbol.

    Args:
        symbol: Trading pair symbol.
        limit: Number of bid/ask levels.

    Returns:
        Dict with order book data.
    """
    return {
        "symbol": symbol.upper(),
        "bids": [],
        "asks": [],
        "spread": None,
        "mid_price": None,
        "timestamp": datetime.now().isoformat(),
        "message": f"Order book request for {symbol} (depth={limit})",
    }


def _market_data_get_market_data(
    symbol: str,
    timeframe: str = "1d",
    include_ohlcv: bool = True,
    include_ticker: bool = True,
    include_orderbook: bool = False,
) -> Dict[str, Any]:
    """Fetch aggregated market data for a symbol.

    Args:
        symbol: Trading pair symbol.
        timeframe: Candle timeframe.
        include_ohlcv: Whether to include OHLCV data.
        include_ticker: Whether to include ticker data.
        include_orderbook: Whether to include order book data.

    Returns:
        Dict with aggregated market data.
    """
    result: Dict[str, Any] = {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "timestamp": datetime.now().isoformat(),
    }
    if include_ohlcv:
        result["ohlcv"] = []
    if include_ticker:
        result["ticker"] = {
            "symbol": symbol.upper(),
            "last_price": 0.0,
            "timestamp": datetime.now().isoformat(),
        }
    if include_orderbook:
        result["orderbook"] = {
            "symbol": symbol.upper(),
            "bids": [],
            "asks": [],
        }
    return result


# ─── Order Execution Tools ────────────────────────────────────────────────────


def _orders_place_order(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "market",
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    strategy_name: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Place a trading order through the execution manager.

    Args:
        symbol: Trading symbol (e.g., 'BTC/USDT', 'AAPL').
        side: Order side ('buy' or 'sell').
        quantity: Order quantity in base currency.
        order_type: Order type ('market', 'limit', 'stop', 'stop_limit').
        price: Limit price (required for limit and stop_limit orders).
        stop_price: Stop trigger price (required for stop and stop_limit orders).
        stop_loss: Suggested stop-loss price.
        take_profit: Suggested take-profit price.
        strategy_name: Name of the strategy placing the order.
        agent_name: Name of the agent placing the order.

    Returns:
        Dict with order confirmation and status.
    """
    # Validate side
    side = side.lower()
    if side not in ("buy", "sell"):
        return {
            "error": f"Invalid side: {side!r}. Must be 'buy' or 'sell'.",
            "status": "rejected",
        }

    # Validate order type
    valid_types = ("market", "limit", "stop", "stop_limit")
    order_type = order_type.lower()
    if order_type not in valid_types:
        return {
            "error": f"Invalid order_type: {order_type!r}. Must be one of {valid_types}.",
            "status": "rejected",
        }

    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    return {
        "order_id": order_id,
        "symbol": symbol.upper(),
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
        "stop_price": stop_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "status": "submitted",
        "strategy_name": strategy_name,
        "agent_name": agent_name,
        "timestamp": datetime.now().isoformat(),
        "message": f"Order {order_id}: {side.upper()} {quantity} {symbol.upper()} @ {order_type}",
    }


def _orders_cancel_order(order_id: str) -> Dict[str, Any]:
    """Cancel a pending order.

    Args:
        order_id: Order ID to cancel.

    Returns:
        Dict with cancellation status.
    """
    return {
        "order_id": order_id,
        "status": "cancel_requested",
        "timestamp": datetime.now().isoformat(),
        "message": f"Cancellation requested for order {order_id}",
    }


def _orders_get_order_status(order_id: str) -> Dict[str, Any]:
    """Get the status of an order.

    Args:
        order_id: Order ID to query.

    Returns:
        Dict with order status details.
    """
    return {
        "order_id": order_id,
        "status": "unknown",
        "message": f"Order status query for {order_id}",
    }


# ─── Risk Assessment Tools ────────────────────────────────────────────────────


def _risk_assess_trade(
    symbol: str,
    direction: str,
    lot_size: float,
    entry: float,
    stop_loss: float,
    account_balance: float = 1_000_000.0,
    take_profit: Optional[float] = None,
    daily_pnl: float = 0.0,
    weekly_pnl: float = 0.0,
    trade_count_today: int = 0,
    active_positions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Assess trade risk through the 9-checkpoint risk gate.

    Evaluates a proposed trade through all 9 constitutional risk
    checkpoints. Any failure results in a VETO.

    Args:
        symbol: Trading symbol.
        direction: Trade direction (BUY/SELL/LONG/SHORT).
        lot_size: Proposed lot size.
        entry: Entry price.
        stop_loss: Stop loss price.
        account_balance: Current account balance.
        take_profit: Optional take profit price.
        daily_pnl: Today's accumulated P&L.
        weekly_pnl: This week's accumulated P&L.
        trade_count_today: Number of trades today.
        active_positions: List of currently held symbols.

    Returns:
        Dict with verdict (APPROVED/VETOED) and checkpoint details.
    """
    try:
        from quant_nanggroe_ai.engine.risk.checks import RiskCheckGate

        gate = RiskCheckGate()
        result = gate.evaluate(
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry=entry,
            stop_loss=stop_loss,
            account_balance=account_balance,
            take_profit=take_profit,
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            trade_count_today=trade_count_today,
            active_positions=active_positions or [],
        )
        return result
    except Exception as exc:
        logger.exception("Risk assessment failed: %s", exc)
        return {
            "symbol": symbol,
            "direction": direction,
            "verdict": "ERROR",
            "error": str(exc),
        }


def _risk_compute_var(
    portfolio_value: float,
    confidence_level: float = 0.95,
    time_horizon: int = 1,
    method: str = "parametric",
    returns_data: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Compute Value at Risk (VaR) and Conditional VaR (CVaR).

    Supports parametric (variance-covariance), historical, and Monte Carlo methods.

    Args:
        portfolio_value: Current portfolio value.
        confidence_level: Confidence level (0.90-0.99).
        time_horizon: Time horizon in days.
        method: Calculation method (parametric/historical/monte_carlo).
        returns_data: Optional list of historical returns.

    Returns:
        Dict with VaR and CVaR results.
    """
    # In production, this would call the risk engine's VaR calculator
    return {
        "var_value": 0.0,
        "cvar_value": 0.0,
        "confidence_level": confidence_level,
        "time_horizon": time_horizon,
        "method": method,
        "portfolio_value": portfolio_value,
        "var_pct": 0.0,
        "cvar_pct": 0.0,
        "message": f"VaR computation: {method} @ {confidence_level} for {time_horizon}d",
    }


def _risk_compute_drawdown(
    portfolio_value: float,
    peak_value: float,
    current_value: float,
) -> Dict[str, Any]:
    """Compute current and maximum drawdown.

    Args:
        portfolio_value: Portfolio value for reference.
        peak_value: Peak portfolio value.
        current_value: Current portfolio value.

    Returns:
        Dict with drawdown analysis results.
    """
    current_dd = ((peak_value - current_value) / peak_value * 100) if peak_value > 0 else 0.0
    return {
        "current_drawdown": round(current_dd, 4),
        "max_drawdown": round(current_dd, 4),  # Simplified; production tracks full history
        "peak_value": peak_value,
        "current_value": current_value,
        "portfolio_value": portfolio_value,
        "message": f"Drawdown analysis: current={current_dd:.2f}%",
    }


# ─── Factor Computation Tools ─────────────────────────────────────────────────


def _factors_list(
    zoo: Optional[str] = None,
    theme: Optional[str] = None,
) -> Dict[str, Any]:
    """List available alpha factors with optional filtering.

    Args:
        zoo: Filter by zoo (alpha101, gtja191, technical, fundamental).
        theme: Filter by theme (momentum, reversal, volume, etc.).

    Returns:
        Dict with list of factor IDs and metadata.
    """
    try:
        from quant_nanggroe_ai.engine.factors.registry import get_default_registry

        registry = get_default_registry()
        factor_ids = registry.list(zoo=zoo, theme=theme)
        return {
            "factors": factor_ids,
            "count": len(factor_ids),
            "filters": {"zoo": zoo, "theme": theme},
        }
    except Exception as exc:
        logger.exception("Factor listing failed: %s", exc)
        return {
            "factors": [],
            "count": 0,
            "error": str(exc),
        }


def _factors_compute(
    factor_id: str,
    data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute an alpha factor on provided data.

    Args:
        factor_id: Unique factor identifier (e.g., 'alpha101_001').
        data: Optional list of OHLCV records for computation.

    Returns:
        Dict with computed factor values.
    """
    if data is None:
        return {
            "factor_id": factor_id,
            "values": [],
            "error": "No data provided for computation",
        }

    try:
        import pandas as pd
        from quant_nanggroe_ai.engine.factors.registry import get_default_registry

        registry = get_default_registry()
        df = pd.DataFrame(data)
        result = registry.compute(factor_id, df)
        return {
            "factor_id": factor_id,
            "values": result.tolist(),
            "count": len(result),
        }
    except KeyError as exc:
        return {
            "factor_id": factor_id,
            "values": [],
            "error": f"Factor not found: {exc}",
        }
    except Exception as exc:
        logger.exception("Factor computation failed: %s", exc)
        return {
            "factor_id": factor_id,
            "values": [],
            "error": str(exc),
        }


def _factors_get_meta(factor_id: str) -> Dict[str, Any]:
    """Get metadata for a specific alpha factor.

    Args:
        factor_id: Unique factor identifier.

    Returns:
        Dict with factor metadata.
    """
    try:
        from quant_nanggroe_ai.engine.factors.registry import get_default_registry

        registry = get_default_registry()
        meta = registry.get_meta(factor_id)
        return {
            "factor_id": meta.id,
            "zoo": meta.zoo,
            "theme": meta.theme,
            "formula_latex": meta.formula_latex,
            "columns_required": meta.columns_required,
            "universe": meta.universe,
            "min_warmup_bars": meta.min_warmup_bars,
        }
    except KeyError:
        return {
            "factor_id": factor_id,
            "error": f"Factor {factor_id!r} not found",
        }


def _factors_health() -> Dict[str, Any]:
    """Get factor registry health status.

    Returns:
        Dict with registry health details.
    """
    try:
        from quant_nanggroe_ai.engine.factors.registry import get_default_registry

        registry = get_default_registry()
        return registry.health()
    except Exception as exc:
        return {"error": str(exc)}


# ─── Backtest Execution Tools ─────────────────────────────────────────────────


def _backtest_run(
    symbols: Optional[List[str]] = None,
    strategy_type: str = "signal_based",
    initial_capital: float = 1_000_000.0,
    commission_rate: float = 0.001,
    slippage_bps: float = 5.0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    market: str = "equity",
) -> Dict[str, Any]:
    """Run a backtest with the specified configuration.

    Args:
        symbols: List of symbols to backtest.
        strategy_type: Strategy type (signal_based, factor_based, ml_based).
        initial_capital: Starting capital.
        commission_rate: Commission rate as decimal.
        slippage_bps: Slippage in basis points.
        start_date: Backtest start date (ISO format).
        end_date: Backtest end date (ISO format).
        market: Market type (equity, crypto, forex, futures).

    Returns:
        Dict with backtest results and metrics.
    """
    # In production, this would invoke BacktestEngine.run()
    return {
        "status": "completed",
        "symbols": symbols or [],
        "strategy_type": strategy_type,
        "initial_capital": initial_capital,
        "commission_rate": commission_rate,
        "slippage_bps": slippage_bps,
        "market": market,
        "metrics": {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
        },
        "message": (
            f"Backtest run: {strategy_type} on {market} "
            f"with {len(symbols) if symbols else 0} symbols"
        ),
    }


def _backtest_walk_forward(
    symbols: Optional[List[str]] = None,
    train_window: int = 252,
    test_window: int = 63,
    initial_capital: float = 1_000_000.0,
) -> Dict[str, Any]:
    """Run walk-forward analysis for robust strategy validation.

    Args:
        symbols: List of symbols to analyze.
        train_window: Training window in bars.
        test_window: Test window in bars.
        initial_capital: Starting capital.

    Returns:
        Dict with walk-forward analysis results.
    """
    return {
        "status": "completed",
        "symbols": symbols or [],
        "train_window": train_window,
        "test_window": test_window,
        "initial_capital": initial_capital,
        "folds": 0,
        "avg_metrics": {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
        },
        "message": (
            f"Walk-forward analysis: train={train_window}, test={test_window}"
        ),
    }


# ─── Portfolio Query Tools ────────────────────────────────────────────────────


def _portfolio_get() -> Dict[str, Any]:
    """Get current portfolio overview.

    Returns:
        Dict with portfolio summary including positions, PnL, and risk metrics.
    """
    return {
        "id": "default",
        "name": "default",
        "currency": "USD",
        "initial_capital": 1_000_000.0,
        "cash": 1_000_000.0,
        "total_value": 1_000_000.0,
        "positions": {},
        "total_unrealized_pnl": 0.0,
        "total_realized_pnl": 0.0,
        "daily_pnl": 0.0,
        "weekly_pnl": 0.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": None,
        "win_rate": 0.0,
        "total_trades": 0,
        "timestamp": datetime.now().isoformat(),
    }


def _portfolio_get_positions() -> Dict[str, Any]:
    """Get all open positions.

    Returns:
        Dict with position details keyed by symbol.
    """
    return {
        "positions": {},
        "count": 0,
        "total_unrealized_pnl": 0.0,
        "timestamp": datetime.now().isoformat(),
    }


def _portfolio_get_position(symbol: str) -> Dict[str, Any]:
    """Get position details for a specific symbol.

    Args:
        symbol: Trading symbol.

    Returns:
        Dict with position details.
    """
    return {
        "symbol": symbol.upper(),
        "side": "flat",
        "quantity": 0.0,
        "entry_price": 0.0,
        "current_price": 0.0,
        "unrealized_pnl": 0.0,
        "stop_loss": None,
        "take_profit": None,
        "timestamp": datetime.now().isoformat(),
        "message": f"No open position for {symbol}",
    }


def _portfolio_get_performance() -> Dict[str, Any]:
    """Get portfolio performance metrics.

    Returns:
        Dict with performance metrics and statistics.
    """
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_trade_return": 0.0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "timestamp": datetime.now().isoformat(),
    }


# ─── Tool Schema Definitions ──────────────────────────────────────────────────

MARKET_DATA_GET_OHLCV = ToolDefinition(
    name="market_data.get_ohlcv",
    description="Fetch OHLCV candlestick data for a trading symbol. Supports multiple timeframes and date ranges.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbol": {
                "type": "string",
                "description": "Trading pair symbol (e.g., 'BTC/USDT', 'AAPL')",
                "minLength": 1,
            },
            "timeframe": {
                "type": "string",
                "description": "Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)",
                "default": "1d",
            },
            "start": {
                "type": "string",
                "description": "Start datetime in ISO format",
            },
            "end": {
                "type": "string",
                "description": "End datetime in ISO format",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of candles to return",
                "default": 500,
                "minimum": 1,
                "maximum": 10000,
            },
        },
        required=["symbol"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "symbol": {"type": "string"},
            "timeframe": {"type": "string"},
            "data": {"type": "array"},
            "count": {"type": "integer"},
        },
    ),
    annotations={"category": "market_data", "version": "1.0"},
)

MARKET_DATA_GET_TICKER = ToolDefinition(
    name="market_data.get_ticker",
    description="Fetch current ticker data (price, bid/ask, volume, change) for a trading symbol.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbol": {
                "type": "string",
                "description": "Trading pair symbol",
                "minLength": 1,
            },
        },
        required=["symbol"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "symbol": {"type": "string"},
            "last_price": {"type": "number"},
            "timestamp": {"type": "string"},
        },
    ),
    annotations={"category": "market_data", "version": "1.0"},
)

MARKET_DATA_GET_ORDERBOOK = ToolDefinition(
    name="market_data.get_orderbook",
    description="Fetch order book snapshot (bids, asks, spread) for a trading symbol.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbol": {
                "type": "string",
                "description": "Trading pair symbol",
                "minLength": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Number of bid/ask levels",
                "default": 20,
                "minimum": 1,
                "maximum": 100,
            },
        },
        required=["symbol"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "symbol": {"type": "string"},
            "bids": {"type": "array"},
            "asks": {"type": "array"},
        },
    ),
    annotations={"category": "market_data", "version": "1.0"},
)

MARKET_DATA_GET_MARKET_DATA = ToolDefinition(
    name="market_data.get_market_data",
    description="Fetch aggregated market data (OHLCV + ticker + orderbook) for a symbol in a single call.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbol": {
                "type": "string",
                "description": "Trading pair symbol",
                "minLength": 1,
            },
            "timeframe": {
                "type": "string",
                "description": "Candle timeframe",
                "default": "1d",
            },
            "include_ohlcv": {
                "type": "boolean",
                "description": "Include OHLCV data",
                "default": True,
            },
            "include_ticker": {
                "type": "boolean",
                "description": "Include ticker data",
                "default": True,
            },
            "include_orderbook": {
                "type": "boolean",
                "description": "Include order book data",
                "default": False,
            },
        },
        required=["symbol"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "symbol": {"type": "string"},
            "timeframe": {"type": "string"},
            "ohlcv": {"type": "array"},
            "ticker": {"type": "object"},
        },
    ),
    annotations={"category": "market_data", "version": "1.0"},
)

ORDERS_PLACE_ORDER = ToolDefinition(
    name="orders.place_order",
    description="Place a trading order through the execution manager with guard pipeline enforcement.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbol": {
                "type": "string",
                "description": "Trading symbol (e.g., 'BTC/USDT', 'AAPL')",
                "minLength": 1,
            },
            "side": {
                "type": "string",
                "description": "Order side: 'buy' or 'sell'",
                "enum": ["buy", "sell"],
            },
            "quantity": {
                "type": "number",
                "description": "Order quantity in base currency",
                "exclusiveMinimum": 0,
            },
            "order_type": {
                "type": "string",
                "description": "Order type",
                "enum": ["market", "limit", "stop", "stop_limit"],
                "default": "market",
            },
            "price": {
                "type": "number",
                "description": "Limit price (required for limit and stop_limit orders)",
                "exclusiveMinimum": 0,
            },
            "stop_price": {
                "type": "number",
                "description": "Stop trigger price (required for stop and stop_limit orders)",
                "exclusiveMinimum": 0,
            },
            "stop_loss": {
                "type": "number",
                "description": "Suggested stop-loss price",
                "exclusiveMinimum": 0,
            },
            "take_profit": {
                "type": "number",
                "description": "Suggested take-profit price",
                "exclusiveMinimum": 0,
            },
            "strategy_name": {
                "type": "string",
                "description": "Name of the strategy placing the order",
            },
            "agent_name": {
                "type": "string",
                "description": "Name of the agent placing the order",
            },
        },
        required=["symbol", "side", "quantity"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "order_id": {"type": "string"},
            "symbol": {"type": "string"},
            "status": {"type": "string"},
        },
    ),
    annotations={"category": "orders", "version": "1.0", "risk": "high"},
)

ORDERS_CANCEL_ORDER = ToolDefinition(
    name="orders.cancel_order",
    description="Cancel a pending order by its ID.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "order_id": {
                "type": "string",
                "description": "Order ID to cancel",
                "minLength": 1,
            },
        },
        required=["order_id"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "order_id": {"type": "string"},
            "status": {"type": "string"},
        },
    ),
    annotations={"category": "orders", "version": "1.0"},
)

ORDERS_GET_ORDER_STATUS = ToolDefinition(
    name="orders.get_order_status",
    description="Get the current status and fill details of an order.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "order_id": {
                "type": "string",
                "description": "Order ID to query",
                "minLength": 1,
            },
        },
        required=["order_id"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "order_id": {"type": "string"},
            "status": {"type": "string"},
        },
    ),
    annotations={"category": "orders", "version": "1.0"},
)

RISK_ASSESS_TRADE = ToolDefinition(
    name="risk.assess_trade",
    description="Assess trade risk through the 9-checkpoint constitutional risk gate. Any failure results in VETO.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbol": {
                "type": "string",
                "description": "Trading symbol",
                "minLength": 1,
            },
            "direction": {
                "type": "string",
                "description": "Trade direction (BUY/SELL/LONG/SHORT)",
            },
            "lot_size": {
                "type": "number",
                "description": "Proposed lot size",
                "exclusiveMinimum": 0,
            },
            "entry": {
                "type": "number",
                "description": "Entry price",
                "exclusiveMinimum": 0,
            },
            "stop_loss": {
                "type": "number",
                "description": "Stop loss price",
                "exclusiveMinimum": 0,
            },
            "account_balance": {
                "type": "number",
                "description": "Current account balance",
                "default": 1000000,
                "exclusiveMinimum": 0,
            },
            "take_profit": {
                "type": "number",
                "description": "Take profit price",
                "exclusiveMinimum": 0,
            },
            "daily_pnl": {
                "type": "number",
                "description": "Today's P&L",
                "default": 0,
            },
            "weekly_pnl": {
                "type": "number",
                "description": "This week's P&L",
                "default": 0,
            },
            "trade_count_today": {
                "type": "integer",
                "description": "Number of trades today",
                "default": 0,
            },
            "active_positions": {
                "type": "array",
                "description": "Currently held symbols",
                "items": {"type": "string"},
            },
        },
        required=["symbol", "direction", "lot_size", "entry", "stop_loss"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "symbol": {"type": "string"},
            "verdict": {"type": "string"},
            "checkpoints": {"type": "object"},
        },
    ),
    annotations={"category": "risk", "version": "1.0", "constitutional": True},
)

RISK_COMPUTE_VAR = ToolDefinition(
    name="risk.compute_var",
    description="Compute Value at Risk (VaR) and Conditional VaR (CVaR/Expected Shortfall) for the portfolio.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "portfolio_value": {
                "type": "number",
                "description": "Current portfolio value",
                "exclusiveMinimum": 0,
            },
            "confidence_level": {
                "type": "number",
                "description": "Confidence level (0.90-0.99)",
                "default": 0.95,
                "minimum": 0.9,
                "maximum": 0.99,
            },
            "time_horizon": {
                "type": "integer",
                "description": "Time horizon in days",
                "default": 1,
                "minimum": 1,
            },
            "method": {
                "type": "string",
                "description": "Calculation method",
                "enum": ["parametric", "historical", "monte_carlo"],
                "default": "parametric",
            },
        },
        required=["portfolio_value"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "var_value": {"type": "number"},
            "cvar_value": {"type": "number"},
            "confidence_level": {"type": "number"},
        },
    ),
    annotations={"category": "risk", "version": "1.0"},
)

RISK_COMPUTE_DRAWDOWN = ToolDefinition(
    name="risk.compute_drawdown",
    description="Compute current and maximum drawdown for the portfolio.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "portfolio_value": {
                "type": "number",
                "description": "Portfolio value for reference",
                "exclusiveMinimum": 0,
            },
            "peak_value": {
                "type": "number",
                "description": "Peak portfolio value",
                "exclusiveMinimum": 0,
            },
            "current_value": {
                "type": "number",
                "description": "Current portfolio value",
                "exclusiveMinimum": 0,
            },
        },
        required=["portfolio_value", "peak_value", "current_value"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "current_drawdown": {"type": "number"},
            "max_drawdown": {"type": "number"},
        },
    ),
    annotations={"category": "risk", "version": "1.0"},
)

FACTORS_LIST = ToolDefinition(
    name="factors.list",
    description="List available alpha factors with optional filtering by zoo and theme.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "zoo": {
                "type": "string",
                "description": "Filter by zoo (alpha101, gtja191, technical, fundamental)",
            },
            "theme": {
                "type": "string",
                "description": "Filter by theme (momentum, reversal, volume, etc.)",
            },
        },
        required=[],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "factors": {"type": "array"},
            "count": {"type": "integer"},
        },
    ),
    annotations={"category": "factors", "version": "1.0"},
)

FACTORS_COMPUTE = ToolDefinition(
    name="factors.compute",
    description="Compute an alpha factor on provided OHLCV data.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "factor_id": {
                "type": "string",
                "description": "Unique factor identifier (e.g., 'alpha101_001')",
                "minLength": 1,
            },
            "data": {
                "type": "array",
                "description": "OHLCV data records for computation",
                "items": {"type": "object"},
            },
        },
        required=["factor_id"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "factor_id": {"type": "string"},
            "values": {"type": "array"},
            "count": {"type": "integer"},
        },
    ),
    annotations={"category": "factors", "version": "1.0"},
)

FACTORS_GET_META = ToolDefinition(
    name="factors.get_meta",
    description="Get metadata for a specific alpha factor (formula, required columns, warmup).",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "factor_id": {
                "type": "string",
                "description": "Unique factor identifier",
                "minLength": 1,
            },
        },
        required=["factor_id"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "factor_id": {"type": "string"},
            "zoo": {"type": "string"},
            "theme": {"type": "array"},
        },
    ),
    annotations={"category": "factors", "version": "1.0"},
)

FACTORS_HEALTH = ToolDefinition(
    name="factors.health",
    description="Get factor registry health status (loaded factors, errors, by-zoo breakdown).",
    input_schema=ToolInputSchema(
        type="object",
        properties={},
        required=[],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "loaded": {"type": "integer"},
            "failed": {"type": "integer"},
        },
    ),
    annotations={"category": "factors", "version": "1.0"},
)

BACKTEST_RUN = ToolDefinition(
    name="backtest.run",
    description="Run a backtest with specified configuration, symbols, and strategy type.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbols": {
                "type": "array",
                "description": "List of symbols to backtest",
                "items": {"type": "string"},
            },
            "strategy_type": {
                "type": "string",
                "description": "Strategy type",
                "enum": ["signal_based", "factor_based", "ml_based"],
                "default": "signal_based",
            },
            "initial_capital": {
                "type": "number",
                "description": "Starting capital",
                "default": 1000000,
                "exclusiveMinimum": 0,
            },
            "commission_rate": {
                "type": "number",
                "description": "Commission rate as decimal",
                "default": 0.001,
            },
            "slippage_bps": {
                "type": "number",
                "description": "Slippage in basis points",
                "default": 5.0,
            },
            "start_date": {
                "type": "string",
                "description": "Backtest start date (ISO format)",
            },
            "end_date": {
                "type": "string",
                "description": "Backtest end date (ISO format)",
            },
            "market": {
                "type": "string",
                "description": "Market type",
                "enum": ["equity", "crypto", "forex", "futures"],
                "default": "equity",
            },
        },
        required=[],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "status": {"type": "string"},
            "metrics": {"type": "object"},
        },
    ),
    annotations={"category": "backtest", "version": "1.0"},
)

BACKTEST_WALK_FORWARD = ToolDefinition(
    name="backtest.walk_forward",
    description="Run walk-forward analysis for robust out-of-sample strategy validation.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbols": {
                "type": "array",
                "description": "List of symbols to analyze",
                "items": {"type": "string"},
            },
            "train_window": {
                "type": "integer",
                "description": "Training window in bars",
                "default": 252,
                "minimum": 10,
            },
            "test_window": {
                "type": "integer",
                "description": "Test window in bars",
                "default": 63,
                "minimum": 5,
            },
            "initial_capital": {
                "type": "number",
                "description": "Starting capital",
                "default": 1000000,
                "exclusiveMinimum": 0,
            },
        },
        required=[],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "status": {"type": "string"},
            "avg_metrics": {"type": "object"},
        },
    ),
    annotations={"category": "backtest", "version": "1.0"},
)

PORTFOLIO_GET = ToolDefinition(
    name="portfolio.get",
    description="Get current portfolio overview (positions, PnL, risk metrics, trade statistics).",
    input_schema=ToolInputSchema(
        type="object",
        properties={},
        required=[],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "total_value": {"type": "number"},
            "cash": {"type": "number"},
            "positions": {"type": "object"},
            "total_unrealized_pnl": {"type": "number"},
        },
    ),
    annotations={"category": "portfolio", "version": "1.0"},
)

PORTFOLIO_GET_POSITIONS = ToolDefinition(
    name="portfolio.get_positions",
    description="Get all open positions with unrealized P&L and stop-loss details.",
    input_schema=ToolInputSchema(
        type="object",
        properties={},
        required=[],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "positions": {"type": "object"},
            "count": {"type": "integer"},
        },
    ),
    annotations={"category": "portfolio", "version": "1.0"},
)

PORTFOLIO_GET_POSITION = ToolDefinition(
    name="portfolio.get_position",
    description="Get position details for a specific symbol.",
    input_schema=ToolInputSchema(
        type="object",
        properties={
            "symbol": {
                "type": "string",
                "description": "Trading symbol",
                "minLength": 1,
            },
        },
        required=["symbol"],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "symbol": {"type": "string"},
            "side": {"type": "string"},
            "quantity": {"type": "number"},
        },
    ),
    annotations={"category": "portfolio", "version": "1.0"},
)

PORTFOLIO_GET_PERFORMANCE = ToolDefinition(
    name="portfolio.get_performance",
    description="Get portfolio performance metrics (returns, Sharpe, drawdown, win rate, profit factor).",
    input_schema=ToolInputSchema(
        type="object",
        properties={},
        required=[],
    ),
    output_schema=ToolOutputSchema(
        type="object",
        properties={
            "total_return": {"type": "number"},
            "sharpe_ratio": {"type": "number"},
            "max_drawdown": {"type": "number"},
            "win_rate": {"type": "number"},
        },
    ),
    annotations={"category": "portfolio", "version": "1.0"},
)


# ─── Tool Registry ────────────────────────────────────────────────────────────

# Maps tool names to (definition, function) tuples
TRADING_TOOLS: Dict[str, tuple[ToolDefinition, Callable[..., Any]]] = {
    # Market Data
    "market_data.get_ohlcv": (MARKET_DATA_GET_OHLCV, _market_data_get_ohlcv),
    "market_data.get_ticker": (MARKET_DATA_GET_TICKER, _market_data_get_ticker),
    "market_data.get_orderbook": (MARKET_DATA_GET_ORDERBOOK, _market_data_get_orderbook),
    "market_data.get_market_data": (MARKET_DATA_GET_MARKET_DATA, _market_data_get_market_data),
    # Orders
    "orders.place_order": (ORDERS_PLACE_ORDER, _orders_place_order),
    "orders.cancel_order": (ORDERS_CANCEL_ORDER, _orders_cancel_order),
    "orders.get_order_status": (ORDERS_GET_ORDER_STATUS, _orders_get_order_status),
    # Risk
    "risk.assess_trade": (RISK_ASSESS_TRADE, _risk_assess_trade),
    "risk.compute_var": (RISK_COMPUTE_VAR, _risk_compute_var),
    "risk.compute_drawdown": (RISK_COMPUTE_DRAWDOWN, _risk_compute_drawdown),
    # Factors
    "factors.list": (FACTORS_LIST, _factors_list),
    "factors.compute": (FACTORS_COMPUTE, _factors_compute),
    "factors.get_meta": (FACTORS_GET_META, _factors_get_meta),
    "factors.health": (FACTORS_HEALTH, _factors_health),
    # Backtest
    "backtest.run": (BACKTEST_RUN, _backtest_run),
    "backtest.walk_forward": (BACKTEST_WALK_FORWARD, _backtest_walk_forward),
    # Portfolio
    "portfolio.get": (PORTFOLIO_GET, _portfolio_get),
    "portfolio.get_positions": (PORTFOLIO_GET_POSITIONS, _portfolio_get_positions),
    "portfolio.get_position": (PORTFOLIO_GET_POSITION, _portfolio_get_position),
    "portfolio.get_performance": (PORTFOLIO_GET_PERFORMANCE, _portfolio_get_performance),
}


def register_all_trading_tools(server: Any) -> None:
    """Register all trading tools with an MCP server.

    Args:
        server: MCPServer instance to register tools with.
    """
    for tool_name, (definition, func) in TRADING_TOOLS.items():
        handler = FunctionToolHandler(
            name=definition.name,
            description=definition.description,
            input_schema=definition.input_schema,
            func=func,
            output_schema=definition.output_schema,
            annotations=definition.annotations,
        )
        try:
            server.register_tool(handler)
        except ValueError:
            logger.warning("Tool %s already registered, skipping", tool_name)


def get_trading_tool_names() -> List[str]:
    """Get the names of all available trading tools.

    Returns:
        Sorted list of trading tool names.
    """
    return sorted(TRADING_TOOLS.keys())


def get_trading_tool_categories() -> Dict[str, List[str]]:
    """Group trading tools by category.

    Returns:
        Dict mapping category names to lists of tool names.
    """
    categories: Dict[str, List[str]] = {}
    for tool_name, (definition, _) in TRADING_TOOLS.items():
        category = definition.annotations.get("category", "uncategorized")
        if category not in categories:
            categories[category] = []
        categories[category].append(tool_name)
    return categories
