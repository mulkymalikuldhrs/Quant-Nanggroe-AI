# engine.risk.kill_switch

## Class: 

Kill switch severity level.

*Line: 31*

---

## Class: 

What triggered the kill switch.

*Line: 39*

---

## Class: 

Current status of the kill switch.

*Line: 52*

---

## Class: 

Record of a kill switch activation/deactivation.

*Line: 62*

---

## Class: 

Configuration for the kill switch.

*Line: 77*

---

## Class: 

Emergency kill switch with auto-activation.

Monitors portfolio and market conditions, automatically
activating when safety thresholds are breached.

Usage::

    ks = KillSwitch()
    # Check if trading is allowed
    if ks.can_trade():
        # Execute trade
        pass

    # Manually activate
    ks.activate(KillSwitchLevel.LEVEL_1, reason="Manual override")

    # Deactivate after cooldown
    ks.deactivate()

**Methods:** __init__, is_active, status, reset, check_auto_trigger, activate, deactivate, check_auto_activate, check_warning, can_trade, can_hold_positions, on_activate, current_level, events, config, stats

*Line: 100*

---

## Function: 

*Line: 121*

---

## Function: 

Property access for is_active (backward compat).

*Line: 136*

---

## Function: 

Dict-returning status (backward compat for tests/RiskManager).

*Line: 140*

---

## Function: 

Reset kill switch (bypasses cooldown for emergency reset).

*Line: 155*

---

## Function: 

Dict-returning auto-trigger check (backward compat).

*Line: 173*

---

## Function: 

Activate the kill switch at a specified level.

Parameters
----------
level:
    Kill switch level to activate.
reason:
    Reason for activation.
trigger:
    What triggered the activation.
auto_activated:
    Whether this was automatically triggered.

Returns
-------
KillSwitchEvent
    Record of the activation.

*Line: 193*

---

## Function: 

Deactivate the kill switch.

Returns
-------
KillSwitchEvent or None
    Deactivation record, or None if not active.

*Line: 256*

---

## Function: 

Check if auto-activation conditions are met.

Parameters
----------
daily_pnl_pct:
    Current daily P&L as percentage (negative for loss).
weekly_pnl_pct:
    Current weekly P&L as percentage (negative for loss).
max_drawdown_pct:
    Current maximum drawdown percentage.
volatility_pct:
    Current market volatility percentage.

Returns
-------
KillSwitchEvent or None
    Activation event if triggered, else None.

*Line: 306*

---

## Function: 

Check if any metric is approaching its auto-activation threshold.

Returns True if any metric exceeds EARLY_WARNING_THRESHOLD (80%)
of its limit. Does NOT trigger the kill switch — just returns a flag.

Parameters
----------
daily_pnl_pct:
    Current daily P&L as percentage (negative for loss).
weekly_pnl_pct:
    Current weekly P&L as percentage (negative for loss).
max_drawdown_pct:
    Current maximum drawdown percentage.
volatility_pct:
    Current market volatility percentage.

Returns
-------
bool
    True if any metric is in the warning zone.

*Line: 376*

---

## Function: 

Check if new trades are allowed.

*Line: 424*

---

## Function: 

Check if holding existing positions is allowed.

*Line: 428*

---

## Function: 

Register a callback for a specific kill switch level.

*Line: 434*

---

## Function: 

*Line: 441*

---

## Function: 

*Line: 445*

---

## Function: 

*Line: 449*

---

## Function: 

Kill switch statistics.

*Line: 453*

---

