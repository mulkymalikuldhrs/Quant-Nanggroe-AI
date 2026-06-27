# mcp.tools

## Function: 

Fetch OHLCV candlestick data for a symbol.

Args:
    symbol: Trading pair symbol (e.g., 'BTC/USDT', 'AAPL').
    timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M).
    start: Start datetime in ISO format.
    end: End datetime in ISO format.
    limit: Maximum number of candles to return.

Returns:
    Dict with OHLCV data and metadata.

*Line: 38*

---

## Function: 

Fetch current ticker data for a symbol.

Args:
    symbol: Trading pair symbol.

Returns:
    Dict with current ticker information.

*Line: 68*

---

## Function: 

Fetch order book snapshot for a symbol.

Args:
    symbol: Trading pair symbol.
    limit: Number of bid/ask levels.

Returns:
    Dict with order book data.

*Line: 90*

---

## Function: 

Fetch aggregated market data for a symbol.

Args:
    symbol: Trading pair symbol.
    timeframe: Candle timeframe.
    include_ohlcv: Whether to include OHLCV data.
    include_ticker: Whether to include ticker data.
    include_orderbook: Whether to include order book data.

Returns:
    Dict with aggregated market data.

*Line: 113*

---

## Function: 

Place a trading order through the execution manager.

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

*Line: 157*

---

## Function: 

Cancel a pending order.

Args:
    order_id: Order ID to cancel.

Returns:
    Dict with cancellation status.

*Line: 223*

---

## Function: 

Get the status of an order.

Args:
    order_id: Order ID to query.

Returns:
    Dict with order status details.

*Line: 240*

---

## Function: 

Assess trade risk through the 9-checkpoint risk gate.

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

*Line: 259*

---

## Function: 

Compute Value at Risk (VaR) and Conditional VaR (CVaR).

Supports parametric (variance-covariance), historical, and Monte Carlo methods.

Args:
    portfolio_value: Current portfolio value.
    confidence_level: Confidence level (0.90-0.99).
    time_horizon: Time horizon in days.
    method: Calculation method (parametric/historical/monte_carlo).
    returns_data: Optional list of historical returns.

Returns:
    Dict with VaR and CVaR results.

*Line: 321*

---

## Function: 

Compute current and maximum drawdown.

Args:
    portfolio_value: Portfolio value for reference.
    peak_value: Peak portfolio value.
    current_value: Current portfolio value.

Returns:
    Dict with drawdown analysis results.

*Line: 356*

---

## Function: 

List available alpha factors with optional filtering.

Args:
    zoo: Filter by zoo (alpha101, gtja191, technical, fundamental).
    theme: Filter by theme (momentum, reversal, volume, etc.).

Returns:
    Dict with list of factor IDs and metadata.

*Line: 385*

---

## Function: 

Compute an alpha factor on provided data.

Args:
    factor_id: Unique factor identifier (e.g., 'alpha101_001').
    data: Optional list of OHLCV records for computation.

Returns:
    Dict with computed factor values.

*Line: 417*

---

## Function: 

Get metadata for a specific alpha factor.

Args:
    factor_id: Unique factor identifier.

Returns:
    Dict with factor metadata.

*Line: 464*

---

## Function: 

Get factor registry health status.

Returns:
    Dict with registry health details.

*Line: 494*

---

## Function: 

Run a backtest with the specified configuration.

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

*Line: 512*

---

## Function: 

Run walk-forward analysis for robust strategy validation.

Args:
    symbols: List of symbols to analyze.
    train_window: Training window in bars.
    test_window: Test window in bars.
    initial_capital: Starting capital.

Returns:
    Dict with walk-forward analysis results.

*Line: 560*

---

## Function: 

Get current portfolio overview.

Returns:
    Dict with portfolio summary including positions, PnL, and risk metrics.

*Line: 598*

---

## Function: 

Get all open positions.

Returns:
    Dict with position details keyed by symbol.

*Line: 624*

---

## Function: 

Get position details for a specific symbol.

Args:
    symbol: Trading symbol.

Returns:
    Dict with position details.

*Line: 638*

---

## Function: 

Get portfolio performance metrics.

Returns:
    Dict with performance metrics and statistics.

*Line: 661*

---

## Function: 

Register all trading tools with an MCP server.

Args:
    server: MCPServer instance to register tools with.

*Line: 1423*

---

## Function: 

Get the names of all available trading tools.

Returns:
    Sorted list of trading tool names.

*Line: 1444*

---

## Function: 

Group trading tools by category.

Returns:
    Dict mapping category names to lists of tool names.

*Line: 1453*

---

