# engine.backtest.engines.futures_engine

## Function: 

Extract product code from futures symbol.

Handles formats like:
  - ``IF2406.CFFEX`` → ``IF``
  - ``ESZ4`` → ``ES``
  - ``rb2410.SHFE`` → ``rb``
  - ``CL2412`` → ``CL``

Args:
    code: Futures symbol string.

Returns:
    Product code string (uppercase).

*Line: 67*

---

## Class: 

Futures engine with contract-multiplier support.

Config keys:
  - ``leverage``: default 10.0
  - ``commission_per_contract``: per-contract commission, default 0.0
  - ``commission_rate``: rate-based commission, default 0.00005
  - ``slippage``: default 0.0003
  - ``margin_rate``: margin as fraction of notional, default 0.1
  - ``multipliers``: optional dict of symbol -> multiplier overrides

The engine auto-detects contract multipliers from the product code.
Override with ``config["multipliers"]`` for custom products.

**Methods:** __init__, get_contract_multiplier, _calc_pnl, _calc_margin, _calc_raw_size, can_execute, round_size, calc_commission, apply_slippage, on_bar

*Line: 93*

---

## Function: 

*Line: 108*

---

## Function: 

Contract multiplier for the instrument.

Looks up from custom overrides first, then from known tables.

Args:
    symbol: Futures symbol (e.g. 'IF2406.CFFEX', 'ESZ4').

Returns:
    Points-to-currency multiplier (e.g. IF=300, ES=50).
    Default 1.0 if unknown.

*Line: 122*

---

## Function: 

P&L with contract multiplier: direction * size * cm * (exit - entry).

*Line: 165*

---

## Function: 

Margin with contract multiplier: size * price * cm / leverage.

*Line: 177*

---

## Function: 

Position sizing with contract multiplier: target_notional / (price * cm).

*Line: 188*

---

## Function: 

Futures: long/short/close allowed. Price limit checks are optional.

*Line: 200*

---

## Function: 

Futures: round to integer number of contracts.

*Line: 204*

---

## Function: 

Futures commission: per-contract fee + rate-based fee.

Args:
    size: Number of contracts.
    price: Execution price.
    direction: Trade direction.
    is_open: Opening or closing trade.

Returns:
    Commission amount.

*Line: 208*

---

## Function: 

Futures slippage: unfavourable direction.

*Line: 233*

---

## Function: 

No special per-bar hooks for futures (settlement is handled at close).

*Line: 237*

---

