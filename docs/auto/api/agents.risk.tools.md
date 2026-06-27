# agents.risk.tools

## Function: 

Check if two symbols are in the same correlation group.

*Line: 61*

---

## Function: 

Lazy-load VaRCalculator from engine.risk.var.

*Line: 72*

---

## Function: 

Lazy-load KellyCriterion from engine.risk.kelly.

*Line: 82*

---

## Function: 

Lazy-load DrawdownMonitor from engine.risk.drawdown.

*Line: 92*

---

## Function: 

Lazy-load KillSwitch from engine.risk.kill_switch.

*Line: 102*

---

## Function: 

Compute Value at Risk (VaR) using parametric method.

PRODUCTION: Uses VaRCalculator from engine.risk.var for real
parametric/historical/Monte Carlo VaR calculations.
Falls back to in-file calculation if engine unavailable.
Mock fallback only in _MOCK_MODE.

Args:
    portfolio_value: Total portfolio value in USD
    confidence_level: Confidence level (0.95 or 0.99)
    holding_period_days: Holding period in days
    daily_volatility: Daily volatility estimate

Returns:
    JSON string with VaR calculation

*Line: 117*

---

## Function: 

Compute Conditional Value at Risk (CVaR / Expected Shortfall).

PRODUCTION: Uses VaRCalculator from engine.risk.var for real CVaR.
Falls back to in-file calculation if engine unavailable.
Mock fallback only in _MOCK_MODE.

Args:
    portfolio_value: Total portfolio value in USD
    confidence_level: Confidence level (0.95 or 0.99)
    daily_volatility: Daily volatility estimate

Returns:
    JSON string with CVaR calculation

*Line: 198*

---

## Function: 

Check current drawdown against constitutional limits.

PRODUCTION: Uses DrawdownMonitor from engine.risk.drawdown
for real drawdown tracking with constitutional enforcement.
Falls back to in-file calculation if engine unavailable.

Args:
    portfolio_value: Current portfolio value
    peak_value: Historical peak portfolio value
    current_drawdown_pct: Current drawdown percentage (if pre-calculated)

Returns:
    JSON string with drawdown assessment

*Line: 274*

---

## Function: 

Calculate position size using Kelly Criterion, capped at constitutional limits.

PRODUCTION: Uses KellyCriterion from engine.risk.kelly for real
multi-variant Kelly calculations (Full, Half, Quarter, Fractional, Adaptive).
Falls back to in-file calculation if engine unavailable.

Args:
    win_rate: Historical win rate (0.0 - 1.0)
    avg_win: Average winning trade amount
    avg_loss: Average losing trade amount
    account_balance: Current account balance

Returns:
    JSON string with Kelly sizing recommendation

*Line: 345*

---

## Function: 

Manage the emergency kill switch.

PRODUCTION: Uses KillSwitch from engine.risk.kill_switch for real
emergency halt with audit trail and manual reset confirmation.
Falls back to in-file calculation if engine unavailable.

Args:
    action: Action to perform (check, activate, reset)
    daily_pnl_pct: Current daily PnL percentage
    weekly_pnl_pct: Current weekly PnL percentage
    reason: Reason for activation

Returns:
    JSON string with kill switch status

*Line: 438*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 23*

---

## Function: 

*Line: 27*

---

