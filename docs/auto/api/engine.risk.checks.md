# engine.risk.checks

## Class: 

Risk assessment level.

*Line: 51*

---

## Class: 

Proposed trade action.

*Line: 61*

---

## Class: 

Result from a risk check.

*Line: 72*

---

## Class: 

Snapshot of current portfolio state.

**Methods:** daily_pnl_pct, weekly_pnl_pct, position_count, total_position_value

*Line: 90*

---

## Class: 

A proposed trade request.

**Methods:** notional_value

*Line: 124*

---

## Class: 

Constitutional risk guard with hardcoded limits.

All limits are enforced as constitutional constraints that
cannot be overridden.  Every trade must pass through this
guard before execution.

Usage::

    guard = ConstitutionalRiskGuard()
    result = guard.check_trade(
        request=TradeRequest(symbol="AAPL", action=TradeAction.BUY,
                            quantity=10, price=185.0),
        portfolio=PortfolioSnapshot(total_equity=100000),
    )
    if result.approved:
        # Execute trade
        pass

**Methods:** __init__, check_trade, evaluate, calculate_position_size, stats

*Line: 147*

---

## Function: 

Daily P&L as percentage of equity.

*Line: 103*

---

## Function: 

Weekly P&L as percentage of equity.

*Line: 108*

---

## Function: 

*Line: 113*

---

## Function: 

*Line: 117*

---

## Function: 

*Line: 140*

---

## Function: 

*Line: 167*

---

## Function: 

Check a proposed trade against constitutional risk limits.

Parameters
----------
request:
    The proposed trade.
portfolio:
    Current portfolio snapshot.

Returns
-------
RiskCheckResult
    Risk assessment with approval status.

*Line: 175*

---

## Function: 

Flat-parameter evaluate (backward compat for RiskManager).

*Line: 289*

---

## Function: 

Calculate position size based on risk budget.

Parameters
----------
equity:
    Total portfolio equity.
entry_price:
    Entry price per unit.
stop_loss_price:
    Stop-loss price per unit.
risk_pct:
    Risk as percentage of equity.

Returns
-------
float
    Position size in units.

*Line: 332*

---

## Function: 

Risk guard statistics.

*Line: 375*

---

