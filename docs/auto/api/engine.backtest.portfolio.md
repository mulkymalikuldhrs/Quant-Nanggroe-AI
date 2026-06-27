# engine.backtest.portfolio

## Class: 

An open position in a single instrument.

Attributes:
    symbol: Instrument identifier.
    direction: 1 for long, -1 for short.
    entry_price: Execution price at entry.
    entry_time: Timestamp when position was opened.
    size: Number of shares / coins / contracts.
    leverage: Effective leverage (1 for spot/stocks).
    commission: Commission paid at entry.

*Line: 20*

---

## Class: 

A completed round-trip trade.

Attributes:
    symbol: Instrument identifier.
    direction: 1 for long, -1 for short.
    entry_price: Entry execution price.
    exit_price: Exit execution price.
    entry_time: Entry timestamp.
    exit_time: Exit timestamp.
    size: Number of shares / coins traded.
    pnl: Realised profit/loss in cash terms.
    pnl_pct: Realised P&L as percentage of entry value.
    exit_reason: Why closed (signal / stop_loss / end_of_backtest).
    commission: Total commission (entry + exit).
    holding_bars: Number of bars held.

*Line: 43*

---

## Class: 

Portfolio state manager for backtesting.

Tracks positions, cash, and equity throughout a backtest.
Supports multiple positions, commission tracking, and P&L calculation.

**Methods:** __init__, equity, unrealized_pnl, position_count, get_position, can_open_position, open_position, close_position, _apply_commission, mark_to_market, _calc_unrealized_pnl

*Line: 75*

---

## Function: 

*Line: 82*

---

## Function: 

Total portfolio equity (cash + unrealized P&L).

*Line: 96*

---

## Function: 

Total unrealized P&L across all positions.

*Line: 106*

---

## Function: 

Number of open positions.

*Line: 115*

---

## Function: 

Get the current position for a symbol.

*Line: 119*

---

## Function: 

Check if a new position can be opened.

Args:
    price: Entry price.
    size: Position size.
    commission: Commission for the trade.

Returns:
    True if the position can be opened.

*Line: 123*

---

## Function: 

Open a new position.

Args:
    symbol: Instrument identifier.
    direction: 1 for long, -1 for short.
    size: Position size in units.
    price: Entry price.
    timestamp: Entry timestamp.
    commission: Commission for opening.

Returns:
    TradeRecord for the opening (or None if failed).

*Line: 141*

---

## Function: 

Close an existing position.

Args:
    symbol: Instrument identifier.
    price: Exit price.
    timestamp: Exit timestamp.
    reason: Reason for closing.

Returns:
    TradeRecord for the closed position, or None if no position exists.

*Line: 189*

---

## Function: 

Apply additional commission to a trade (for exit commission).

*Line: 235*

---

## Function: 

Update current prices for all held positions.

Args:
    price_row: Series of current prices indexed by symbol.

*Line: 239*

---

## Function: 

Calculate unrealized P&L for a position.

*Line: 251*

---

