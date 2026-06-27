# agents.risk.agent

## Class: 

Risk Agent with 9-checkpoint gate and FULL VETO AUTHORITY.

Constitutional risk limits are HARDCODED and CANNOT be overridden.
Any checkpoint failure results in trade VETO. Breach of daily/weekly
limits activates the kill switch automatically.

**Methods:** __init__, run, _run_checkpoints, _kill_switch_active, _summarize_market_data

*Line: 49*

---

## Function: 

*Line: 58*

---

## Function: 

Execute the 9-checkpoint risk validation.

Every proposed trade must pass ALL 9 constitutional checkpoints.
Any failure results in VETO. No exceptions possible.

Args:
    state: Current agent state

Returns:
    State updates with risk assessment and verdict

*Line: 77*

---

## Function: 

Run all 9 constitutional risk checkpoints.

Args:
    signals: Proposed trading signals
    portfolio_state: Current portfolio state
    daily_pnl_pct: Daily PnL percentage
    weekly_pnl_pct: Weekly PnL percentage
    trades_today: Number of trades executed today

Returns:
    List of RiskCheckpoint results

*Line: 166*

---

## Function: 

Handle already-active kill switch.

*Line: 319*

---

## Function: 

Summarize market data for the risk prompt.

*Line: 347*

---

