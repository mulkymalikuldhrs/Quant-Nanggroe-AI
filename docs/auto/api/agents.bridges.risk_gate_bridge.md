# agents.bridges.risk_gate_bridge

## Class: 

Verdict from the deterministic risk gate bridge.

*Line: 52*

---

## Class: 

Result from the deterministic risk gate bridge.

Attributes:
    verdict: APPROVED, REJECTED, MODIFIED, or KILL_SWITCH
    symbol: Trading symbol that was evaluated
    direction: Trade direction (BUY/SELL)
    checkpoints: Dict of all 9 checkpoint results
    failed_checkpoints: List of checkpoint names that failed
    adjusted_lot_size: If MODIFIED, the new position size; otherwise None
    adjusted_position_pct: If MODIFIED, the new position size as % of portfolio
    llm_verdict: The LLM risk agent's original verdict (for logging)
    llm_disagreement: True if LLM and deterministic gate disagreed
    reason: Human-readable reason string
    timestamp: When the gate evaluation occurred

**Methods:** to_dict

*Line: 62*

---

## Class: 

Bridge between the LLM agent pipeline and the deterministic RiskCheckGate.

This bridge is a MANDATORY step in the trade flow. It sits AFTER the
LLM-based Risk Agent and BEFORE the Execution Agent.

Usage:
    bridge = RiskGateBridge()
    result = bridge.evaluate(
        symbol="AAPL",
        direction="BUY",
        lot_size=0.1,
        entry=150.0,
        stop_loss=148.0,
        account_balance=1_000_000,
        take_profit=154.0,
        llm_verdict="APPROVED",
        daily_pnl=-500.0,
        weekly_pnl=-2000.0,
        trade_count_today=2,
        active_positions=["GOOGL", "MSFT"],
    )
    if result.verdict == GateVerdict.APPROVED:
        # Proceed to execution
    elif result.verdict == GateVerdict.REJECTED:
        # Trade blocked — check result.failed_checkpoints

**Methods:** __init__, risk_manager, evaluate, evaluate_from_state, update_pnl, add_position, remove_position, status, _compute_kelly_if_available, _kelly_adjusted_lot

*Line: 109*

---

## Function: 

Convert to dictionary for agent state.

*Line: 91*

---

## Function: 

Initialize the Risk Gate Bridge.

Args:
    initial_equity: Starting account equity for the RiskManager.

*Line: 137*

---

## Function: 

Access the underlying RiskManager for P&L updates.

*Line: 162*

---

## Function: 

Run the deterministic 9-checkpoint risk gate on a trade proposal.

This is the FINAL gate — it CANNOT be bypassed. If the deterministic
gate rejects, the trade is blocked regardless of the LLM verdict.

Args:
    symbol: Trading symbol (e.g., "AAPL", "EURUSD")
    direction: Trade direction ("BUY" or "SELL")
    lot_size: Proposed lot size
    entry: Entry price
    stop_loss: Stop loss price
    account_balance: Current account balance
    take_profit: Optional take profit price
    llm_verdict: The LLM risk agent's verdict (for comparison logging)
    daily_pnl: Today's accumulated P&L
    weekly_pnl: This week's accumulated P&L
    trade_count_today: Number of trades executed today
    active_positions: List of currently held symbols

Returns:
    GateResult with the deterministic gate's final verdict

*Line: 166*

---

## Function: 

Evaluate trade decisions from the agent pipeline state.

This is the primary integration point for the LangGraph agent pipeline.
It takes the agent state after the LLM risk assessment and runs
the deterministic gate on each decision.

Args:
    state: Current AgentState dictionary

Returns:
    State updates with deterministic risk gate results

*Line: 348*

---

## Function: 

Update P&L tracking in the deterministic risk manager.

Call this after a trade is closed to keep the risk state current.

Args:
    trade_pnl: P&L from the completed trade.
    symbol: Symbol of the trade.

*Line: 500*

---

## Function: 

Track a new open position in the deterministic risk manager.

*Line: 511*

---

## Function: 

Remove a closed position from the deterministic risk manager.

*Line: 515*

---

## Function: 

Get current deterministic risk status.

*Line: 519*

---

## Function: 

Try to compute Kelly criterion position sizing.

Returns None if insufficient data is available.

Args:
    symbol: Trading symbol.
    account_balance: Account balance.
    entry: Entry price.
    stop_loss: Stop loss price.

Returns:
    Kelly result dict or None.

*Line: 525*

---

## Function: 

Adjust lot size based on Kelly criterion fraction.

Args:
    lot_size: Original proposed lot size.
    kelly_fraction: Kelly-adjusted fraction (0-1).
    account_balance: Account balance.
    entry: Entry price.
    stop_loss: Stop loss price.

Returns:
    Adjusted lot size.

*Line: 561*

---

