# engine.risk.drawdown

## Class: 

Drawdown analysis result.

*Line: 31*

---

## Class: 

Drawdown Monitor with Constitutional Limit.

Tracks equity drawdowns and enforces the maximum drawdown
constitutional limit (10%). When breached, signals for
kill switch activation.

Usage:
    monitor = DrawdownMonitor(max_drawdown=0.10)
    monitor.update(equity_value)
    if monitor.is_breached:
        # Halt trading

**Methods:** __init__, current_drawdown, max_drawdown_observed, is_breached, update, get_status, calculate_cvar_drawdown, calculate_risk_of_ruin, estimate_recovery_time

*Line: 41*

---

## Function: 

Initialize drawdown monitor.

Args:
    max_drawdown: Maximum allowed drawdown (0.10 = 10%).
    initial_equity: Starting equity value.

*Line: 55*

---

## Function: 

Current drawdown as a fraction (0.0 = no drawdown, 0.10 = 10% DD).

*Line: 75*

---

## Function: 

Maximum drawdown observed since monitoring started.

*Line: 82*

---

## Function: 

Whether the constitutional drawdown limit is breached.

*Line: 87*

---

## Function: 

Update monitor with new equity value.

Args:
    equity: Current portfolio equity.

Returns:
    DrawdownInfo with current drawdown status.

*Line: 91*

---

## Function: 

Get current drawdown status.

*Line: 129*

---

## Function: 

Calculate CVaR-based drawdown estimate.

Instead of just the worst historical drawdown, this
estimates the expected drawdown in the worst (1-α) scenarios.

Args:
    equity_series: Historical equity curve.
    confidence_level: Confidence level for CVaR.

Returns:
    CVaR drawdown estimate.

*Line: 140*

---

## Function: 

Calculate probability of reaching the drawdown limit.

Uses the gambler's ruin formula adapted for trading.

Args:
    win_rate: Probability of winning trade.
    avg_win: Average win amount.
    avg_loss: Average loss amount.
    max_drawdown_limit: Maximum drawdown before ruin.

Returns:
    Probability of ruin (0-1).

*Line: 175*

---

## Function: 

Estimate time to recover from drawdown.

Args:
    current_drawdown: Current drawdown as fraction.
    avg_annual_return: Expected annual return.

Returns:
    Estimated recovery time in years.

*Line: 214*

---

