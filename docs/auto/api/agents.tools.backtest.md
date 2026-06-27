# agents.tools.backtest

## Function: 

Generate SMA crossover trade signals.

Returns a list of signal dicts with 'bar_index', 'direction', 'price'.

*Line: 47*

---

## Function: 

Generate RSI mean-reversion trade signals.

Buy when RSI crosses above oversold, sell when RSI crosses below overbought.

*Line: 96*

---

## Function: 

Generate MACD crossover signals.

Buy when MACD line crosses above signal line.
Sell when MACD line crosses below signal line.

*Line: 159*

---

## Class: 

In-memory store for backtest results, keyed by backtest_id.

**Methods:** __init__, store, get, list_ids

*Line: 242*

---

## Class: 

Backtesting tool for agent consumption.

Provides a high-level interface to run strategy backtests, store
results, and retrieve them by ID. Supports both built-in strategies
and custom strategy functions.

Built-in strategies:
  - sma_crossover: SMA fast/slow crossover
  - rsi_mean_revert: RSI oversold/overbought mean-reversion
  - macd_crossover: MACD line/signal crossover

Usage::

    tool = BacktestTool(market_data_tool=mdt)
    result = await tool.run_backtest(
        strategy="sma_crossover",
        symbol="AAPL",
        timeframe="1d",
        start_date="2023-01-01",
        end_date="2024-01-01",
    )
    print(result["metrics"]["sharpe_ratio"])

**Methods:** __init__, register_strategy, _filter_candles_by_date, _simulate_trades, _calculate_metrics

*Line: 266*

---

## Function: 

Get or create the default BacktestTool instance.

*Line: 697*

---

## Function: 

*Line: 177*

---

## Function: 

*Line: 245*

---

## Function: 

Store a backtest result.

*Line: 249*

---

## Function: 

Retrieve a backtest result by ID.

*Line: 257*

---

## Function: 

List all stored backtest IDs.

*Line: 261*

---

## Function: 

Initialize the BacktestTool.

Args:
    market_data_tool: Optional MarketDataTool for auto-fetching data.
    max_stored_results: Maximum number of results to keep in memory.

*Line: 292*

---

## Function: 

Register a custom strategy function.

The function must accept `closes: List[float]` as the first
argument and return a list of signal dicts with keys
'bar_index', 'direction', 'price'.

Args:
    name: Strategy name for lookup.
    func: Strategy signal generation function.

*Line: 491*

---

## Function: 

Filter candles to the requested date range.

*Line: 511*

---

## Function: 

Simulate trades from signals and build equity curve.

Simple simulation: alternate BUY/SELL signals, track P&L.

Returns:
    Tuple of (trades_list, equity_curve_list).

*Line: 537*

---

## Function: 

Calculate backtest performance metrics.

Computes Sharpe ratio, max drawdown, win rate, and other metrics
from the equity curve and trade list.

*Line: 606*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 31*

---

## Function: 

*Line: 35*

---

