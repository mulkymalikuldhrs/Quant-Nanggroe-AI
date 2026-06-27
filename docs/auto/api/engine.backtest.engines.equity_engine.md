# engine.backtest.engines.equity_engine

## Class: 

US / HK / China-A equity engine.

The ``market`` parameter selects the rule set:
  - ``"us"``: US equity (fractional shares, zero commission)
  - ``"hk"``: HK equity (100-share lots, stamp tax + levies)
  - ``"china_a"``: A-share (T+1, no short, price limits)

Config keys (all optional — sensible defaults):
  - ``slippage_us``: default 0.0005
  - ``slippage_hk``: default 0.001
  - ``slippage_china``: default 0.001
  - ``hk_stamp_tax``: default 0.001 (0.1% bilateral)
  - ``hk_commission``: default 0.00015 (万1.5)
  - ``hk_levy``: default 0.0000565 (SFC + FRC)
  - ``hk_settlement``: default 0.00002 (CCASS)
  - ``commission_rate``: A-share commission rate, default 0.00025 (万2.5)
  - ``commission_min``: A-share min commission, default 5.0 RMB
  - ``stamp_tax``: A-share stamp tax sell-only, default 0.0005
  - ``transfer_fee``: A-share transfer fee bilateral, default 0.00001

**Methods:** __init__, can_execute, _can_execute_china, round_size, calc_commission, apply_slippage, on_bar

*Line: 38*

---

## Function: 

Extract date from bar, handling various column names.

*Line: 194*

---

## Function: 

Calculate price change percentage from bar data.

*Line: 210*

---

## Function: 

Determine price limit based on board type.

Args:
    symbol: Stock code (e.g. 300001.SZ, 688001.SH, 000001.SZ).

Returns:
    Limit as fraction (0.10, 0.20, 0.30, or 0.05).

*Line: 224*

---

## Function: 

*Line: 60*

---

## Function: 

Check if trade is allowed by market rules.

Args:
    symbol: Instrument identifier.
    direction: 1 (buy), -1 (short), 0 (close).
    bar: Current bar data.

Returns:
    True if trade is allowed.

*Line: 80*

---

## Function: 

A-share execution rules.

1. No short selling
2. T+1: can't sell shares bought today
3. Price limits: ±10% main board, ±20% ChiNext/STAR, ±5% ST

*Line: 96*

---

## Function: 

Round position size per market lot rules.

- US: fractional shares (0.01)
- HK: 100-share lots
- China A: 100-share lots

*Line: 129*

---

## Function: 

Calculate commission based on market rules.

- US: zero commission
- HK: stamp tax + levies
- China A: commission + stamp tax (sell) + transfer fee

*Line: 140*

---

## Function: 

Apply slippage based on market.

- US: low slippage
- HK: moderate slippage
- China A: moderate slippage

*Line: 171*

---

## Function: 

No per-bar hooks for equity markets.

*Line: 186*

---

