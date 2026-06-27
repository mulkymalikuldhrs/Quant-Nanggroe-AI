# engine.risk.strategy_auto_disable

## Class: 

Internal state for a single strategy's performance tracking.

**Methods:** __init__, to_dict, from_dict

*Line: 44*

---

## Class: 

Monitors trailing Sharpe per strategy and auto-disables when below threshold.

Features:
    - Tracks trailing Sharpe per strategy over a configurable window
    - Disables strategy when trailing Sharpe < threshold (default: 0.3)
    - Re-enables after N consecutive days above threshold (default: 30)
    - Integrates with KillSwitch (LEVEL_1 equivalent per strategy)
    - Persists disabled state to JSON for restart survival
    - Returns True from update() if strategy is still active

Usage::

    mgr = AutoDisableManager()
    # Feed daily P&L series for a strategy
    active = mgr.update("MeanReversion", daily_pnl_series)
    if not active:
        # Strategy was auto-disabled, skip trade execution
        pass

    # Check which strategies are disabled
    disabled = mgr.get_disabled_strategies()

    # Re-enable manually
    mgr.enable("MeanReversion")

**Methods:** __init__, update, disable, enable, is_disabled, get_disabled_strategies, get_active_strategies, get_state, get_config, save_state, _compute_trailing_sharpe, _check_disable, _check_re_enable, _set_disabled, _set_enabled, _load_state

*Line: 76*

---

## Function: 

*Line: 47*

---

## Function: 

*Line: 55*

---

## Function: 

*Line: 66*

---

## Function: 

*Line: 103*

---

## Function: 

Update trailing Sharpe for a strategy.

Args:
    strategy_name: Name of the strategy.
    pnl_series: Series of P&L values (daily returns ideally).

Returns:
    True if the strategy is still active (not disabled).

*Line: 124*

---

## Function: 

Manually disable a strategy.

Args:
    strategy_name: Name of the strategy to disable.
    reason: Reason for disabling.

Returns:
    True if the strategy was newly disabled.

*Line: 151*

---

## Function: 

Manually re-enable a strategy.

Args:
    strategy_name: Name of the strategy to enable.
    reason: Reason for re-enabling.

Returns:
    True if the strategy was newly enabled.

*Line: 174*

---

## Function: 

Check if a strategy is currently disabled.

*Line: 191*

---

## Function: 

Get list of currently disabled strategy names.

*Line: 196*

---

## Function: 

Get list of currently active (not disabled) strategy names.

*Line: 200*

---

## Function: 

Get serialisable state of all tracked strategies.

*Line: 204*

---

## Function: 

Get current configuration.

*Line: 211*

---

## Function: 

Persist disabled state to JSON.

*Line: 220*

---

## Function: 

Compute trailing annualized Sharpe from the last N values.

*Line: 236*

---

## Function: 

Check if trailing Sharpe warrants disabling.

*Line: 245*

---

## Function: 

Check if trailing Sharpe has recovered enough to re-enable.

*Line: 256*

---

## Function: 

Mark strategy as disabled and activate kill switch.

*Line: 270*

---

## Function: 

Mark strategy as enabled.

*Line: 292*

---

## Function: 

Load disabled state from JSON persistence.

*Line: 307*

---

