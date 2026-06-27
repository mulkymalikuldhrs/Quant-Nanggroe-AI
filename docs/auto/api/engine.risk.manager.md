# engine.risk.manager

## Class: 

Current risk state tracking.

Tracks daily/weekly P&L, trade counts, and drawdown
for constitutional limit enforcement.

*Line: 57*

---

## Class: 

Risk Manager with CONSTITUTIONAL limits.

Enforces hardcoded risk limits that cannot be overridden.
All trade proposals must pass through the 9-checkpoint gate
before execution. If any constitutional limit is breached,
the kill switch is automatically activated.

Usage:
    rm = RiskManager()
    result = rm.check_trade(symbol="AAPL", direction="BUY", ...)
    if result["verdict"] == "APPROVED":
        # Execute trade
        size = rm.calculate_position_size(...)

**Methods:** __init__, check_trade, update_pnl, add_position, remove_position, calculate_position_size, calculate_kelly_size, status, _reset_daily_if_needed, _save_state, _load_state, stress_test, optimal_f_position_size, atr_position_size, calculate_position_size_with_var, _auto_check_kill_switch

*Line: 74*

---

## Function: 

*Line: 90*

---

## Function: 

9-checkpoint risk validation.

Returns APPROVED or VETOED with detailed checkpoint results.
No agent can override a VETO.

Args:
    symbol: Trading symbol.
    direction: BUY/SELL/LONG/SHORT.
    lot_size: Proposed lot size.
    entry: Entry price.
    stop_loss: Stop loss price.
    account_balance: Current account balance.
    take_profit: Optional take profit price.

Returns:
    Dict with verdict, checkpoints, and risk metrics.

*Line: 113*

---

## Function: 

Update daily and weekly P&L tracking.

Args:
    trade_pnl: P&L from the completed trade.
    symbol: Symbol of the trade (for position tracking).

*Line: 200*

---

## Function: 

Track a new open position.

*Line: 226*

---

## Function: 

Remove a closed position.

*Line: 231*

---

## Function: 

Calculate proper position size based on risk parameters.

Risk_pct is CAPPED at MAX_RISK_PER_TRADE regardless of input.

Args:
    account_balance: Current account balance.
    risk_pct: Requested risk percentage.
    stop_loss_pips: Stop loss distance in pips.
    pip_value: Value per pip.

Returns:
    Dict with position size and risk details.

*Line: 236*

---

## Function: 

Calculate position size using Kelly Criterion.

Args:
    win_rate: Historical win rate (0-1).
    avg_win: Average winning trade amount.
    avg_loss: Average losing trade amount.
    account_balance: Current account balance.
    method: Kelly method (FULL_KELLY, HALF_KELLY, QUARTER_KELLY).

Returns:
    Dict with Kelly calculation results.

*Line: 276*

---

## Function: 

Get current risk status.

*Line: 327*

---

## Function: 

Reset daily counters if new day.

*Line: 370*

---

## Function: 

Persist risk state to the configured backend.

*Line: 385*

---

## Function: 

Load risk state from the configured backend.

*Line: 409*

---

## Function: 

Run stress tests on portfolio.

Applies historical-like scenarios to the current return distribution
to estimate VaR and CVaR under stressed conditions.

Args:
    returns: Historical returns series.
    scenarios: Dict of {scenario_name: (return_change, vol_change)}.
        return_change is a multiplier on annualized return.
        vol_change is a multiplier on annualized volatility.

Returns:
    Dict of scenario results with stressed VaR, CVaR, and Sharpe.

*Line: 470*

---

## Function: 

Calculate position size to target volatility.

Uses volatility targeting approach: scales position up or down
so that the resulting portfolio has the desired volatility level.

Args:
    returns: Historical returns series.
    target_volatility: Target annual volatility.
    lookback: Lookback period in days.

Returns:
    Position size as fraction of portfolio (0.1 to 3.0).

*Line: 530*

---

## Function: 

Calculate position size using ATR (Average True Range).

Uses a 2-ATR stop distance and scales the position so that
the dollar risk equals the specified risk_per_trade fraction.

Args:
    entry_price: Entry price.
    atr: Average True Range value.
    account_balance: Account balance.
    risk_per_trade: Fraction of account to risk per trade.
    max_risk_per_trade: Maximum risk per trade.

Returns:
    Dict with position_size, stop_loss, and risk_amount.

*Line: 563*

---

## Function: 

Calculate position size based on VaR limit.

Scales the position so that the VaR at the given confidence level
does not exceed max_var_pct of the portfolio value.

Args:
    returns: Historical returns array.
    portfolio_value: Current portfolio value.
    max_var_pct: Maximum VaR as percentage of portfolio.
    confidence: VaR confidence level.

Returns:
    Position size as fraction of portfolio (0.0 to 1.0).

*Line: 606*

---

## Function: 

Auto-check if kill switch should activate based on risk limits.

*Line: 639*

---

