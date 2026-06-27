# memory.journal

## Class: 

Trade journal for recording and analyzing trade history.

Provides structured trade logging with entry/exit tracking,
PnL calculation, and reflection/review capabilities.

Usage:
    journal = TradeJournal()
    journal.record_entry(symbol="BTC/USDT", side="buy", price=50000, quantity=0.1)
    journal.record_exit(symbol="BTC/USDT", price=52000, pnl=200.0)
    journal.add_reflection(symbol="BTC/USDT", notes="Good trend following trade")

**Methods:** __init__, record_entry, record_exit, add_reflection, get_trade_history, get_performance_summary, save, load

*Line: 18*

---

## Function: 

Initialize trade journal.

Args:
    persist_path: Path for journal persistence file

*Line: 32*

---

## Function: 

Record a trade entry.

Args:
    symbol: Trading pair symbol
    side: Trade direction ('buy' or 'sell')
    price: Entry price
    quantity: Trade quantity
    agent_name: Agent that made the decision
    strategy: Strategy name
    reasoning: Decision reasoning
    metadata: Additional metadata

Returns:
    Trade ID

*Line: 43*

---

## Function: 

Record a trade exit.

Args:
    symbol: Trading pair symbol
    price: Exit price
    pnl: Realized PnL
    notes: Exit notes

Returns:
    Trade ID if found, None otherwise

*Line: 94*

---

## Function: 

Add reflection notes to an open or recent trade.

*Line: 140*

---

## Function: 

Get trade history with optional filters.

Args:
    symbol: Filter by symbol
    status: Filter by status ('open', 'closed')
    limit: Maximum trades to return

Returns:
    List of trade records

*Line: 152*

---

## Function: 

Calculate performance summary across all closed trades.

*Line: 176*

---

## Function: 

Persist journal to disk.

*Line: 200*

---

## Function: 

Load journal from disk.

*Line: 208*

---

