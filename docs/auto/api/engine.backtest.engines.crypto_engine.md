# engine.backtest.engines.crypto_engine

## Function: 

Look up tiered maintenance margin rate.

Args:
    notional_usd: Position notional in USD.

Returns:
    Maintenance margin rate.

*Line: 38*

---

## Function: 

Calculate crypto funding fee for one symbol.

Funding fees are charged every 8 hours (00:00/08:00/16:00 UTC).
For daily data, a single daily funding fee is applied as fallback.

Args:
    symbol: Instrument code.
    bar: Current bar data.
    timestamp: Bar timestamp.
    positions: Shared positions dict.
    funding_rate: Fixed rate per settlement.
    applied_set: ``(symbol, date, hour)`` dedup set — mutated.
    daily_done_set: ``(symbol, date)`` dedup set — mutated.

Returns:
    Fee amount (positive = longs pay, negative = longs receive).

*Line: 53*

---

## Function: 

Check if a crypto position should be liquidated.

Uses tiered maintenance margin model. A position is liquidated
when ``margin + unrealized <= maintenance_margin``.

Args:
    symbol: Instrument code.
    bar: Current bar data.
    positions: Shared positions dict.

Returns:
    True if liquidation should be triggered.

*Line: 106*

---

## Class: 

Crypto perpetual contract engine.

Config keys:
  - ``leverage``: default 1.0
  - ``maker_rate``: default 0.0002
  - ``taker_rate``: default 0.0005
  - ``slippage``: default 0.0005
  - ``margin_mode``: ``"isolated"`` (default) or ``"cross"``
  - ``funding_rate``: fixed rate per settlement, default 0.0001

**Methods:** __init__, _reset_state, can_execute, round_size, calc_commission, apply_slippage, on_bar

*Line: 139*

---

## Function: 

*Line: 151*

---

## Function: 

Reset engine state including funding fee tracking.

*Line: 162*

---

## Function: 

Crypto: 24/7, long/short/close all allowed.

*Line: 168*

---

## Function: 

Crypto supports fractional sizes, round to 6 decimals.

*Line: 172*

---

## Function: 

Maker/Taker separated.

Opens typically hit taker, closes hit maker.

*Line: 176*

---

## Function: 

Slippage: unfavourable direction.

*Line: 186*

---

## Function: 

Crypto per-bar hooks: funding fee + liquidation check.

*Line: 190*

---

