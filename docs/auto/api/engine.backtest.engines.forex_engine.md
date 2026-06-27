# engine.backtest.engines.forex_engine

## Function: 

Size of 1 pip for the pair.

Args:
    symbol: Forex pair (e.g. 'EUR/USD', 'USD/JPY').

Returns:
    1 pip in price terms (0.0001 or 0.01 for JPY pairs).

*Line: 57*

---

## Function: 

Normalize forex symbol to 'XXX/YYY' format.

Args:
    symbol: Raw symbol string.

Returns:
    Normalized symbol like 'EUR/USD'.

*Line: 70*

---

## Function: 

Calculate forex swap for one symbol.

Swap is the overnight rollover interest charged/credited for
holding a position past the daily close. Wednesday = triple swap
to cover the weekend.

Args:
    symbol: Forex pair.
    timestamp: Bar timestamp.
    positions: Shared positions dict.
    lot_size: Standard lot size (e.g. 100_000).
    last_swap_dates: Per-symbol date tracking dict — mutated.

Returns:
    Swap amount (positive = credit, negative = debit).

*Line: 87*

---

## Class: 

Forex engine for spot / CFD pairs.

Config keys:
  - ``leverage``: default 100.0 (100:1)
  - ``spread_pips_override``: override spread for all pairs
  - ``lot_size``: default 100000 (standard lot)
  - ``swap_enabled``: default True
  - ``slippage_pips``: additional slippage beyond spread, default 0.3

**Methods:** __init__, _reset_state, can_execute, round_size, calc_commission, apply_slippage, apply_slippage_for_symbol, on_bar, get_contract_multiplier

*Line: 135*

---

## Function: 

*Line: 146*

---

## Function: 

Reset engine state including swap tracking.

*Line: 155*

---

## Function: 

Forex: 24x5, no restrictions.

*Line: 160*

---

## Function: 

Round to micro-lot granularity (0.01 lots = 1000 units).

Position size is in currency units (not lots) for P&L compatibility.

*Line: 164*

---

## Function: 

Forex: spread is the cost, embedded in slippage. No explicit commission.

The cost is captured via ``apply_slippage`` which applies half-spread.
Some ECN brokers charge per-lot commission; for simplicity, zero here.

*Line: 171*

---

## Function: 

Apply half-spread + slippage using _active_symbol for correct pip/spread.

Args:
    price: Mid price.
    direction: 1 (buy) or -1 (sell).

Returns:
    Slipped price.

*Line: 181*

---

## Function: 

Symbol-aware slippage with correct spread.

Args:
    symbol: Forex pair.
    price: Mid price.
    direction: 1 (buy) or -1 (sell).

Returns:
    Slipped price.

*Line: 193*

---

## Function: 

Apply daily swap/rollover at end of trading day.

*Line: 217*

---

## Function: 

Forex: multiplier is 1.0 (size is in currency units).

*Line: 230*

---

