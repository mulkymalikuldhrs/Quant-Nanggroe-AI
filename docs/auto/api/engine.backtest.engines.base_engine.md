# engine.backtest.engines.base_engine

## Class: 

An open position in a single instrument.

Attributes:
    symbol: Instrument identifier.
    direction: 1 for long, -1 for short.
    entry_price: Execution price at entry.
    entry_time: Timestamp when position was opened.
    size: Number of shares / coins / contracts.
    leverage: Effective leverage (1 for spot/stocks).
    entry_bar_idx: Index in the dates array at entry (for holding_bars).
    entry_commission: Commission paid at entry.

*Line: 39*

---

## Class: 

Portfolio state at a single point in time.

Attributes:
    timestamp: Bar timestamp.
    capital: Free cash.
    unrealized: Total unrealised P&L across all positions.
    equity: capital + margin_in_use + unrealized.
    positions: Number of open positions.

*Line: 64*

---

## Class: 

Configuration for a market engine.

Attributes:
    initial_cash: Starting capital.
    leverage: Default leverage.
    bars_per_year: Bars per year for annualisation (None = auto-detect).
    benchmark: Benchmark ticker for comparison.
    max_positions: Maximum simultaneous positions.

*Line: 83*

---

## Class: 

Abstract base for all market engines.

Subclasses override market-rule methods:
  - ``can_execute``: whether a trade is allowed by market rules
  - ``round_size``: lot-size rounding
  - ``calc_commission``: fee structure
  - ``apply_slippage``: slippage model
  - ``on_bar``: per-bar hooks (funding fees, liquidation, etc.)

Usage::

    engine = EquityEngine(config, market="us")
    result = engine.run(prices, signals)

**Methods:** __init__, can_execute, round_size, calc_commission, apply_slippage, on_bar, _calc_pnl, _calc_margin, _calc_raw_size, run, _reset_state, _execute_bars, _calc_equity_from_prices, _rebalance, _close_position, _force_close_all, _by_symbol_stats, _by_exit_reason_stats

*Line: 104*

---

## Function: 

Initialise the engine.

Args:
    config: Backtest configuration dict. Recognised keys:
        - ``initial_cash``: Starting capital (default 1_000_000).
        - ``leverage``: Default leverage (default 1.0).

*Line: 120*

---

## Function: 

Whether market rules allow this trade.

Args:
    symbol: Instrument identifier.
    direction: 1 (long), -1 (short), 0 (close).
    bar: Current bar data (OHLCV + extras).

Returns:
    True if allowed.

*Line: 141*

---

## Function: 

Round position size per market lot rules.

Args:
    raw_size: Desired size.
    price: Current price.

Returns:
    Rounded size.

*Line: 154*

---

## Function: 

Calculate commission for a trade.

Args:
    size: Trade size.
    price: Execution price.
    direction: 1 or -1.
    is_open: True for opening, False for closing.

Returns:
    Commission amount.

*Line: 166*

---

## Function: 

Apply slippage to execution price.

Args:
    price: Raw price.
    direction: 1 (buying/covering short) or -1 (selling/shorting).

Returns:
    Slipped price.

*Line: 182*

---

## Function: 

Per-bar market-rule hook (funding fees, liquidation, etc.).

Default: no-op. Override in subclass as needed.

*Line: 193*

---

## Function: 

Realised P&L for a closed position.

Override in FuturesEngine to inject contract multiplier.

*Line: 201*

---

## Function: 

Margin (collateral) required for a position.

*Line: 215*

---

## Function: 

Convert target notional exposure to number of units/contracts.

*Line: 225*

---

## Function: 

Run the backtest on price data with trading signals.

The engine processes data bar-by-bar, executing trades based on
signal-driven target weights with market-rule enforcement.

Args:
    prices: DataFrame with DatetimeIndex and columns for each symbol.
        Values are close prices.
    signals: DataFrame with same index/columns as prices.
        Values are target position weights (-1 to 1).
    position_sizer: Optional callable for custom position sizing.
        Signature: (signal, capital, price) -> size.
    bars_per_year: Override for annualisation factor.
        None = use engine default (252 for equity, 365 for crypto).
    benchmark_returns: Optional benchmark return series.

Returns:
    Dict with:
        - ``metrics``: Performance metrics dictionary.
        - ``equity_curve``: pd.Series of equity over time.
        - ``trades``: List of TradeRecord.
        - ``final_equity``: Final portfolio equity.
        - ``total_trades``: Number of completed trades.

*Line: 238*

---

## Function: 

Reset engine state for a new backtest run.

*Line: 315*

---

## Function: 

Bar-by-bar execution with market rule enforcement.

Args:
    prices: Close price DataFrame.
    shifted_signals: Shifted signal DataFrame.
    symbols: List of symbol names.
    position_sizer: Optional position sizing callable.

*Line: 324*

---

## Function: 

Total equity = free cash + sum(margin + unrealised) per position.

Args:
    price_row: Series of current prices indexed by symbol.

Returns:
    Total equity value.

*Line: 389*

---

## Function: 

Adjust position for *symbol* toward *target_weight*.

Args:
    symbol: Instrument identifier.
    target_weight: Target weight (-1 to 1).
    price: Current price.
    timestamp: Current bar timestamp.
    equity: Current portfolio equity.
    position_sizer: Optional custom position sizer.

*Line: 409*

---

## Function: 

Close position, record trade, return capital.

Args:
    symbol: Instrument identifier.
    exit_price: Execution price for closing.
    exit_time: Closing timestamp.
    reason: Reason for closing (``signal``, ``liquidation``,
        ``end_of_backtest``, etc.).

*Line: 501*

---

## Function: 

Force close all remaining positions at end of backtest.

Args:
    prices: Price DataFrame for exit price lookup.

*Line: 548*

---

## Function: 

Per-symbol trade statistics.

Returns:
    Mapping ``{symbol: {count, win_rate, total_pnl, avg_pnl}}``.

*Line: 571*

---

## Function: 

Per-exit-reason trade statistics.

Returns:
    Mapping ``{reason: {count, total_pnl}}``.

*Line: 593*

---

